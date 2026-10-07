#!/usr/bin/env python3
"""Owned local PostgreSQL/RabbitMQ stand. No cloud, host ports or global cleanup."""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
PG = 'postgres@sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea'
MQ = 'rabbitmq@sha256:d7af1c87c5f1eda13fcfca06db452bf3aeab6619fc3358b68535c0c02c4e52bc'
LABEL = 'course.stand.owner'


def call(args, timeout=60, optional=False):
    r = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=timeout)
    if r.returncode and not optional:
        raise RuntimeError(f'{args[0]} failed ({r.returncode}): {r.stderr[-1200:]}')
    return r


def save(root, state):
    path = root / 'stand.json'
    if path.is_symlink() or (path.exists() and path.stat().st_nlink != 1):
        raise ValueError('unsafe state file')
    temporary = root / 'stand.new.json'
    if temporary.exists() or temporary.is_symlink():
        raise ValueError('pending state write needs inspection')
    temporary.write_text(json.dumps(state, indent=2) + '\n')
    temporary.replace(path)


def load(root):
    if root.is_symlink() or (root / 'stand.json').is_symlink():
        raise ValueError('symlink workspace refused')
    state = json.loads((root / 'stand.json').read_text())
    if state.get('root') != str(root.resolve()) or not re.fullmatch('[0-9a-f]{32}', state.get('id', '')):
        raise ValueError('ownership mismatch')
    return state


@contextlib.contextmanager
def lock(root):
    path = root / '.lock'
    if path.is_symlink() or (path.exists() and path.stat().st_nlink != 1):
        raise ValueError('unsafe lock')
    with path.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def inspect(kind, name, optional=False):
    r = call(['docker', kind, 'inspect', name], optional=optional)
    return json.loads(r.stdout)[0] if r.returncode == 0 else None


def owned(state, kind, name):
    value = inspect(kind, name)
    labels = value.get('Config', {}).get('Labels', {}) if kind == 'container' else value.get('Labels', {})
    if not labels or labels.get(LABEL) != state['id']:
        raise ValueError('resource ownership mismatch: ' + name)
    previous = state.get('resources', {}).get(name)
    identity = value.get('Id', value.get('Name'))
    if previous and previous['identity'] != identity:
        raise ValueError('resource identity changed: ' + name)
    return value


def ensure(root, state, kind, name, command):
    # Persist intent before creation; restart may recover only the matching label/ID.
    state.setdefault('intents', {})[name] = kind
    save(root, state)
    value = inspect(kind, name, optional=True)
    if value is None:
        if name in state.get('resources', {}):
            raise ValueError('saved resource missing; refusing silent data recreation: ' + name)
        call(command, timeout=120)
    value = owned(state, kind, name)
    state.setdefault('resources', {})[name] = {'kind': kind, 'identity': value.get('Id', value.get('Name'))}
    save(root, state)


def doctor(root):
    root_parent = root if root.exists() else root.parent
    free = shutil.disk_usage(root_parent).free
    info = json.loads(call(['docker', 'info', '--format', '{{json .}}']).stdout)
    if info.get('ServerErrors') or not info.get('ServerVersion'):
        raise RuntimeError('Docker daemon unavailable to this process; inspect socket access')
    contexts = json.loads(call(['docker', 'context', 'inspect']).stdout)
    endpoint = contexts[0]['Endpoints']['docker']['Host']
    override = os.environ.get('DOCKER_HOST')
    if not endpoint.startswith('unix://') or (override and not override.startswith('unix://')):
        raise RuntimeError('local Unix-socket Docker required; remote contexts are outside this lab')
    result = {'host_free_gib': round(free / 2**30, 2), 'docker_memory_gib': round(info['MemTotal'] / 2**30, 2),
              'architecture': info['Architecture'], 'server_version': info['ServerVersion']}
    if free < 5 * 2**30 or info['MemTotal'] < 2 * 2**30:
        raise RuntimeError('need 5 GiB free disk and 2 GiB Docker RAM: ' + json.dumps(result))
    return result


def readiness(state):
    until = time.monotonic() + 90
    pg, mq = state['prefix'] + '-pg', state['prefix'] + '-mq'
    while time.monotonic() < until:
        a = call(['docker', 'exec', pg, 'pg_isready', '-U', 'lab', '-d', 'lab'], optional=True)
        b = call(['docker', 'exec', '--user', 'rabbitmq', mq, 'rabbitmq-diagnostics', '-q', 'ping'], optional=True)
        if a.returncode == b.returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError('services not ready within 90 seconds')


def setup(root, state):
    state['preflight'] = doctor(root)
    for ref in (PG, MQ):
        if inspect('image', ref, optional=True) is None:
            call(['docker', 'pull', ref], timeout=240)
    image = state['prefix'] + '-client:local'
    if 'client_image_id' not in state:
        call(['docker', 'build', '--label', LABEL + '=' + state['id'], '-t', image, HERE], timeout=300)
        state['client_image_id'] = inspect('image', image)['Id']
        state['dockerfile_sha256'] = hashlib.sha256((HERE / 'Dockerfile').read_bytes()).hexdigest()
        save(root, state)
    elif inspect('image', image)['Id'] != state['client_image_id']:
        raise ValueError('client image identity changed')
    label = LABEL + '=' + state['id']
    net = state['prefix'] + '-net'
    ensure(root, state, 'network', net, ['docker', 'network', 'create', '--internal', '--label', label, net])
    for suffix, ref, variables in (
        ('pg', PG, ['POSTGRES_USER=lab', 'POSTGRES_PASSWORD=local-fixture-only', 'POSTGRES_DB=lab']),
        ('mq', MQ, ['RABBITMQ_DEFAULT_USER=lab', 'RABBITMQ_DEFAULT_PASS=local-fixture-only']),
    ):
        name, volume = state['prefix'] + '-' + suffix, state['prefix'] + '-' + suffix + '-data'
        ensure(root, state, 'volume', volume, ['docker', 'volume', 'create', '--label', label, volume])
        mount = '/var/lib/postgresql/data' if suffix == 'pg' else '/var/lib/rabbitmq'
        command = ['docker', 'create', '--name', name, '--hostname', suffix, '--label', label,
                   '--network', net, '--network-alias', suffix, '--memory', '512m', '--cpus', '1',
                   '--mount', f'type=volume,src={volume},dst={mount}']
        for variable in variables:
            command += ['--env', variable]
        command += [ref]
        ensure(root, state, 'container', name, command)
        call(['docker', 'start', name])
    readiness(state)
    state['status'] = 'running'
    save(root, state)


def lifecycle(root, state, action):
    for resource, record in state['resources'].items():
        owned(state, record['kind'], resource)
    for suffix in ('pg', 'mq'):
        call(['docker', action, state['prefix'] + '-' + suffix])
    if action == 'start':
        readiness(state)
    state['status'] = 'running' if action == 'start' else 'stopped'
    save(root, state)


def run(root, state, workspace, case):
    for resource, record in state['resources'].items():
        owned(state, record['kind'], resource)
    if inspect('image', state['prefix'] + '-client:local')['Id'] != state['client_image_id']:
        raise ValueError('client image identity changed')
    for suffix in ('pg', 'mq'):
        if not owned(state, 'container', state['prefix'] + '-' + suffix)['State']['Running']:
            raise RuntimeError('stand stopped; use resume')
    r = call(['docker', 'run', '--rm', '--network', state['prefix'] + '-net', '--user', f'{os.getuid()}:{os.getgid()}',
              '--memory', '256m', '--cpus', '1', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
              '--mount', f'type=bind,src={HERE},dst=/kit,readonly',
              '--mount', f'type=bind,src={workspace},dst=/lab', state['client_image_id'], case],
             timeout=90, optional=True)
    if r.stdout:
        print(r.stdout, end='')
    if r.stderr:
        print(r.stderr[-4000:], file=sys.stderr)
    try:
        report = json.loads(r.stdout)
    except ValueError:
        return 2  # A harness traceback is never successful defect detection.
    if case != 'health' and report.get('exit') != r.returncode:
        return 2
    return r.returncode


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['doctor', 'setup', 'check', 'stop', 'resume'])
    p.add_argument('root', type=Path)
    args = p.parse_args()
    root = args.root
    try:
        if args.action == 'doctor':
            print(json.dumps(doctor(root), indent=2)); return 0
        if args.action == 'setup' and not root.exists():
            root.mkdir(parents=True, mode=0o700)
            identity = uuid.uuid4().hex
            save(root, {'version': 1, 'id': identity, 'root': str(root.resolve()), 'prefix': 'ofstand-' + identity[:12]})
        state = load(root)
        with lock(root):
            if args.action == 'setup': setup(root, state)
            elif args.action in ('stop', 'resume'): lifecycle(root, state, 'stop' if args.action == 'stop' else 'start')
            else: return run(root, state, root.resolve(), 'health')
        print(json.dumps({'status': state['status'], 'root': str(root.resolve())}))
        return 0
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        print(str(exc), file=sys.stderr); return 2


if __name__ == '__main__':
    raise SystemExit(main())

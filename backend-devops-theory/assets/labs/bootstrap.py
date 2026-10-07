#!/usr/bin/env python3
"""Prepare an owned LOCAL kind/Linux lab; installs tools inside its workspace only."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import time
import uuid
import zipfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('course_stand', HERE.parent / 'backend-labs/stand.py')
stand = importlib.util.module_from_spec(spec); spec.loader.exec_module(stand)
call = stand.call
NODE = 'kindest/node@sha256:050072256b9a903bd914c0b2866828150cb229cea0efe5892e2b644d5dd3b34f'
PYTHON = 'python@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f'
PINS = ['ansible-core==2.19.13', 'cffi==2.1.1', 'cryptography==50.0.2', 'Jinja2==3.1.6',
        'MarkupSafe==3.0.3', 'packaging==26.3', 'pycparser==3.0', 'PyYAML==6.0.3', 'resolvelib==1.2.1']


def safe(root, relative):
    value = root / relative
    if root.resolve() not in value.resolve().parents or value.is_symlink() or (value.is_file() and value.stat().st_nlink != 1):
        raise ValueError('unsafe workspace path: ' + relative)
    return value


def download(root, name, url):
    target = safe(root, 'downloads/' + name)
    target.parent.mkdir(exist_ok=True)
    call(['curl', '-fL', '-sS', '--connect-timeout', '15', '--max-time', '180', '--output', target, url], timeout=190)
    return target


def install(root, state, name, url, checksum_url, member=None):
    target = safe(root, 'tools/' + name)
    if name in state.get('tools', {}):
        if hashlib.sha256(target.read_bytes()).hexdigest() != state['tools'][name]['binary_sha256']:
            raise ValueError('installed tool changed: ' + name)
        return
    archive = download(root, url.rsplit('/',1)[1], url)
    checksum = download(root, name + '.checksums', checksum_url).read_text()
    matching = [line.split()[0] for line in checksum.splitlines() if archive.name in line]
    if not matching and len(checksum.split()) == 1: matching = [checksum.strip()]
    expected = matching[0] if len(matching) == 1 else ''
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if not re.fullmatch('[0-9a-fA-F]{64}', expected) or actual != expected.lower():
        raise ValueError('release checksum mismatch: ' + name)
    if member and archive.name.endswith('.zip'):
        with zipfile.ZipFile(archive) as package: data = package.read(member)
    elif member:
        with tarfile.open(archive) as package:
            entry = package.getmember(member)
            if not entry.isfile(): raise ValueError('archive entry is not a regular file')
            data = package.extractfile(entry).read()
    else: data = archive.read_bytes()
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(data); target.chmod(0o700)
    state.setdefault('tools', {})[name] = {'url': url, 'checksum_url': checksum_url,
        'archive_sha256': actual, 'binary_sha256': hashlib.sha256(data).hexdigest()}
    stand.save(root, state)


def tools(root, state):
    system = platform.system().lower()
    arch = {'arm64':'arm64', 'aarch64':'arm64', 'x86_64':'amd64'}.get(platform.machine())
    if system not in ('darwin','linux') or not arch: raise ValueError('supported hosts: macOS/Linux amd64/arm64')
    pair = system + '-' + arch
    url = 'https://github.com/kubernetes-sigs/kind/releases/download/v0.29.0/kind-' + pair
    install(root,state,'kind',url,url+'.sha256sum')
    url = f'https://dl.k8s.io/release/v1.33.1/bin/{system}/{arch}/kubectl'
    install(root,state,'kubectl',url,url+'.sha256')
    url = f'https://get.helm.sh/helm-v3.18.3-{pair}.tar.gz'
    install(root,state,'helm',url,url+'.sha256sum',pair+'/helm')
    url = f'https://releases.hashicorp.com/terraform/1.13.5/terraform_1.13.5_{system}_{arch}.zip'
    install(root,state,'terraform',url,'https://releases.hashicorp.com/terraform/1.13.5/terraform_1.13.5_SHA256SUMS','terraform')


def node(state):
    name = state['prefix'] + '-control-plane'
    current = stand.inspect('container', name)
    if current['Config']['Labels'].get('io.x-k8s.kind.cluster') != state['prefix']:
        raise ValueError('kind ownership label mismatch')
    if state.get('node_id') and current['Id'] != state['node_id']:
        raise ValueError('kind node identity changed')
    return name, current


def dexec(state, *args, timeout=120):
    name, _ = node(state)
    return call(['docker', 'exec', name, *args], timeout=timeout)


def user_exec(state, args, timeout=120):
    name, _ = node(state)
    return call(['docker','exec',name,'runuser','-u','learner','--','env','XDG_RUNTIME_DIR=/run/user/1500',
                 'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1500/bus',*args], timeout=timeout)


def user_manager(state):
    dexec(state, 'systemctl', 'start', 'dbus', 'systemd-logind', 'user@1500.service')
    user_exec(state, ['systemctl','--user','show','--property=Version'])


def kubectl(root, *args, optional=False):
    return call([root/'tools/kubectl','--kubeconfig',root/'kubeconfig',*args], optional=optional)


def wait_cluster(root):
    until = time.monotonic() + 100
    while time.monotonic() < until:
        r = kubectl(root, 'get', '--raw', '/readyz', optional=True)
        if r.returncode == 0 and r.stdout.strip() == 'ok': return
        time.sleep(2)
    raise RuntimeError('API did not become ready within 100 seconds')


def import_image(root, state, ref, short):
    tag = state['prefix'] + '-' + short + ':fixture'
    call(['docker','tag',ref,tag])
    call([root/'tools/kind','load','docker-image',tag,'--name',state['prefix']],timeout=150)
    # Read the actual imported manifest; never alias a registry index as a manifest.
    reference = 'docker.io/library/' + tag
    lines = dexec(state,'ctr','--namespace','k8s.io','images','ls').stdout.splitlines()
    matching = [line.split()[2] for line in lines if line.split() and line.split()[0] == reference]
    if len(matching) != 1 or not re.fullmatch('sha256:[0-9a-f]{64}',matching[0]): raise ValueError('cannot identify imported manifest')
    alias = 'docker.io/library/' + ('python' if short=='py' else 'postgres') + '@' + matching[0]
    dexec(state,'ctr','--namespace','k8s.io','images','tag','--force',reference,alias)
    state.setdefault('images',{})[short] = {'registry':ref,'manifest':alias,'temporary_tag':tag}
    stand.save(root,state)


def setup(root, state):
    print('preflight and workspace tools',flush=True)
    info = stand.doctor(root)
    if info['host_free_gib'] < 8 or info['docker_memory_gib'] < 4:
        raise RuntimeError('kind/Linux profile needs 8 GiB host free space and 4 GiB Docker RAM')
    state['preflight'] = info; stand.save(root,state)
    tools(root,state)
    for ref in (NODE,PYTHON,stand.PG):
        if stand.inspect('image',ref,optional=True) is None: call(['docker','pull',ref],timeout=300)
    name = state['prefix'] + '-control-plane'
    current = stand.inspect('container',name,optional=True)
    if not current:
        if state.get('node_id'): raise ValueError('node missing; refuse silent replacement of data')
        config = safe(root,'kind.json')
        config.write_text(json.dumps({'kind':'Cluster','apiVersion':'kind.x-k8s.io/v1alpha4',
            'networking':{'apiServerAddress':'127.0.0.1'},'nodes':[{'role':'control-plane'}]}))
        state['creation_pending'] = True; stand.save(root,state)
        call([root/'tools/kind','create','cluster','--name',state['prefix'],'--image',NODE,
              '--config',config,'--kubeconfig',root/'kubeconfig','--wait','120s'],timeout=240)
    _, current = node(state)
    state['node_id'] = current['Id']; state['creation_pending'] = False; stand.save(root,state)
    if not current['State']['Running']: call(['docker','start',name])
    wait_cluster(root)
    print('local node ready; preparing Linux user environment',flush=True)
    if not state.get('linux_prepared'):
        dexec(state,'apt-get','update',timeout=180)
        dexec(state,'apt-get','install','-y','--no-install-recommends','dbus-user-session',timeout=180)
        existing = call(['docker','exec',name,'id','-u','learner'],optional=True)
        if existing.returncode:
            dexec(state,'useradd','--uid','1500','--create-home','--shell','/bin/bash','learner')
        elif existing.stdout.strip() != '1500': raise ValueError('unexpected learner UID')
        dexec(state,'usermod','-a','-G','systemd-journal','learner')
        dexec(state,'systemctl','start','dbus','systemd-logind')
        dexec(state,'loginctl','enable-linger','learner')
        deps = safe(root,'ansible-deps'); deps.mkdir(exist_ok=True)
        call(['docker','run','--rm','--mount',f'type=bind,src={deps},dst=/deps',PYTHON,'python','-m','pip','install',
              '--target','/deps','--python-version','3.11','--only-binary=:all:','--no-cache-dir',
              '--report','/deps/install-report.json',*PINS],timeout=300)
        dexec(state,'mkdir','-p','/opt/ansible-deps','/opt/orderflow-labs')
        call(['docker','cp',str(deps)+'/.',name+':/opt/ansible-deps'])
        wrapper = safe(root,'ansible-playbook')
        wrapper.write_text('#!/bin/sh\nPYTHONPATH=/opt/ansible-deps exec /usr/bin/python3 -m ansible.cli.playbook "$@"\n')
        wrapper.chmod(0o755)
        call(['docker','cp',wrapper,name+':/opt/ansible-playbook'])
        state['debian_packages'] = dexec(state,'dpkg-query','-W','systemd','dbus-user-session','python3').stdout.strip().splitlines()
        state['linux_prepared'] = True; stand.save(root,state)
    call(['docker','cp',str(HERE)+'/.',name+':/opt/orderflow-labs'])
    user_manager(state)
    for ref,short in ((PYTHON,'py'),(stand.PG,'pg')):
        if short not in state.get('images',{}): import_image(root,state,ref,short)
    state['status']='running'; stand.save(root,state)


def check(root,state):
    _,current=node(state)
    if not current['State']['Running']: raise RuntimeError('stand stopped; use resume')
    wait_cluster(root); user_manager(state)
    record={'node_id':current['Id'],'linux':user_exec(state,['python3','--version']).stdout.strip(),
        'linux_identity':user_exec(state,['id']).stdout.strip(),
        'ansible':user_exec(state,['/opt/ansible-playbook','--version']).stdout.splitlines()[0],
        'kubernetes':json.loads(kubectl(root,'version','-o','json').stdout)['serverVersion']['gitVersion'],
        'helm':call([root/'tools/helm','version','--short']).stdout.strip(),
        'terraform':json.loads(call([root/'tools/terraform','version','-json']).stdout)['terraform_version'],
        'node_ready':kubectl(root,'wait','--for=condition=Ready','node','--all','--timeout=60s').returncode==0}
    marker='/home/learner/stand-identity'
    code='from pathlib import Path; import sys; p=Path(sys.argv[1]); old=p.read_text() if p.exists() else None; assert old in (None,sys.argv[2]); assert old is not None or sys.argv[3]=="first"; p.write_text(sys.argv[2]); print(old is not None)'
    preserved=user_exec(state,['python3','-c',code,marker,state['id'],'repeat' if (root/'check.json').exists() else 'first']).stdout.strip()=='True'
    if (root/'check.json').exists() and not preserved: raise ValueError('Linux persistent marker lost')
    record['data_preserved']=preserved
    safe(root,'check.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def audit(root,state,cases=None):
    check(root,state)
    stamp=uuid.uuid4().hex[:10]
    destination=safe(root,'checks-'+stamp); destination.mkdir()
    script=HERE/'bootstrap_checks.py'
    name,_=node(state)
    call(['docker','cp',script,name+':/opt/orderflow-labs/bootstrap_checks.py'])
    cases=cases or ['L02a','L02b','L02c','A25','T24','K27','H28']
    linux_cases=[c for c in cases if c in ('L02a','L02b','L02c','A25')]
    summary={}
    if linux_cases:
        user_exec(state,['python3','/opt/orderflow-labs/bootstrap_checks.py',stamp,*linux_cases],timeout=200)
        call(['docker','cp',name+':/home/learner/checks-'+stamp+'/.',destination])
        summary=json.loads((destination/'summary.json').read_text())
    env={**os.environ,'KUBECONFIG':str(root/'kubeconfig'),'PATH':str(root/'tools')+os.pathsep+os.environ.get('PATH','')}
    for case in ('T24','K27','H28'):
        if case not in cases: continue
        workspace=destination/case
        subprocess.run([sys.executable,HERE/'lab.py','prepare',workspace,'--case',case],check=True,capture_output=True)
        codes=[]
        for phase in ('broken','reference','reset'):
            if phase!='broken': subprocess.run([sys.executable,HERE/'lab.py',phase,workspace],check=True,capture_output=True)
            cmd=[sys.executable,str(HERE/'lab.py'),'check',str(workspace),'--context','kind-'+state['prefix'],
                 '--image',state['images']['py']['manifest'],'--postgres-image',state['images']['pg']['manifest'],
                 '--helm',str(root/'tools/helm'),'--terraform',str(root/'tools/terraform')]
            result=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=150)
            (destination/(case+'-'+phase+'.json')).write_text(result.stdout)
            (destination/(case+'-'+phase+'.stderr')).write_text(result.stderr)
            codes.append(result.returncode)
        summary[case]=codes
        print(json.dumps({case:codes}),flush=True)
    safe(root,'audit.json').write_text(json.dumps({'path':str(destination),'results':summary},indent=2)+'\n')
    return 0 if all(v==[1,0,1] for v in summary.values()) else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['doctor','setup','check','stop','resume','audit'])
    p.add_argument('root',type=Path)
    p.add_argument('--cases',nargs='+',choices=['L02a','L02b','L02c','A25','T24','K27','H28'])
    args=p.parse_args(); root=args.root.resolve()
    try:
        if args.root.is_symlink(): raise ValueError('symlink root refused')
        if args.action=='doctor': print(json.dumps(stand.doctor(root))); return 0
        if args.action=='setup' and not root.exists():
            root.mkdir(parents=True,mode=0o700); identity=uuid.uuid4().hex
            stand.save(root,{'id':identity,'root':str(root),'prefix':'ofbootstrap-'+identity[:10],'profile':'kind-linux'})
        state=stand.load(root)
        if state.get('profile')!='kind-linux': raise ValueError('wrong profile')
        with stand.lock(root):
            if args.action=='setup': setup(root,state)
            elif args.action=='check': print(json.dumps(check(root,state),indent=2))
            elif args.action=='audit': return audit(root,state,args.cases)
            else:
                name,_=node(state); call(['docker','stop' if args.action=='stop' else 'start',name])
                if args.action=='resume': check(root,state)
                state['status']='stopped' if args.action=='stop' else 'running'; stand.save(root,state)
        print(json.dumps({'status':state.get('status'),'root':str(root)})); return 0
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
        print(str(exc),file=sys.stderr); return 2


if __name__=='__main__': raise SystemExit(main())

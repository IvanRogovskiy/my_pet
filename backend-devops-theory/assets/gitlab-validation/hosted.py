#!/usr/bin/env python3
"""A synthetic hosted GitLab gate/artifact audit on NEW branches only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import quote
import uuid

IMAGE = 'python@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f'
SCENARIOS = ('bypass', 'blocked', 'success', 'corrupt')
BUILD = '''import hashlib, json, os
from pathlib import Path
body = ('synthetic-course-release:' + os.environ['CI_COMMIT_SHA']).encode()
Path('release.txt').write_bytes(body)
Path('manifest.json').write_text(json.dumps({'commit':os.environ['CI_COMMIT_SHA'],'sha256':hashlib.sha256(body).hexdigest()}))
'''
PROMOTE = '''import hashlib, json, os
from pathlib import Path
m=json.loads(Path('manifest.json').read_text())
body=Path('release.txt').read_bytes()
if os.environ.get('AUDIT_CORRUPT') == 'true':
    body += b'corruption'
ok = m['commit']==os.environ['CI_COMMIT_SHA'] and hashlib.sha256(body).hexdigest()==m['sha256']
Path('promotion.json').write_text(json.dumps({'commit':m['commit'],'sha256':m['sha256'],'verified':ok,'synthetic_only':True}))
raise SystemExit(0 if ok else 1)
'''

def python_command(source):
    # POSIX quoted literal; no interpolation of source by a shell.
    import shlex
    return 'python -c ' + shlex.quote(source)

def pipeline(scenario):
    if scenario not in SCENARIOS:
        raise ValueError('unknown scenario')
    needs = [{'job':'build','artifacts':True}]
    if scenario != 'bypass':
        needs.append({'job':'gate','artifacts':False})
    return {
        'workflow': {'rules':[{'if':'$CI_PIPELINE_SOURCE == "push"'},{'when':'never'}]},
        'stages':['build','verify','promote'],
        'default':{'image':IMAGE,'timeout':'2 minutes'},
        'build':{'stage':'build','script':[python_command(BUILD)],
                 'artifacts':{'paths':['release.txt','manifest.json'],'expire_in':'7 days'}},
        'gate':{'stage':'verify','needs':['build'],'when':'manual','allow_failure':False,
                'script':['exit ' + ('0' if scenario in ('success','corrupt') else '1')]},
        'promote_marker':{'stage':'promote','needs':needs,
            'variables':{'GIT_STRATEGY':'none','AUDIT_CORRUPT':str(scenario=='corrupt').lower()},
            'script':[python_command(PROMOTE)],
            'artifacts':{'paths':['promotion.json'],'when':'always','expire_in':'7 days'}},
    }

def scrub(value):
    if isinstance(value, dict):
        return {k: '[REDACTED]' if re.search(r'token|password|secret|authorization|cookie',k,re.I) else scrub(v) for k,v in value.items()}
    if isinstance(value,list):
        return [scrub(v) for v in value]
    if isinstance(value,str):
        value=re.sub(r'\b(?:glpat-|glrt-|GR1348941)[A-Za-z0-9_-]+','[REDACTED]',value)
        return re.sub(r'(https?://[^\s?]+)\?[^\s]+',r'\1?[REDACTED]',value)
    return value

class Client:
    def __init__(self, wrapper):
        self.wrapper=str(Path(wrapper).resolve())
    def api(self, method, endpoint, payload=None, text=False):
        cmd=['sh',self.wrapper,'api','--hostname','gitlab.com','--method',method,endpoint]
        if payload is not None:
            cmd+=['--header','Content-Type: application/json','--input','-']
        r=subprocess.run(cmd,input=json.dumps(payload) if payload is not None else None,capture_output=True,text=True,timeout=60)
        if r.returncode:
            # Avoid dumping API bodies: they can carry access tokens and signed URLs.
            raise RuntimeError('GitLab request failed: '+method+' '+endpoint.split('?')[0]+'; '+scrub(r.stderr[-800:]))
        return r.stdout if text else json.loads(r.stdout)

def select(obj, fields):
    return {key:obj.get(key) for key in fields}

def prepare(path, project):
    if path.exists() or path.is_symlink():
        raise ValueError('prepare requires a new directory')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+',project):
        raise ValueError('invalid project path')
    path.mkdir(parents=True,mode=0o700)
    state={'version':1,'root':str(path.resolve()),'id':uuid.uuid4().hex,'project':project,'runs':{}}
    for scenario in SCENARIOS:
        (path/(scenario+'.gitlab-ci.json')).write_text(json.dumps(pipeline(scenario),indent=2)+'\n')
    save(path,state)
    return state

def save(path,state):
    (path/'state.json').write_text(json.dumps(scrub(state),ensure_ascii=False,indent=2)+'\n')

def load(path):
    if path.is_symlink():
        raise ValueError('symlink workspace refused')
    state=json.loads((path/'state.json').read_text())
    if state.get('root')!=str(path.resolve()) or not re.fullmatch('[0-9a-f]{32}',state.get('id','')):
        raise ValueError('workspace ownership mismatch')
    return state

def publish(client,path,state):
    endpoint='projects/'+quote(state['project'],safe='')
    project=client.api('GET',endpoint)
    if project.get('path_with_namespace')!=state['project'] or project.get('visibility')!='private':
        raise ValueError('requires the explicitly selected private course project')
    if project.get('ci_config_path') not in ('',None,'.gitlab-ci.yml'):
        raise ValueError('custom CI config path requires a separate reviewed fixture')
    state['project_id']=project['id']
    state['project_snapshot']=select(project,['id','path_with_namespace','visibility','default_branch','shared_runners_enabled'])
    base='projects/'+str(project['id'])
    branch=client.api('GET',base+'/repository/branches/'+quote(project['default_branch'],safe=''))
    state['base_sha']=branch['commit']['id']
    for scenario in SCENARIOS:
        if scenario in state['runs']:
            continue
        ref='course-quality-'+state['id'][:12]+'-'+scenario
        content=(path/(scenario+'.gitlab-ci.json')).read_text()
        if json.loads(content)!=pipeline(scenario):
            raise ValueError('fixture changed; review before publishing')
        lint=client.api('POST',base+'/ci/lint',{'content':content,'include_jobs':True})
        if not lint.get('valid'):
            raise ValueError('GitLab CI lint failed: '+str(scrub(lint.get('errors',[]))))
        state['runs'][scenario]={'ref':ref,'fixture_sha256':hashlib.sha256(content.encode()).hexdigest(),'publication':'pending'}
        save(path,state)  # A failed/ambiguous POST is inspected; never blindly retried.
        commit=client.api('POST',base+'/repository/commits',{'branch':ref,'start_sha':state['base_sha'],
            'commit_message':'Course audit: synthetic '+scenario+' gate and artifact verification',
            'actions':[{'action':'update','file_path':'.gitlab-ci.yml','content':content}]})
        state['runs'][scenario].update(sha=commit['id'],publication='committed')
        save(path,state)
        print(json.dumps({'scenario':scenario,'ref':ref,'sha':commit['id']}),flush=True)

def job_summary(job):
    return select(job,['id','name','status','stage','started_at','finished_at','web_url','failure_reason'])

def tick(client,path,state):
    base='projects/'+str(state['project_id'])
    for scenario,run in state['runs'].items():
        if run.get('result') is not None or run.get('publication')!='committed':
            continue
        pipelines=client.api('GET',base+'/pipelines?ref='+quote(run['ref'],safe='')+'&sha='+run['sha']+'&per_page=10')
        if not pipelines:
            continue
        if len(pipelines)!=1:
            raise ValueError('ambiguous pipeline count for exact SHA')
        pipe=pipelines[0]
        run['pipeline']=select(pipe,['id','sha','ref','status','web_url'])
        jobs=client.api('GET',base+'/pipelines/'+str(pipe['id'])+'/jobs?per_page=100')
        named={j['name']:j for j in jobs}
        run['jobs']=[job_summary(j) for j in jobs]
        gate=named.get('gate',{}); build=named.get('build',{}); marker=named.get('promote_marker',{})
        if gate.get('status')=='manual' and not run.get('gate_play_requested'):
            ready=marker.get('status')=='success' if scenario=='bypass' else build.get('status')=='success'
            if ready:
                run['before_gate']={j['name']:j['status'] for j in jobs}
                run['gate_play_requested']=True
                save(path,state)
                client.api('POST',base+'/jobs/'+str(gate['id'])+'/play',{})
        if pipe['status'] in ('success','failed','canceled','skipped'):
            expected={'bypass':('failed','success'),'blocked':('failed','skipped'),
                      'success':('success','success'),'corrupt':('success','failed')}[scenario]
            observed=(gate.get('status'),marker.get('status'))
            artifact=None
            if marker.get('status') in ('success','failed'):
                artifact=client.api('GET',base+'/jobs/'+str(marker['id'])+'/artifacts/promotion.json')
                run['artifact']=select(artifact,['commit','sha256','verified','synthetic_only'])
            artifact_ok=artifact is None if scenario=='blocked' else bool(artifact and artifact.get('commit')==run['sha'] and artifact.get('verified')==(scenario!='corrupt'))
            pipeline_ok=pipe['status']==('success' if scenario=='success' else 'failed')
            run['result']={'passed':observed==expected and artifact_ok and pipeline_ok and build.get('status')=='success',
                           'expected_gate_marker':list(expected),'observed_gate_marker':list(observed),'artifact_checked':artifact_ok}
        save(path,state)
    complete=len(state['runs'])==len(SCENARIOS) and all(r.get('result') is not None for r in state['runs'].values())
    return complete

def verify(client,path,state):
    base='projects/'+str(state['project_id'])
    for scenario,run in state['runs'].items():
        if not run.get('result'):
            raise ValueError('collect all terminal results before verify')
        build=next(j for j in run['jobs'] if j['name']=='build')
        endpoint=base+'/jobs/'+str(build['id'])+'/artifacts/'
        manifest=client.api('GET',endpoint+'manifest.json')
        body=client.api('GET',endpoint+'release.txt',text=True).encode()
        actual=hashlib.sha256(body).hexdigest()
        ok=manifest.get('commit')==run['sha'] and manifest.get('sha256')==actual
        marker=run.get('artifact')
        if marker:
            ok=ok and marker.get('sha256')==actual and marker.get('commit')==manifest['commit']
        jobs={j['name']:j for j in run['jobs']}
        timing=(jobs['promote_marker']['finished_at'] < jobs['gate']['started_at']) if scenario=='bypass' else (
            jobs['promote_marker']['started_at'] is None if scenario=='blocked' else
            jobs['promote_marker']['started_at'] >= jobs['gate']['finished_at'])
        run['independent_artifact_check']={'downloaded_from_build_job':build['id'],'computed_sha256':actual,
            'manifest':select(manifest,['commit','sha256']),'passed':bool(ok),'ordering_confirmed':timing}
        run['result']['passed']=run['result']['passed'] and bool(ok) and timing
    branch=client.api('GET',base+'/repository/branches/'+quote(state['project_snapshot']['default_branch'],safe=''))
    state['default_branch_unchanged']=branch['commit']['id']==state['base_sha']
    save(path,state)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','publish','collect','verify','status'])
    parser.add_argument('path',type=Path)
    parser.add_argument('--project')
    parser.add_argument('--wrapper')
    parser.add_argument('--seconds',type=int,default=40)
    args=parser.parse_args()
    try:
        if args.action=='prepare':
            state=prepare(args.path,args.project or '')
        else:
            state=load(args.path)
            if args.action in ('publish','collect','verify'):
                if not args.wrapper:parser.error('--wrapper required')
                client=Client(args.wrapper)
                if args.action=='publish':publish(client,args.path,state)
                elif args.action=='verify':verify(client,args.path,state)
                else:
                    deadline=time.monotonic()+min(max(args.seconds,0),50)
                    while True:
                        done=tick(client,args.path,state)
                        if done or time.monotonic()>=deadline:break
                        time.sleep(3)
        print(json.dumps(scrub(state),ensure_ascii=False,indent=2))
        failed = state.get('default_branch_unchanged') is False or any(r.get('result',{}).get('passed') is False for r in state['runs'].values())
        return 1 if failed else 0
    except (ValueError,RuntimeError,OSError,subprocess.TimeoutExpired) as exc:
        print(str(scrub(str(exc))),file=sys.stderr);return 2

if __name__=='__main__':
    raise SystemExit(main())

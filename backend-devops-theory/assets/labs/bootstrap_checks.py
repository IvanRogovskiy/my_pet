"""Runs as the unprivileged learner inside the owned kind node."""
import json
from pathlib import Path
import subprocess
import sys

base=Path('/home/learner')/('checks-'+sys.argv[1])
base.mkdir()
cli='/opt/orderflow-labs/lab.py'
summary={}
for case in sys.argv[2:]:
    root=base/case
    subprocess.run([sys.executable,cli,'prepare',str(root),'--case',case],check=True,capture_output=True)
    codes=[]
    for phase in ('broken','reference','reset'):
        if phase!='broken': subprocess.run([sys.executable,cli,phase,str(root)],check=True,capture_output=True)
        result=subprocess.run([sys.executable,cli,'check',str(root),'--ansible','/opt/ansible-playbook'],capture_output=True,text=True,timeout=90)
        (base/(case+'-'+phase+'.json')).write_text(result.stdout)
        (base/(case+'-'+phase+'.stderr')).write_text(result.stderr)
        codes.append(result.returncode)
    summary[case]=codes
(base/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary))
# The controller always copies diagnostics, even when the learner checks fail.

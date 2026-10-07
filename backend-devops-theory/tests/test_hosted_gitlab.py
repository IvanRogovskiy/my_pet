import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

PATH=Path(__file__).resolve().parents[1]/'assets/gitlab-validation/hosted.py'
spec=importlib.util.spec_from_file_location('hosted_validation',PATH)
hosted=importlib.util.module_from_spec(spec);spec.loader.exec_module(hosted)

class Hosted(unittest.TestCase):
    def test_artifact_exact_commit_and_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            env={**os.environ,'CI_COMMIT_SHA':'a'*40}
            subprocess.run([sys.executable,'-c',hosted.BUILD],cwd=temp,env=env,check=True)
            for commit,corrupt,want in [('a'*40,'false',0),('b'*40,'false',1),('a'*40,'true',1)]:
                r=subprocess.run([sys.executable,'-c',hosted.PROMOTE],cwd=temp,env={**env,'CI_COMMIT_SHA':commit,'AUDIT_CORRUPT':corrupt})
                self.assertEqual(r.returncode,want)

    def test_sensitive_response_fields_and_urls_are_redacted(self):
        value={'runners_token':'synthetic-hidden','nested':{'Authorization':'bearer secret'},'message':'glrt-fakeSecret123 https://example.invalid/job?signature=private'}
        result=json.dumps(hosted.scrub(value))
        for secret in ('synthetic-hidden','bearer secret','fakeSecret123','signature=private'):
            self.assertNotIn(secret,result)

    def test_refuses_public_project_before_commit(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'owned';state=hosted.prepare(root,'example/course')
            client=Mock();client.api.return_value={'path_with_namespace':'example/course','visibility':'public'}
            with self.assertRaises(ValueError):hosted.publish(client,root,state)
            self.assertEqual(client.api.call_count,1)
            self.assertEqual(client.api.call_args.args[0],'GET')

if __name__=='__main__':unittest.main()

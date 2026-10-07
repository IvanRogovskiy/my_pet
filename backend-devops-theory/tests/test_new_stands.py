import importlib.util
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE=Path(__file__).resolve().parents[1]/'assets'
spec=importlib.util.spec_from_file_location('stand_guard_tests',BASE/'backend-labs/stand.py')
stand=importlib.util.module_from_spec(spec);spec.loader.exec_module(stand)


class NewStands(unittest.TestCase):
    def test_partial_docker_info_is_environment_error(self):
        result=subprocess.CompletedProcess([],0,json.dumps({'MemTotal':0,'Architecture':'','ServerVersion':''}),'')
        with tempfile.TemporaryDirectory() as folder, patch.object(stand,'call',return_value=result):
            with self.assertRaisesRegex(RuntimeError,'daemon unavailable'):
                stand.doctor(Path(folder))

    def test_missing_recorded_volume_is_not_recreated(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            state={'id':'a'*32,'resources':{'owned-data':{'kind':'volume','identity':'owned-data'}}}
            with patch.object(stand,'inspect',return_value=None), patch.object(stand,'call') as execute:
                with self.assertRaisesRegex(ValueError,'silent data recreation'):
                    stand.ensure(root,state,'volume','owned-data',['docker','volume','create','owned-data'])
                execute.assert_not_called()

    def test_replaced_container_is_never_stopped(self):
        state={'id':'a'*32,'prefix':'owned','resources':{'owned-pg':{'kind':'container','identity':'original'}}}
        current={'Id':'replacement','Config':{'Labels':{stand.LABEL:'a'*32}}}
        with patch.object(stand,'inspect',return_value=current), patch.object(stand,'call') as execute:
            with self.assertRaisesRegex(ValueError,'identity changed'):
                stand.lifecycle(Path('/unused'),state,'stop')
            execute.assert_not_called()

    def test_backend_reset_preserves_evidence_and_refuses_symlink(self):
        cli=BASE/'backend-labs/lab.py'
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'lab'
            subprocess.run([sys.executable,cli,'prepare',root,'--case','B08R'],check=True,capture_output=True)
            evidence=root/'evidence/kept.json';evidence.write_text('{"old":true}')
            subprocess.run([sys.executable,cli,'reference',root],check=True,capture_output=True)
            subprocess.run([sys.executable,cli,'reset',root],check=True,capture_output=True)
            self.assertEqual(evidence.read_text(),'{"old":true}')
            outside=Path(folder)/'outside.py';outside.write_text('untouched')
            (root/'submission.py').unlink();(root/'submission.py').symlink_to(outside)
            result=subprocess.run([sys.executable,cli,'reset',root],capture_output=True)
            self.assertEqual(result.returncode,2)
            self.assertEqual(outside.read_text(),'untouched')

    def test_harness_traceback_is_not_a_detected_student_defect(self):
        state={'resources':{},'prefix':'owned','client_image_id':'sha256:fixture'}
        image={'Id':'sha256:fixture'}
        result=subprocess.CompletedProcess([],1,'','Traceback: missing evidence directory')
        with patch.object(stand,'inspect',return_value=image), patch.object(stand,'owned',return_value={'State':{'Running':True}}), patch.object(stand,'call',return_value=result):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(stand.run(Path('/unused'),state,Path('/unused'),'B08R'),2)


if __name__=='__main__':unittest.main()

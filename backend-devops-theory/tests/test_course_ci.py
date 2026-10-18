"""CI evidence guard must fail on tampering, omissions and redirected paths."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("course_ci", Path(__file__).resolve().parents[2] / "scripts/course_ci.py")
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


class EvidenceGuard(unittest.TestCase):
    def test_changed_missing_extra_or_redirected_evidence_fails(self):
        for mutation in ("changed", "missing", "extra", "symlink", "traversal"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "report"
                root.mkdir()
                target = root / "answer.json"
                target.write_text("original")
                hashes = {"answer.json": hashlib.sha256(b"original").hexdigest()}
                (root / "manifest.json").write_text(json.dumps({"sha256": hashes}))
                self.assertEqual(ci.verify_manifest(root), 1)
                if mutation == "changed": target.write_text("changed")
                elif mutation == "missing": target.unlink()
                elif mutation == "extra": (root / "extra.txt").write_text("unregistered")
                elif mutation == "symlink":
                    outside = Path(temp) / "original"
                    target.rename(outside)
                    target.symlink_to(outside)
                else:
                    (root / "manifest.json").write_text(json.dumps({"sha256": {"../answer.json": hashes["answer.json"]}}))
                with self.assertRaises((ValueError, OSError)):
                    ci.verify_manifest(root)

    def test_manifest_checks_are_read_only_and_ignore_bytecode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "answer.json").write_bytes(b"first answer\n")
            content = json.dumps({"sha256": {"answer.json": hashlib.sha256(b"first answer\n").hexdigest()}})
            (root / "manifest.json").write_text(content)
            (root / "__pycache__").mkdir()
            (root / "__pycache__/x.pyc").write_bytes(b"cache")
            self.assertEqual(ci.verify_manifest(root), 1)
            self.assertEqual((root / "manifest.json").read_text(), content)
            self.assertEqual((root / "answer.json").read_bytes(), b"first answer\n")


if __name__ == "__main__":
    unittest.main()

"""Structural checks that remain useful when topics or references are edited."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Materials(unittest.TestCase):
    def test_local_links_resolve(self):
        for path in ROOT.rglob("*.md"):
            for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text()):
                if re.match(r"https?://|mailto:|#", link):
                    continue
                with self.subTest(file=str(path.relative_to(ROOT)), link=link):
                    self.assertTrue((path.parent / link.split('#')[0]).is_file())

    def test_topic_parts_and_prerequisites_match_index(self):
        index = (ROOT / "references/curriculum-index.md").read_text()
        rows = re.findall(r"^\| (\d{2}) \| (.*?) \| (\d+) \| (.*?) \|$",index,re.M)
        self.assertEqual([int(r[0]) for r in rows], list(range(1,31)))
        self.assertEqual(sum(int(r[2]) for r in rows),92)
        self.assertEqual(len(re.findall(r"^\| Ф\d \|",index,re.M)),6)
        boundaries = (ROOT / 'references/part-boundaries.md').read_text()
        actual_parts = re.findall(r'^\| (\d\d/\d) \|', boundaries, re.M)
        expected_parts = [number + '/' + str(part) for number, _, count, _ in rows for part in range(1, int(count)+1)]
        self.assertEqual(actual_parts, expected_parts)
        for number,title,count,filename in rows:
            content = (ROOT / "references" / filename).read_text()
            body = re.search(r"^## " + number + " " + re.escape(title) + r"\n(.*?)(?=^## |\Z)",content,re.M|re.S)[1]
            parts = re.search(r"\*\*Выдавать по частям:\*\*\n(.*?)(?=\n\*\*)",body,re.S)[1]
            self.assertEqual(len(re.findall(r"^\d+\.",parts,re.M)),int(count))
            prerequisites = re.search(r"Предпосылки: (.*?)\.",body)[1]
            self.assertTrue(all(int(p) < int(number) for p in re.findall(r"\d+",prerequisites)))


if __name__ == '__main__':
    unittest.main()

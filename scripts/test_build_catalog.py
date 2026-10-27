import tempfile
import unittest
from pathlib import Path

import build_catalog as bc

README = f"# T\n\n{bc.START}\nold\n{bc.END}\n\ntail\n"


def make_repo(root, skills):
    (root / "README.md").write_text(README, encoding="utf-8")
    for folder, frontmatter in skills.items():
        d = root / "skills" / folder
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(f"---\n{frontmatter}\n---\nbody\n", encoding="utf-8")


GOOD = 'name: {n}\ndescription: Does a thing. Then more detail.\nmetadata:\n  category: demo\n  version: "1.2.0"'


class CatalogTests(unittest.TestCase):
    def run_main(self, skills, *flags):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_repo(root, skills)
            code = bc.main(["--root", str(root), *flags])
            return code, (root / "README.md").read_text(encoding="utf-8")

    def test_parse_frontmatter_nested(self):
        data = bc.parse_frontmatter('---\nname: a\nmetadata:\n  version: "2"\n---\nx')
        self.assertEqual(data, {"name": "a", "metadata": {"version": "2"}})

    def test_writes_table_and_keeps_surrounding_text(self):
        code, readme = self.run_main({"a-skill": GOOD.format(n="a-skill")})
        self.assertEqual(code, 0)
        self.assertIn("| [`a-skill`](skills/a-skill) | demo | 1.2.0 | Does a thing. |", readme)
        self.assertTrue(readme.startswith("# T\n") and readme.endswith("tail\n"))

    def test_check_fails_when_stale_and_does_not_write(self):
        code, readme = self.run_main({"a-skill": GOOD.format(n="a-skill")}, "--check")
        self.assertEqual(code, 1)
        self.assertIn("old", readme)

    def test_check_passes_after_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_repo(root, {"a-skill": GOOD.format(n="a-skill")})
            self.assertEqual(bc.main(["--root", str(root)]), 0)
            self.assertEqual(bc.main(["--root", str(root), "--check"]), 0)

    def test_name_must_match_folder(self):
        code, _ = self.run_main({"folder": GOOD.format(n="other")})
        self.assertEqual(code, 1)

    def test_description_limit(self):
        long = GOOD.format(n="a-skill").replace("Does a thing. Then more detail.", "x" * 1025)
        code, _ = self.run_main({"a-skill": long})
        self.assertEqual(code, 1)

    def test_version_and_category_required(self):
        code, _ = self.run_main({"a-skill": "name: a-skill\ndescription: Hi there."})
        self.assertEqual(code, 1)

    def test_groups_by_category_before_name(self):
        # names and categories sort in opposite orders, so a name-only sort would fail this
        skills = {
            "a-skill": GOOD.format(n="a-skill").replace("demo", "zeta"),
            "b-skill": GOOD.format(n="b-skill").replace("demo", "alpha"),
        }
        _, readme = self.run_main(skills)
        self.assertLess(readme.index("b-skill"), readme.index("a-skill"))

    def test_name_orders_skills_within_a_category(self):
        skills = {
            "b-skill": GOOD.format(n="b-skill").replace("demo", "alpha"),
            "a-skill": GOOD.format(n="a-skill").replace("demo", "alpha"),
        }
        _, readme = self.run_main(skills)
        self.assertLess(readme.index("a-skill"), readme.index("b-skill"))


if __name__ == "__main__":
    unittest.main()

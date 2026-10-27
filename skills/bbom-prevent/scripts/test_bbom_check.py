"""Tests for bbom_check.py. Run: python3 -m unittest scripts/test_bbom_check.py -v (from the skill folder)."""
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bbom_check as bc  # noqa: E402

SCRIPT = os.path.join(HERE, "bbom_check.py")


def write(root, rel, body=""):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(textwrap.dedent(body))


def cycles(root):
    found, langs, skipped = bc.find_cycles(root, bc.DEFAULT_RULES)
    return found, langs, skipped


def jload(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def jdump(obj, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh)


def cli(root, *args):
    return subprocess.run([sys.executable, SCRIPT, *args, root], capture_output=True, text=True)


class PythonCycles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_two_module_cycle(self):
        write(self.root, "orders.py", "import billing\n")
        write(self.root, "billing.py", "import orders\n")
        found, langs, _ = cycles(self.root)
        self.assertEqual(found, [["billing.py", "orders.py"]])
        self.assertEqual(langs, ["Python"])

    def test_from_import_and_package_layout(self):
        write(self.root, "src/pkg/__init__.py")
        write(self.root, "src/pkg/a.py", "from pkg import b\n")
        write(self.root, "src/pkg/b.py", "from .a import thing\n")
        found, _, _ = cycles(self.root)
        self.assertEqual(found, [["src/pkg/a.py", "src/pkg/b.py"]])

    def test_relative_import_cycle(self):
        write(self.root, "app/__init__.py")
        write(self.root, "app/x.py", "from . import y\n")
        write(self.root, "app/y.py", "from .x import f\n")
        found, _, _ = cycles(self.root)
        self.assertEqual(found, [["app/x.py", "app/y.py"]])

    def test_lazy_import_inside_function_counts_by_default(self):
        write(self.root, "a.py", "import b\n")
        write(self.root, "b.py", "def f():\n    import a\n    return a\n")
        self.assertEqual(cycles(self.root)[0], [["a.py", "b.py"]])

    def test_load_time_scope_ignores_lazy_import(self):
        write(self.root, "a.py", "import b\n")
        write(self.root, "b.py", "def f():\n    import a\n    return a\n")
        rules = dict(bc.DEFAULT_RULES, cycle_scope="load-time")
        self.assertEqual(bc.find_cycles(self.root, rules)[0], [])

    def test_type_checking_import_is_not_a_cycle(self):
        write(self.root, "a.py", "import b\n")
        write(self.root, "b.py", "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import a\n")
        self.assertEqual(cycles(self.root)[0], [])

    def test_stdlib_name_does_not_create_false_cycle(self):
        write(self.root, "utils/json.py", "import app\n")
        write(self.root, "app.py", "import json\n")  # stdlib json, not utils/json.py
        self.assertEqual(cycles(self.root)[0], [])

    def test_acyclic_chain(self):
        write(self.root, "a.py", "import b\n")
        write(self.root, "b.py", "import c\n")
        write(self.root, "c.py", "x = 1\n")
        self.assertEqual(cycles(self.root)[0], [])

    def test_three_module_cycle_is_one_component(self):
        write(self.root, "a.py", "import b\n")
        write(self.root, "b.py", "import c\n")
        write(self.root, "c.py", "import a\n")
        self.assertEqual(cycles(self.root)[0], [["a.py", "b.py", "c.py"]])


class JsCycles(unittest.TestCase):
    def test_relative_cycle_with_index_resolution(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "src/a.ts", "import { b } from './lib'\n")
            write(root, "src/lib/index.ts", "import { a } from '../a'\n")
            write(root, "src/ok.ts", "import type { A } from './a'\nimport x from 'react'\n")
            found, langs, _ = cycles(root)
            self.assertEqual(found, [["src/a.ts", "src/lib/index.ts"]])
            self.assertIn("JavaScript/TypeScript", langs)

    def test_type_only_import_ignored(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "a.ts", "import { b } from './b'\n")
            write(root, "b.ts", "import type { a } from './a'\n")
            self.assertEqual(cycles(root)[0], [])

    def test_unsupported_language_is_reported_not_ignored(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "Main.java", "class Main {}\n")
            _, _, skipped = cycles(root)
            self.assertEqual(skipped, {".java": 1})


class InstalledToolingIgnored(unittest.TestCase):
    """Installed skills and the vendored script must not enter the baseline."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        big = "x = 1\n" * 450
        write(self.root, "app.py", "x = 1\n")
        write(self.root, ".kiro/skills/some-skill/scripts/big.py", big)
        write(self.root, ".claude/skills/some-skill/scripts/big.py", big)
        write(self.root, "tools/bbom_check.py", big)
        write(self.root, ".kiro/skills/some-skill/a.py", "import b\n")
        write(self.root, ".kiro/skills/some-skill/b.py", "import a\n")
        write(self.root, "tools/other.py", big)

    def tearDown(self):
        self.tmp.cleanup()

    def test_init_baseline_excludes_tooling_but_keeps_project_tools(self):
        self.assertEqual(cli(self.root, "init").returncode, 0)
        baseline = jload(os.path.join(self.root, ".bbom", "baseline.json"))
        self.assertEqual(list(baseline["big_files"]), ["tools/other.py"])
        self.assertEqual(baseline["cycles"], [])


class Ratchet(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        write(self.root, "orders.py", "import billing\n")
        write(self.root, "billing.py", "import orders\n")
        write(self.root, "db.py", "x = 1\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_existing_cycle_is_grandfathered_and_new_one_fails(self):
        self.assertEqual(cli(self.root, "init").returncode, 0)
        base = jload(os.path.join(self.root, ".bbom/baseline.json"))
        self.assertEqual(base["cycles"], [["billing.py", "orders.py"]])
        self.assertNotIn("_cycle_languages", base)
        self.assertEqual(cli(self.root, "check").returncode, 0)

        write(self.root, "x.py", "import y\n")
        write(self.root, "y.py", "import x\n")
        r = cli(self.root, "check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("NEW CYCLE", r.stdout)

    def test_file_joining_existing_cycle_fails(self):
        cli(self.root, "init")
        write(self.root, "orders.py", "import billing\nimport db\n")
        write(self.root, "db.py", "import billing\n")
        write(self.root, "billing.py", "import orders\n")
        r = cli(self.root, "check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("CYCLE GREW", r.stdout)

    def test_breaking_the_cycle_then_ratchet_locks_it_in(self):
        cli(self.root, "init")
        write(self.root, "billing.py", "x = 1\n")
        r = cli(self.root, "check")
        self.assertEqual(r.returncode, 0)
        self.assertIn("ratchet", r.stdout)
        self.assertEqual(cli(self.root, "ratchet").returncode, 0)
        base = jload(os.path.join(self.root, ".bbom/baseline.json"))
        self.assertEqual(base["cycles"], [])
        # the old cycle is now a new violation
        write(self.root, "billing.py", "import orders\n")
        self.assertEqual(cli(self.root, "check").returncode, 1)

    def test_accept_requires_reason_and_records_cycle(self):
        cli(self.root, "init")
        write(self.root, "x.py", "import y\n")
        write(self.root, "y.py", "import x\n")
        self.assertEqual(cli(self.root, "accept").returncode, 1)
        self.assertEqual(cli(self.root, "accept", "--reason", "short").returncode, 1)
        r = subprocess.run([sys.executable, SCRIPT, "accept", self.root, "--reason",
                            "Temporary, tracked in ADR-007, removed next sprint"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(cli(self.root, "check").returncode, 0)
        base = jload(os.path.join(self.root, ".bbom/baseline.json"))
        self.assertEqual(len(base["history"]), 1)

    def test_old_baseline_without_cycles_does_not_fail(self):
        cli(self.root, "init")
        path = os.path.join(self.root, ".bbom/baseline.json")
        base = jload(path)
        del base["cycles"]
        jdump(base, path)
        r = cli(self.root, "check")
        self.assertEqual(r.returncode, 0)
        self.assertIn("predates cycle detection", r.stdout)

    def test_init_refuses_to_overwrite(self):
        cli(self.root, "init")
        self.assertEqual(cli(self.root, "init").returncode, 1)

    def test_size_and_top_level_still_enforced(self):
        cli(self.root, "init")
        write(self.root, "big.py", "\n".join(f"v{i} = {i}" for i in range(500)))
        write(self.root, "newdir/a.py", "x = 1\n")
        out = cli(self.root, "check").stdout
        self.assertIn("NEW LARGE FILE", out)
        self.assertIn("NEW TOP-LEVEL", out)

    def test_boundary_rule(self):
        write(self.root, "ui/page.py", "from db import conn\n")
        cli(self.root, "init")
        rules_path = os.path.join(self.root, ".bbom/rules.json")
        rules = jload(rules_path)
        rules["boundaries"] = [{"name": "ui-no-db", "paths": ["ui/**"], "forbid_regex": r"from\s+db\s+import", "why": "x"}]
        jdump(rules, rules_path)
        os.remove(os.path.join(self.root, ".bbom/baseline.json"))
        cli(self.root, "init")
        self.assertEqual(cli(self.root, "check").returncode, 0)  # grandfathered
        write(self.root, "ui/other.py", "from db import conn\n")
        self.assertEqual(cli(self.root, "check").returncode, 1)


if __name__ == "__main__":
    unittest.main()

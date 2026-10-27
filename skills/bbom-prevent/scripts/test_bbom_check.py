"""Tests for bbom_check.py. Run: python3 -m unittest scripts/test_bbom_check.py -v (from the skill folder)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

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
    found, langs, skipped, _failed = bc.find_cycles(root, bc.DEFAULT_RULES)
    return found, langs, skipped


def jload(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def jdump(obj, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh)


def cli(root, *args):
    return subprocess.run([sys.executable, SCRIPT, *args, root], capture_output=True, text=True)


def cli_stdin(root, stdin, *args):
    return subprocess.run([sys.executable, SCRIPT, *args, root], capture_output=True, text=True, input=stdin)


def can_symlink():
    with tempfile.TemporaryDirectory() as d:
        try:
            os.symlink(d, os.path.join(d, "l"))
        except (OSError, NotImplementedError):
            return False
    return True


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


class PythonImportResolution(unittest.TestCase):
    """Every imported name resolves on its own, and package initializers are real dependencies."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_from_import_of_several_modules_keeps_every_edge(self):
        write(self.root, "pkg/__init__.py")
        write(self.root, "pkg/a.py", "from . import b, c\n")
        write(self.root, "pkg/b.py")
        write(self.root, "pkg/c.py", "from . import a\n")
        self.assertEqual(cycles(self.root)[0], [["pkg/a.py", "pkg/c.py"]])

    def test_outside_importer_depends_on_package_initializer(self):
        write(self.root, "a.py", "import pkg.b\n")
        write(self.root, "pkg/__init__.py", "import a\n")
        write(self.root, "pkg/b.py")
        self.assertEqual(cycles(self.root)[0], [["a.py", "pkg/__init__.py"]])

    def test_sibling_import_does_not_count_its_own_initializer(self):
        # importing pkg.a always loads pkg first, so a re-exporting __init__ is not a cycle by itself
        write(self.root, "pkg/__init__.py", "from .a import thing\n")
        write(self.root, "pkg/a.py", "from . import b\nfrom pkg.b import y\nthing = 1\n")
        write(self.root, "pkg/b.py", "y = 1\n")
        self.assertEqual(cycles(self.root)[0], [])

    def test_attribute_import_from_initializer_is_still_an_edge(self):
        write(self.root, "pkg/__init__.py", "from .a import thing\nCONST = 1\n")
        write(self.root, "pkg/a.py", "from pkg import CONST\nthing = 1\n")
        self.assertEqual(cycles(self.root)[0], [["pkg/__init__.py", "pkg/a.py"]])


class IncompleteAnalysis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        write(self.root, "a.py", "import b\n")
        write(self.root, "b.py", "import a\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_unparsable_file_is_listed(self):
        write(self.root, "broken.py", "this is invalid syntax!\n")
        _, _, _, failed = bc.find_cycles(self.root, bc.DEFAULT_RULES)
        self.assertEqual(failed, ["broken.py"])

    def test_check_warns_about_unparsed_files(self):
        cli(self.root, "init")
        write(self.root, "broken.py", "this is invalid syntax!\n")
        r = cli(self.root, "check")
        self.assertIn("NOT parsed", r.stdout)
        self.assertIn("broken.py", r.stdout)

    def test_ratchet_does_not_drop_a_cycle_while_analysis_is_incomplete(self):
        cli(self.root, "init")
        write(self.root, "b.py", "import a\nthis is invalid syntax!\n")  # edge b -> a is now invisible
        self.assertEqual(cli(self.root, "ratchet").returncode, 0)
        base = jload(os.path.join(self.root, ".bbom/baseline.json"))
        self.assertEqual(base["cycles"], [["a.py", "b.py"]])

    def test_ratchet_keeps_a_js_cycle_that_still_exists(self):
        write(self.root, "x.js", "const r = /[/*]/;\nimport './y.js';\n/* end */\n")
        write(self.root, "y.js", "import './x.js';\n")
        cli(self.root, "init")
        before = jload(os.path.join(self.root, ".bbom/baseline.json"))["cycles"]
        self.assertIn(["x.js", "y.js"], before)
        cli(self.root, "ratchet")
        self.assertIn(["x.js", "y.js"], jload(os.path.join(self.root, ".bbom/baseline.json"))["cycles"])

    def test_latin1_file_with_encoding_cookie_is_parsed(self):
        with open(os.path.join(self.root, "c.py"), "wb") as fh:
            fh.write(b"# -*- coding: latin-1 -*-\nimport a\nx = '\xe9'\n")
        write(self.root, "a.py", "import b\nimport c\n")
        found, _, _, failed = bc.find_cycles(self.root, bc.DEFAULT_RULES)
        self.assertEqual(failed, [])


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

    def test_commented_out_import_is_not_a_dependency(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "a.js", "// import b from './b'\n/* import b from './b' */\n")
            write(root, "b.js", "import a from './a'\n")
            self.assertEqual(cycles(root)[0], [])

    def test_import_after_a_comment_with_a_url_still_counts(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "a.js", "import b from './b' // see http://x.example/y\n")
            write(root, "b.js", "import a from './a'\n")
            self.assertEqual(cycles(root)[0], [["a.js", "b.js"]])

    def test_typescript_js_specifier_resolves_to_ts_source(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "a.ts", "import { b } from './b.js'\n")
            write(root, "b.ts", "import { a } from './a.js'\n")
            self.assertEqual(cycles(root)[0], [["a.ts", "b.ts"]])

    def test_mts_and_cjs_cycles_are_analysed_by_default(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "a.cjs", "const b = require('./b.cjs');\n")
            write(root, "b.cjs", "const a = require('./a.cjs');\n")
            write(root, "c.mts", "import { d } from './d.mjs'\n")
            write(root, "d.mts", "import { c } from './c.mjs'\n")
            self.assertEqual(cycles(root)[0], [["a.cjs", "b.cjs"], ["c.mts", "d.mts"]])

    def test_load_time_scope_is_declared_python_only(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "a.js", "const b = require('./b');\n")
            write(root, "b.js", "function f() { return require('./a'); }\n")
            rules = dict(bc.DEFAULT_RULES, cycle_scope="load-time")
            found, langs, _, _ = bc.find_cycles(root, rules)
            self.assertEqual(found, [["a.js", "b.js"]])  # JS cannot tell lazy from eager
            self.assertTrue(any("Python only" in lang for lang in langs), langs)

    def test_regex_literal_containing_a_comment_opener_does_not_hide_imports(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "a.js", "const r = /[/*]/;\nimport './b.js';\n/* end */\n")
            write(root, "b.js", "import './a.js';\n")
            self.assertEqual(cycles(root)[0], [["a.js", "b.js"]])

    def test_nested_template_containing_a_comment_opener_does_not_hide_imports(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "a.js", "const t = `${`/*`}`;\nimport './b.js';\n/* end */\n")
            write(root, "b.js", "import './a.js';\n")
            self.assertEqual(cycles(root)[0], [["a.js", "b.js"]])

    def test_import_text_inside_strings_and_templates_is_not_a_dependency(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "a.js", "const text = \"require('./b')\";\nconst more = `import x from './b'`;\n")
            write(root, "b.js", "import './a';\n")
            self.assertEqual(cycles(root)[0], [])

    def test_real_imports_around_strings_division_and_templates_still_count(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "a.js", "const half = total / 2; // note\nconst s = `x ${half / 2} y`;\n"
                                "const b = require('./b');\nexport * from './c';\n")
            write(root, "b.js", "import a from './a';\n")
            write(root, "c.js", "import { a } from './a';\n")
            self.assertEqual(cycles(root)[0], [["a.js", "b.js", "c.js"]])

    def test_method_named_require_is_not_an_import(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "a.js", "loader.require('./b');\n")
            write(root, "b.js", "import './a';\n")
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
        r = cli(self.root, "check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("NEW LARGE FILE", r.stdout)
        self.assertIn("NEW TOP-LEVEL", r.stdout)

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


    def test_removed_directory_alone_is_ratcheted(self):
        write(self.root, "old/a.py", "x = 1\n")
        cli(self.root, "init")
        shutil.rmtree(os.path.join(self.root, "old"))
        r = cli(self.root, "ratchet")
        self.assertEqual(r.returncode, 0)
        self.assertIn("old", r.stdout)
        self.assertNotIn("old", jload(os.path.join(self.root, ".bbom/baseline.json"))["top_level_dirs"])
        write(self.root, "old/a.py", "x = 1\n")
        self.assertIn("NEW TOP-LEVEL", cli(self.root, "check").stdout)

    def test_setup_order_enable_boundary_then_accept_with_reason(self):
        # the documented setup: init, enable the real boundary, then record what already violates it
        write(self.root, "src/a.py", "from db import conn\n")
        cli(self.root, "init")
        rules_path = os.path.join(self.root, ".bbom/rules.json")
        rules = jload(rules_path)
        rules["boundaries"] = [{"name": "src-no-db", "paths": ["src/**"], "forbid_regex": r"from\s+db\s+import", "why": "x"}]
        jdump(rules, rules_path)
        self.assertEqual(cli(self.root, "check").returncode, 1)
        r = subprocess.run([sys.executable, SCRIPT, "accept", self.root, "--reason",
                            "initial setup: grandfather existing violations"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(cli(self.root, "check").returncode, 0)
        history = jload(os.path.join(self.root, ".bbom/baseline.json"))["history"]
        self.assertTrue(any("src-no-db" in line for line in history[0]["accepted"]))


class StopHook(unittest.TestCase):
    """`check --stop-hook` follows the Claude Code Stop contract: exit 2 and stderr block, exit 0 allows."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        write(self.root, "a.py", "x = 1\n")
        cli(self.root, "init")
        write(self.root, "big.py", "\n".join(f"v{i} = {i}" for i in range(500)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_failure_blocks_with_the_report_on_stderr(self):
        r = cli_stdin(self.root, "{}", "check", "--stop-hook")
        self.assertEqual(r.returncode, 2)
        self.assertIn("NEW LARGE FILE", r.stderr)
        self.assertEqual(r.stdout, "")

    def test_second_stop_in_a_row_is_allowed_so_it_cannot_loop(self):
        r = cli_stdin(self.root, '{"stop_hook_active": true}', "check", "--stop-hook")
        self.assertEqual(r.returncode, 0)

    def test_clean_repo_passes(self):
        os.remove(os.path.join(self.root, "big.py"))
        self.assertEqual(cli_stdin(self.root, "{}", "check", "--stop-hook").returncode, 0)

    def test_plain_check_still_exits_1(self):
        self.assertEqual(cli(self.root, "check").returncode, 1)


@unittest.skipUnless(can_symlink(), "symlinks unavailable")
class SymlinkContainment(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.outside = os.path.join(self.tmp.name, "outside")
        self.root = os.path.join(self.tmp.name, "repo")
        os.makedirs(self.outside)
        os.makedirs(self.root)
        write(self.outside, "secret.py", "import zzz\n")
        write(self.outside, "pkg/inner.py", "x = 1\n")
        write(self.root, "real.py", "x = 1\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_symlinked_file_and_directory_are_not_scanned(self):
        os.symlink(os.path.join(self.outside, "secret.py"), os.path.join(self.root, "alias.py"))
        os.symlink(os.path.join(self.outside, "pkg"), os.path.join(self.root, "linked"))
        self.assertEqual(sorted(bc.code_files(self.root, bc.DEFAULT_RULES)), ["real.py"])

    def test_init_refuses_a_symlinked_state_directory(self):
        state = os.path.join(self.outside, "state")
        os.makedirs(state)
        os.symlink(state, os.path.join(self.root, ".bbom"))
        r = cli(self.root, "init")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(os.listdir(state), [])

    def test_check_refuses_a_symlinked_state_file(self):
        cli(self.root, "init")
        target = os.path.join(self.outside, "baseline.json")
        shutil.move(os.path.join(self.root, ".bbom/baseline.json"), target)
        os.symlink(target, os.path.join(self.root, ".bbom/baseline.json"))
        r = cli(self.root, "ratchet")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("symlink", r.stderr + r.stdout)


class AtomicSave(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name
        bc.save(self.base, "baseline.json", {"ok": 1})
        self.path = os.path.join(self.base, "baseline.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_unserializable_data_leaves_the_old_file_intact(self):
        with self.assertRaises(TypeError):
            bc.save(self.base, "baseline.json", {"bad": object()})
        self.assertEqual(jload(self.path), {"ok": 1})
        self.assertEqual(os.listdir(self.base), ["baseline.json"])

    def test_failed_replace_leaves_the_old_file_and_no_temp_file(self):
        with mock.patch.object(bc.os, "replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                bc.save(self.base, "baseline.json", {"new": 2})
        self.assertEqual(jload(self.path), {"ok": 1})
        self.assertEqual(os.listdir(self.base), ["baseline.json"])


class StateFilePermissions(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "POSIX permission bits")
    def test_new_state_file_honours_a_restrictive_umask(self):
        with tempfile.TemporaryDirectory() as base:
            old = os.umask(0o077)
            try:
                bc.save(base, "baseline.json", {"a": 1})
            finally:
                os.umask(old)
            self.assertEqual(os.stat(os.path.join(base, "baseline.json")).st_mode & 0o777, 0o600)

    @unittest.skipIf(os.name == "nt", "POSIX permission bits")
    def test_existing_state_file_keeps_its_mode(self):
        with tempfile.TemporaryDirectory() as base:
            path = os.path.join(base, "baseline.json")
            bc.save(base, "baseline.json", {"a": 1})
            os.chmod(path, 0o640)
            bc.save(base, "baseline.json", {"a": 2})
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o640)


class CommandOptions(unittest.TestCase):
    def test_stop_hook_is_rejected_before_init_writes_anything(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "a.py", "x = 1\n")
            r = cli(root, "init", "--stop-hook")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("--stop-hook", r.stderr)
            self.assertFalse(os.path.exists(os.path.join(root, ".bbom")))


class ScanCost(unittest.TestCase):
    def test_module_membership_is_built_once_per_scan(self):
        class CountingIndex(dict):
            values_calls = 0

            def values(self):
                CountingIndex.values_calls += 1
                return super().values()

        with tempfile.TemporaryDirectory() as root:
            for i in range(40):
                write(root, f"m{i}.py", f"import m{(i + 1) % 40}\n" if i % 2 else "x = 1\n")
            real = bc.py_module_index
            with mock.patch.object(bc, "py_module_index", lambda files: CountingIndex(real(files))):
                bc.find_cycles(root, bc.DEFAULT_RULES)
        self.assertLessEqual(CountingIndex.values_calls, 1)


@unittest.skipUnless(can_symlink(), "symlinks unavailable")
class LinkedAncestors(unittest.TestCase):
    def test_git_listed_file_under_a_symlinked_directory_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            outside, repo = os.path.join(tmp, "outside"), os.path.join(tmp, "repo")
            os.makedirs(outside)
            os.makedirs(repo)
            write(outside, "inner.py", "x = 1\n")
            write(repo, "linked/inner.py", "x = 1\n")
            write(repo, "real.py", "x = 1\n")
            try:
                subprocess.run(["git", "-C", repo, "init", "-q"], check=True)
                subprocess.run(["git", "-C", repo, "add", "."], check=True)
            except (OSError, subprocess.CalledProcessError):
                self.skipTest("git unavailable")
            shutil.rmtree(os.path.join(repo, "linked"))
            os.symlink(outside, os.path.join(repo, "linked"))
            listed = subprocess.run(["git", "-C", repo, "ls-files"], capture_output=True, text=True).stdout
            self.assertIn("linked/inner.py", listed)  # git still lists it; the scanner must not follow the link
            self.assertEqual(sorted(bc.code_files(repo, bc.DEFAULT_RULES)), ["real.py"])


@unittest.skipUnless(can_symlink() and hasattr(os, "O_NOFOLLOW"), "needs symlinks and O_NOFOLLOW")
class StateSwapRace(unittest.TestCase):
    def test_swapping_the_state_directory_after_the_check_does_not_redirect_the_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            base, outside = os.path.join(tmp, ".bbom"), os.path.join(tmp, "outside")
            os.makedirs(base)
            os.makedirs(outside)
            real_refuse, swapped = bc.refuse_symlinks, []

            def swap_after_check(*paths):
                real_refuse(*paths)
                if not swapped:
                    swapped.append(1)
                    os.rename(base, base + ".moved")
                    os.symlink(outside, base)

            with mock.patch.object(bc, "refuse_symlinks", swap_after_check):
                with self.assertRaises((OSError, SystemExit)):
                    bc.save(base, "baseline.json", {"a": 1})
            self.assertEqual(os.listdir(outside), [])


if __name__ == "__main__":
    unittest.main()

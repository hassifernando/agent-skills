"""Tests for learnings_check.py. Run: python3 -m unittest scripts/test_learnings_check.py -v (from the skill folder)."""
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import learnings_check as lc  # noqa: E402

SCRIPT = os.path.join(HERE, "learnings_check.py")
TODAY = date(2026, 11, 3)


def write(root, rel, body=""):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(textwrap.dedent(body))


def entry(title="Run migrations before tests", why="tests fail on a stale schema", evidence="`src/app.py`",
          scope="project", added="2026-11-03", verified="2026-11-03", promoted=None):
    lines = [f"## {title}"]
    for key, val in (("why", why), ("evidence", evidence), ("scope", scope), ("added", added),
                     ("verified", verified), ("promoted", promoted)):
        if val is not None:
            lines.append(f"- {key}: {val}")
    return "\n".join(lines) + "\n"


def topic(*entries, name="Testing"):
    return f"# {name}\n\n" + "\n".join(entries)


def index(*rows):
    return "# Learnings\n\n" + "".join(f"- [{n}]({s}.md) — {c} entries — covers {n}\n" for s, n, c in rows)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def check(self, today=TODAY):
        return lc.check(lc.Path(self.root), today)

    def config(self, **cfg):
        write(self.root, ".project-learnings.json", json.dumps(cfg))


class CheckTests(Base):
    def test_missing_dir_is_ok(self):
        rep = self.check()
        self.assertTrue(rep.ok)
        self.assertIn("no learnings yet", rep.notes)

    def test_valid_topic_and_index_pass(self):
        write(self.root, "src/app.py", "x = 1\n")
        write(self.root, "docs/learnings/testing.md", topic(entry(), entry(title="Mock the clock")))
        write(self.root, "docs/learnings/README.md", index(("testing", "Testing", 2)))
        rep = self.check()
        self.assertTrue(rep.ok)
        self.assertEqual(rep.errors, [])
        self.assertEqual(rep.warnings, [])

    def test_missing_field_is_error(self):
        write(self.root, "docs/learnings/testing.md", topic(entry(why=None)))
        write(self.root, "docs/learnings/README.md", index(("testing", "Testing", 1)))
        rep = self.check()
        self.assertEqual(len(rep.errors), 1)
        self.assertIn("testing.md", rep.errors[0])
        self.assertIn("why", rep.errors[0])
        self.assertIn(":3", rep.errors[0])  # the entry heading is on line 3

    def test_bad_scope_and_date_are_errors(self):
        write(self.root, "docs/learnings/testing.md", topic(entry(scope="global", added="03/11/2026")))
        write(self.root, "docs/learnings/README.md", index(("testing", "Testing", 1)))
        rep = self.check()
        self.assertEqual(len(rep.errors), 2)

    def test_over_cap_is_error(self):
        self.config(maxPerTopic=2)
        write(self.root, "docs/learnings/testing.md", topic(entry(title="a"), entry(title="b"), entry(title="c")))
        write(self.root, "docs/learnings/README.md", index(("testing", "Testing", 3)))
        rep = self.check()
        self.assertTrue(any("3 > 2" in e for e in rep.errors), rep.errors)

    def test_index_count_mismatch_is_error(self):
        write(self.root, "docs/learnings/testing.md", topic(entry(title="a"), entry(title="b")))
        write(self.root, "docs/learnings/README.md", index(("testing", "Testing", 3)))
        rep = self.check()
        self.assertEqual(len(rep.errors), 1)
        self.assertIn("3", rep.errors[0])

    def test_topic_missing_from_index_is_error(self):
        write(self.root, "docs/learnings/testing.md", topic(entry()))
        write(self.root, "docs/learnings/README.md", "# Learnings\n")
        rep = self.check()
        self.assertTrue(any("testing" in e and "index" in e for e in rep.errors), rep.errors)

    def test_index_points_to_missing_file_is_error(self):
        write(self.root, "docs/learnings/README.md", index(("ghost", "Ghost", 1)))
        rep = self.check()
        self.assertTrue(any("ghost" in e for e in rep.errors), rep.errors)

    def test_evidence_path_missing_is_warning(self):
        write(self.root, "docs/learnings/testing.md", topic(entry(evidence="`src/gone.py`")))
        write(self.root, "docs/learnings/README.md", index(("testing", "Testing", 1)))
        rep = self.check()
        self.assertTrue(rep.ok)
        self.assertTrue(any("src/gone.py" in w for w in rep.warnings), rep.warnings)

    def test_evidence_absolute_and_parent_paths_are_skipped(self):
        write(self.root, "docs/learnings/testing.md",
              topic(entry(evidence="`/etc/passwd.bak` and `../outside/file.py` and `https://x.io/a.b`")))
        write(self.root, "docs/learnings/README.md", index(("testing", "Testing", 1)))
        rep = self.check()
        self.assertTrue(rep.ok)
        self.assertEqual(rep.warnings, [])

    def test_stale_verified_is_warning(self):
        write(self.root, "docs/learnings/README.md", index(("testing", "Testing", 1)))
        write(self.root, "src/app.py", "")
        write(self.root, "docs/learnings/testing.md", topic(entry(verified=(TODAY - timedelta(days=181)).isoformat())))
        self.assertTrue(any("verified" in w for w in self.check().warnings))
        write(self.root, "docs/learnings/testing.md", topic(entry(verified=(TODAY - timedelta(days=180)).isoformat())))
        self.assertEqual(self.check().warnings, [])

    def test_secret_value_is_error(self):
        lines = [
            "AKIA" + "ABCDEFGH12345678",
            "ghp_" + "a" * 36,
            "github_pat_" + "A1b2C3d4E5f6G7h8I9j0K1",
            "sk-" + "a1B2c3D4e5F6g7H8i9J0k1",
            "sk_live_" + "a1B2c3D4e5F6g7H8i9J0",
            "xoxb-123456789012-abcdefghijkl",
            "-----BEGIN RSA PRIVATE KEY-----",
            "password = hunter2hunter2",
        ]
        body = "# Testing\n\n" + "\n".join(f"note {l}" for l in lines) + "\n"
        write(self.root, "docs/learnings/testing.md", body)
        write(self.root, "docs/learnings/README.md", index(("testing", "Testing", 0)))
        rep = self.check()
        secret_errors = [e for e in rep.errors if "secret" in e]
        self.assertEqual(len(secret_errors), len(lines), rep.errors)
        self.assertFalse(any("hunter2" in e for e in rep.errors))  # never echo the value

    def test_secret_name_without_value_is_not_flagged(self):
        write(self.root, ".env", "")
        write(self.root, "docs/learnings/testing.md", topic(entry(evidence="`STRIPE_KEY` in `.env`")))
        write(self.root, "docs/learnings/README.md", index(("testing", "Testing", 1)))
        rep = self.check()
        self.assertEqual(rep.errors, [])

    def test_secret_word_in_prose_or_code_is_not_flagged(self):
        lines = [
            "- why: the CSRF token: middleware rejects the form",
            "- why: o token: expirava quando o relógio mudava",
            "- evidence: tokenizer=whitespace",
            "- why: secret: AWS_S3_SECRET",
            "- why: the secret: STRIPE_KEY, read at startup",
            '- evidence: `api_key = os.getenv("STRIPE_KEY")`',
        ]
        for line in lines:
            with self.subTest(line=line):
                self.assertEqual(lc.find_secrets(line + "\n"), [])
        for line in ("password = hunter2hunter2", 'password="hunter2hunter2"', "token: x9Lk2mQ7pR4t"):
            with self.subTest(line=line):
                self.assertEqual(lc.find_secrets(line + "\n"), [1])

    def test_portuguese_values_with_english_keys_pass(self):
        self.config(language="pt-BR")
        write(self.root, "src/app.py", "")
        write(self.root, "docs/learnings/testes.md", topic(
            entry(title="Rode as migrações antes dos testes", why="o token: expirava quando o relógio mudava",
                  evidence="`src/app.py` e a investigação no PR #12"), name="Testes"))
        write(self.root, "docs/learnings/README.md", index(("testes", "Testes", 1)))
        rep = self.check()
        self.assertTrue(rep.ok, rep.errors)
        self.assertEqual(rep.warnings, [])

    def test_index_line_in_another_language_warns_with_expected_form(self):
        write(self.root, "docs/learnings/testes.md", topic(entry(evidence="PR #12")))
        write(self.root, "docs/learnings/README.md",
              "# Aprendizados\n\n- [Testes](testes.md) — 1 entrada — como rodar a suíte\n")
        rep = self.check()
        hints = [w for w in rep.warnings if "README.md:3" in w]
        self.assertEqual(len(hints), 1, rep.warnings)
        self.assertIn("— N entries —", hints[0])
        self.assertIn("English", hints[0])

    def test_topic_missing_from_index_names_expected_line(self):
        write(self.root, "docs/learnings/testing.md", topic(entry(evidence="PR #12")))
        write(self.root, "docs/learnings/README.md", "# Learnings\n")
        rep = self.check()
        self.assertTrue(any("- [Testing](testing.md) — 1 entry — " in e for e in rep.errors), rep.errors)

    def test_evidence_snippets_that_are_not_paths_are_not_probed(self):
        evidence = ("`ratelib.Scheduler`, `os.environ`, `user.id`, `src/*.py`, `f(x.y)`, `a = b.c`, "
                    '`"x.y"`, `which file?`, `arr[0].x`, `some text/with space`')
        write(self.root, "docs/learnings/testing.md", topic(entry(evidence=evidence)))
        write(self.root, "docs/learnings/README.md", index(("testing", "Testing", 1)))
        rep = self.check()
        self.assertEqual(rep.warnings, [])

    def test_evidence_file_names_are_probed(self):
        write(self.root, "docs/learnings/testing.md",
              topic(entry(evidence="`app.py`, `src/gone.py:12`, `.env`, `package.lock.json`")))
        write(self.root, "docs/learnings/README.md", index(("testing", "Testing", 1)))
        warned = "\n".join(self.check().warnings)
        for name in ("`app.py`", "`src/gone.py`", "`.env`", "`package.lock.json`"):
            self.assertIn(name, warned)

    def test_dir_escaping_repo_is_error(self):
        for value in ("../outside", "/tmp/x"):
            self.config(dir=value)
            rep = self.check()
            self.assertTrue(any("dir" in e for e in rep.errors), (value, rep.errors))
        self.assertIsNone(lc.resolve_dir(lc.Path(self.root), "../outside"))
        self.assertIsNone(lc.resolve_dir(lc.Path(self.root), "/tmp/x"))

    def test_dir_symlink_to_outside_is_error(self):
        with tempfile.TemporaryDirectory() as outside:
            write(outside, "secret-topic.md", topic(entry(evidence="`nope/missing.py`")))
            write(outside, "README.md", "# x\n")
            try:
                os.symlink(outside, os.path.join(self.root, "linked"))
            except (OSError, NotImplementedError):
                self.skipTest("symlinks not available")
            self.config(dir="linked")
            rep = self.check()
            self.assertTrue(any("dir" in e for e in rep.errors), rep.errors)
            blob = "\n".join(rep.errors + rep.warnings + rep.notes)
            self.assertNotIn("secret-topic", blob)
            self.assertEqual(lc.candidates(lc.Path(self.root)), [])

    def test_invalid_config_is_error(self):
        cases = {
            "{not json": "json",
            json.dumps({"maxPerTopic": 0}): "maxPerTopic",
            json.dumps({"maxPerTopic": "10"}): "maxPerTopic",
            json.dumps({"upstream": {"kind": "email"}}): "upstream",
            json.dumps({"language": 3}): "language",
            json.dumps({"upstream": {"kind": "github-issue", "label": "x"}}): "repo",
            json.dumps({"upstream": {"kind": "github-issue", "repo": "owner", "label": "x"}}): "repo",
            json.dumps({"upstream": {"kind": "github-issue", "repo": "a/b/c", "label": "x"}}): "repo",
            json.dumps({"upstream": {"kind": "github-issue", "repo": "o/r; rm -rf", "label": "x"}}): "repo",
            json.dumps({"upstream": {"kind": "github-issue", "repo": 5, "label": "x"}}): "repo",
            json.dumps({"upstream": {"kind": "github-issue", "repo": "o/r"}}): "label",
            json.dumps({"upstream": {"kind": "github-issue", "repo": "o/r", "label": ""}}): "label",
            json.dumps({"upstream": {"kind": "github-issue", "repo": "o/r", "label": "a\nb"}}): "label",
            json.dumps({"upstream": {"kind": "github-issue", "repo": "o/r", "label": "a`b"}}): "label",
            json.dumps({"upstream": {"kind": "github-issue", "repo": "o/r", "label": 3}}): "label",
            json.dumps({"upstream": {"kind": "file"}}): "path",
            json.dumps({"upstream": {"kind": "file", "path": ""}}): "path",
            json.dumps({"upstream": {"kind": "file", "path": ["x.md"]}}): "path",
        }
        for body, word in cases.items():
            with self.subTest(body=body):
                write(self.root, ".project-learnings.json", body)
                _, errors = lc.load_config(lc.Path(self.root))
                self.assertTrue(any(word.lower() in e.lower() for e in errors), errors)
                self.assertFalse(self.check().ok)

    def test_config_defaults_language_and_unknown_keys(self):
        cfg, errors = lc.load_config(lc.Path(self.root))
        self.assertEqual((cfg["dir"], cfg["maxPerTopic"], errors), ("docs/learnings", 10, []))
        self.assertNotIn("upstream", cfg)
        self.config(upstream={"kind": "github-issue", "repo": "my-org/shared.learnings", "label": "learning candidate"})
        cfg, errors = lc.load_config(lc.Path(self.root))
        self.assertEqual((errors, cfg["upstream"]["repo"]), ([], "my-org/shared.learnings"))
        self.config(language="pt-BR", upstream={"kind": "file", "path": "x.md"}, mystery=1)
        cfg, errors = lc.load_config(lc.Path(self.root))
        self.assertEqual(errors, [])
        rep = self.check()
        self.assertTrue(rep.ok)
        self.assertTrue(any("mystery" in w for w in rep.warnings), rep.warnings)


class ParseTests(unittest.TestCase):
    def test_crlf_bom_and_accents_parse_same(self):
        lf = topic(entry(why="não usar ação"), entry(title="Segunda"))
        crlf = "﻿" + lf.replace("\n", "\r\n")
        self.assertEqual(lc.parse_topic(crlf), lc.parse_topic(lf))
        parsed = lc.parse_topic(crlf)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0].fields["why"], "não usar ação")

    def test_parse_index(self):
        text = index(("testing", "Testing", 2), ("ops", "Ops", 0)) + "\nfree text\n"
        self.assertEqual(lc.parse_index(text), {"testing": 2, "ops": 0})

    def test_find_secrets_returns_line_numbers(self):
        self.assertEqual(lc.find_secrets("ok\npassword: hunter2hunter2\nok\n"), [2])
        self.assertEqual(lc.find_secrets("token: `SOME_TOKEN_NAME`\nsecret = ABC_DEF_GHI\n"), [])


class CandidateTests(Base):
    def test_candidates_lists_unpromoted_only(self):
        write(self.root, "docs/learnings/testing.md", topic(
            entry(title="Cand", scope="candidate"),
            entry(title="Done", scope="candidate", promoted="https://github.com/o/r/issues/1"),
            entry(title="Proj", scope="project")))
        got = lc.candidates(lc.Path(self.root))
        self.assertEqual([c["title"] for c in got], ["Cand"])
        self.assertEqual(got[0]["topic"], "testing")
        self.assertEqual(got[0]["fields"]["scope"], "candidate")


ASSETS = os.path.join(os.path.dirname(HERE), "assets")


def read_asset(name):
    with open(os.path.join(ASSETS, name), encoding="utf-8") as fh:
        return fh.read()


class AssetTests(Base):
    def test_assets_seed_a_valid_repo(self):
        config_text = read_asset("config.example.json")
        write(self.root, ".project-learnings.json", config_text)
        learnings_dir = json.loads(config_text)["dir"]
        write(self.root, f"{learnings_dir}/README.md", read_asset("index-template.md"))
        rep = self.check()
        self.assertTrue(rep.ok, rep.errors)
        self.assertEqual(rep.warnings, [])
        self.assertNotIn("no learnings yet", rep.notes)  # the seeded directory was really read

    def test_config_example_has_upstream_kinds(self):
        cfg = json.loads(read_asset("config.example.json"))
        self.assertIn(cfg["upstream"]["kind"], lc.UPSTREAM_KINDS)
        self.assertEqual(cfg["upstream"]["kind"], "github-issue")
        self.assertEqual(set(cfg), {"dir", "language", "maxPerTopic", "upstream"})

    def test_skill_md_names_the_final_lines(self):
        with open(os.path.join(os.path.dirname(HERE), "SKILL.md"), encoding="utf-8") as fh:
            skill = fh.read()
        for line in ("learning: written <path>", "learning: test proposed <path>", "learning: skipped <reason>",
                     "learning: promoted <link>", "learning: promote skipped <reason>",
                     "learning: promote skipped secret check failed",
                     "learning: refreshed <kept> kept, <changed> changed, <removed> removed"):
            self.assertIn(line, skill)


class CliTests(Base):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-I", SCRIPT, *args], capture_output=True, text=True)

    def test_cli_help_and_exit_codes(self):
        self.assertEqual(self.run_cli("--help").returncode, 0)
        ok = self.run_cli("check", "--repo", self.root)
        self.assertEqual(ok.returncode, 0)
        self.assertIn("note: no learnings yet", ok.stdout)
        write(self.root, "docs/learnings/testing.md", topic(entry(why=None)))
        write(self.root, "docs/learnings/README.md", index(("testing", "Testing", 1)))
        bad = self.run_cli("check", "--repo", self.root)
        self.assertEqual(bad.returncode, 1)
        self.assertIn("error:", bad.stdout)
        cand = self.run_cli("candidates", "--repo", self.root)
        self.assertEqual(cand.returncode, 0)
        self.assertIsInstance(json.loads(cand.stdout), list)


if __name__ == "__main__":
    unittest.main()

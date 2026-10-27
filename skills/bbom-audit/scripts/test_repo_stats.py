"""Tests for repo_stats.py. Run: python3 -m unittest scripts/test_repo_stats.py (from the skill folder)."""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import repo_stats as rs  # noqa: E402


class SymlinkContainment(unittest.TestCase):
    def test_symlinked_file_is_not_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            outside = os.path.join(tmp, "outside")
            repo = os.path.join(tmp, "repo")
            os.makedirs(outside)
            os.makedirs(repo)
            with open(os.path.join(outside, "secret.py"), "w") as fh:
                fh.write("x = 1\n" * 50)
            with open(os.path.join(repo, "real.py"), "w") as fh:
                fh.write("x = 1\n")
            try:
                os.symlink(os.path.join(outside, "secret.py"), os.path.join(repo, "alias.py"))
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            seen = sorted(os.path.basename(p) for p in rs.walk(repo))
            self.assertEqual(seen, ["real.py"])


if __name__ == "__main__":
    unittest.main()

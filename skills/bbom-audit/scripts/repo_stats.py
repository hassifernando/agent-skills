#!/usr/bin/env python3
"""Read-only, language-agnostic repository statistics for an architecture audit.

Standard library only. Never writes inside the repository, never installs anything,
never prints file contents. Output is a map of where to look, not a set of findings.

Usage:
    repo_stats.py REPO [--json OUT.json] [--top N] [--days D]
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "__pycache__", ".tox", ".mypy_cache",
    ".pytest_cache", "dist", "build", "target", "vendor", ".next", ".nuxt", ".gradle",
    ".idea", ".vscode", "coverage", ".terraform", "Pods", ".worktrees",
    "backups", "backup",
}
# Never opened, so their contents cannot leak into any output.
SECRET_NAME = re.compile(r"(^\.env(\..*)?$|\.pem$|\.key$|\.p12$|\.pfx$|id_rsa|credentials|secrets?\.)", re.I)
BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz", ".tar", ".7z",
    ".parquet", ".pkl", ".bin", ".so", ".dylib", ".dll", ".exe", ".woff", ".woff2", ".ttf",
    ".mp4", ".mov", ".mp3", ".sqlite", ".db", ".lock", ".onnx", ".pt", ".h5", ".jar", ".class",
}
LANGS = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".java": "Java", ".kt": "Kotlin",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".swift": "Swift",
    ".c": "C", ".h": "C", ".cpp": "C++", ".cc": "C++", ".hpp": "C++", ".scala": "Scala",
    ".sql": "SQL", ".sh": "Shell", ".bash": "Shell", ".html": "HTML", ".css": "CSS",
    ".scss": "CSS", ".vue": "Vue", ".svelte": "Svelte", ".yml": "YAML", ".yaml": "YAML",
    ".md": "Markdown", ".tf": "Terraform", ".dart": "Dart", ".lua": "Lua", ".r": "R",
}
CODE_LANGS = {l for l in LANGS.values()} - {"YAML", "Markdown", "HTML", "CSS"}
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|specs|e2e)(/|$)|(_test|\.test|\.spec|_spec)\.[a-z]+$|(^|/)test_[^/]+$", re.I)
AGENT_FILES = [
    "CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursorrules", ".cursor/rules", ".github/copilot-instructions.md",
    ".windsurfrules", ".aider.conf.yml", ".claude", ".codex",
]
CI_FILES = [
    ".github/workflows", ".gitlab-ci.yml", "Jenkinsfile", ".circleci", "azure-pipelines.yml",
    "bitbucket-pipelines.yml", ".travis.yml", "buildkite", ".drone.yml",
]
DOC_HINTS = ["README.md", "README", "docs", "ARCHITECTURE.md", "CONTRIBUTING.md", "adr", "docs/adr", "docs/architecture.md"]
MANIFESTS = [
    "package.json", "pyproject.toml", "requirements.txt", "setup.py", "go.mod", "Cargo.toml",
    "pom.xml", "build.gradle", "build.gradle.kts", "Gemfile", "composer.json", "Dockerfile",
    "docker-compose.yml", "docker-compose.yaml", "Makefile", "*.csproj", "mix.exs",
]
AI_TRAILER = re.compile(r"co-authored-by:.*(claude|anthropic|copilot|codex|openai|gemini|cursor|aider|devin)", re.I)


def run_git(repo, *args):
    try:
        out = subprocess.run(
            ["git", "-C", repo, *args], capture_output=True, text=True, timeout=120, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def walk(repo):
    for dirpath, dirnames, filenames in os.walk(repo):
        # A nested directory holding a `.git` *file* is a linked worktree or submodule:
        # a duplicate checkout that would double-count every file.
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not os.path.isfile(os.path.join(dirpath, d, ".git"))
        ]
        for name in filenames:
            yield os.path.join(dirpath, name)


def count_lines(path):
    n = 0
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                if b"\0" in chunk:
                    return None  # binary
                n += chunk.count(b"\n")
    except OSError:
        return None
    return n


def file_stats(repo, top):
    by_lang_files, by_lang_lines = Counter(), Counter()
    sizes, test_files, code_files = [], 0, 0
    top_dirs = defaultdict(lambda: [0, 0])  # first path component -> [files, lines]
    for path in walk(repo):
        rel = os.path.relpath(path, repo).replace(os.sep, "/")
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower()
        if SECRET_NAME.search(name) or ext in BINARY_EXT:
            continue
        lang = LANGS.get(ext)
        if lang is None:
            continue
        lines = count_lines(path)
        if lines is None:
            continue
        by_lang_files[lang] += 1
        by_lang_lines[lang] += lines
        head = rel.split("/")[0] if "/" in rel else "."
        top_dirs[head][0] += 1
        top_dirs[head][1] += lines
        if lang in CODE_LANGS:
            if TEST_PATH.search(rel):
                test_files += 1
            else:
                code_files += 1
            sizes.append((lines, rel))
    sizes.sort(reverse=True)
    return {
        "languages": [
            {"language": l, "files": by_lang_files[l], "lines": by_lang_lines[l]}
            for l, _ in by_lang_lines.most_common()
        ],
        "largest_code_files": [{"lines": n, "path": p} for n, p in sizes[:top]],
        "top_level_dirs": sorted(
            ({"dir": d, "files": v[0], "lines": v[1]} for d, v in top_dirs.items()),
            key=lambda x: -x["lines"],
        )[:15],
        "source_files": code_files,
        "test_files": test_files,
        "test_to_source_file_ratio": round(test_files / code_files, 3) if code_files else None,
    }


def git_stats(repo, top, days):
    if run_git(repo, "rev-parse", "--is-inside-work-tree") is None:
        return {"available": False}
    res = {"available": True}
    head = run_git(repo, "rev-parse", "HEAD")
    res["head"] = head.strip() if head else None
    branch = run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    res["branch"] = branch.strip() if branch else None
    count = run_git(repo, "rev-list", "--count", "HEAD")
    res["commits_total"] = int(count) if count and count.strip().isdigit() else None
    last = run_git(repo, "log", "-1", "--format=%aI")
    res["last_commit"] = last.strip() if last else None
    authors = run_git(repo, "shortlog", "-sn", "--no-merges", "HEAD")
    res["authors"] = len(authors.strip().splitlines()) if authors and authors.strip() else 0

    log = run_git(repo, "log", f"--since={days}.days.ago", "--name-only", "--format=@@%H", "--no-merges")
    churn, commits_window, per_commit = Counter(), 0, []
    if log:
        cur = []
        for line in log.splitlines():
            if line.startswith("@@"):
                if cur:
                    per_commit.append(cur)
                cur = []
                commits_window += 1
            elif line.strip():
                churn[line.strip()] += 1
                cur.append(line.strip())
        if cur:
            per_commit.append(cur)
    res["window_days"] = days
    res["commits_in_window"] = commits_window
    res["most_changed_files_in_window"] = [{"changes": n, "path": p} for p, n in churn.most_common(top)]
    # Commits touching many files at once hint at wide-impact changes.
    wide = sorted((len(c) for c in per_commit), reverse=True)
    res["commits_touching_20plus_files_in_window"] = sum(1 for n in wide if n >= 20)
    res["max_files_in_one_commit_in_window"] = wide[0] if wide else 0

    # Co-change: pairs of files that most often change together (only among the top-churn files).
    hot = {p for p, _ in churn.most_common(25)}
    pairs = Counter()
    for files in per_commit:
        hs = sorted(set(files) & hot)
        for i in range(len(hs)):
            for j in range(i + 1, len(hs)):
                pairs[(hs[i], hs[j])] += 1
    res["frequent_cochange_pairs"] = [
        {"count": n, "a": a, "b": b} for (a, b), n in pairs.most_common(10) if n >= 3
    ]

    bodies = run_git(repo, "log", "--format=%B%x00", "--max-count=5000")
    ai = 0
    if bodies:
        for body in bodies.split("\x00"):
            if AI_TRAILER.search(body):
                ai += 1
    res["commits_with_ai_coauthor_trailer"] = ai
    return res


def exists_any(repo, names):
    found = []
    for n in names:
        if "*" in n:
            continue
        if os.path.exists(os.path.join(repo, n)):
            found.append(n)
    return found


def manifests_found(repo):
    found = []
    for path in walk(repo):
        name = os.path.basename(path)
        if name in MANIFESTS or name.endswith(".csproj"):
            rel = os.path.relpath(path, repo).replace(os.sep, "/")
            if rel.count("/") <= 3:
                found.append(rel)
    return sorted(found)[:40]


def render_md(data):
    out = [f"# Repository stats: {data['repo']}", ""]
    g = data["git"]
    if g.get("available"):
        out += [
            f"- Commit: `{g.get('head')}` on `{g.get('branch')}`; {g.get('commits_total')} commits, "
            f"{g.get('authors')} authors, last commit {g.get('last_commit')}",
            f"- Last {g['window_days']} days: {g['commits_in_window']} commits; "
            f"{g['commits_touching_20plus_files_in_window']} touched 20+ files (max {g['max_files_in_one_commit_in_window']})",
            f"- Commits with an AI co-author trailer (last 5000): {g['commits_with_ai_coauthor_trailer']}",
        ]
    else:
        out.append("- Not a git repository: churn and history signals are unavailable (mark them Unverified).")
    f = data["files"]
    out += ["", f"- Source files: {f['source_files']}, test files: {f['test_files']}, "
            f"ratio {f['test_to_source_file_ratio']} (a rough signal, NOT coverage)", "", "## Languages", ""]
    out += [f"- {x['language']}: {x['files']} files, {x['lines']} lines" for x in f["languages"][:12]]
    out += ["", "## Largest code files", ""]
    out += [f"- {x['lines']:>6}  {x['path']}" for x in f["largest_code_files"]]
    if g.get("available"):
        out += ["", "## Most changed files in the window", ""]
        out += [f"- {x['changes']:>4}  {x['path']}" for x in g["most_changed_files_in_window"]]
        if g["frequent_cochange_pairs"]:
            out += ["", "## Files that change together", ""]
            out += [f"- {x['count']}x  {x['a']}  <->  {x['b']}" for x in g["frequent_cochange_pairs"]]
    out += ["", "## Top-level directories (by lines)", ""]
    out += [f"- {x['dir']}: {x['files']} files, {x['lines']} lines" for x in f["top_level_dirs"]]
    s = data["signals"]
    out += ["", "## Presence signals", "",
            f"- Agent instruction files: {s['agent_instruction_files'] or 'none'}",
            f"- CI config: {s['ci_config'] or 'none'}",
            f"- Docs: {s['docs'] or 'none'}",
            f"- Manifests: {', '.join(s['manifests']) or 'none'}", ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo")
    ap.add_argument("--json", dest="json_out", help="also write the full result as JSON to this path (outside the repo)")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--days", type=int, default=90)
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    if not os.path.isdir(repo):
        sys.exit(f"not a directory: {repo}")
    if args.json_out and os.path.abspath(args.json_out).startswith(repo + os.sep):
        sys.exit("refusing to write inside the audited repository; pick a path outside it")

    data = {
        "repo": repo,
        "files": file_stats(repo, args.top),
        "git": git_stats(repo, args.top, args.days),
        "signals": {
            "agent_instruction_files": exists_any(repo, AGENT_FILES),
            "ci_config": exists_any(repo, CI_FILES),
            "docs": exists_any(repo, DOC_HINTS),
            "manifests": manifests_found(repo),
        },
    }
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    print(render_md(data))


if __name__ == "__main__":
    main()

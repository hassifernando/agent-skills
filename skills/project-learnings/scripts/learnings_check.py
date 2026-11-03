#!/usr/bin/env python3
"""Read-only validator for a repository's curated learnings (the `project-learnings` skill).

Standard library only. It never writes. It reads `.project-learnings.json` at the repo root and the files of
the configured learnings directory (default `docs/learnings`); the only other thing it touches is an
existence check of the repo-relative paths cited as evidence. It never follows a symlink out of the repo.

    learnings_check.py check [--repo PATH]        exit 1 on errors; prints `error:`, `warning:`, `note:` lines
    learnings_check.py candidates [--repo PATH]   JSON list of `scope: candidate` entries not yet promoted

Config (`.project-learnings.json`, all optional): dir (default "docs/learnings"), maxPerTopic (default 10),
language (string), upstream {"kind": "github-issue", "repo": "owner/name", "label": "..."} or
{"kind": "file", "path": "..."}.

Layout: `<dir>/README.md` is the index, one line per topic:
    - [Topic name](slug.md) — N entries — what it covers
and `<dir>/<slug>.md` holds the entries; each `## Rule` heading opens one, followed by `- key: value` lines
(why, evidence, scope, added, verified, promoted). Run with `python3 -I` to ignore the environment.
"""
import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

DEFAULTS = {"dir": "docs/learnings", "maxPerTopic": 10}
SCOPES = ("project", "candidate")
UPSTREAM_KINDS = ("github-issue", "file")
STALE_DAYS = 180
CONFIG_NAME = ".project-learnings.json"
KNOWN_CONFIG_KEYS = {"dir", "maxPerTopic", "upstream", "language"}
REQUIRED_FIELDS = ("why", "evidence", "scope", "added", "verified")
KNOWN_FIELDS = REQUIRED_FIELDS + ("promoted",)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?:sk-|sk_live_)[A-Za-z0-9_-]{20,}"),
    re.compile(r"xoxb-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]
GENERIC_SECRET = re.compile(r"(?i)(?:password|passwd|secret|token|api[_-]?key)\w*\s*[:=]\s*(\S{8,})")
UPPER_NAME = re.compile(r"^[A-Z0-9_]+$")
PLAIN_WORD = re.compile(r"^[^\W\d_]+(?:[-'][^\W\d_]+)*$")
TRAILING_PUNCT = ".,;:!?)]}'\"`"
INDEX_LINE = re.compile(r"^\s*[-*]\s+\[[^\]]*\]\(([^)/\s]+)\.md\)\s*[—–-]+\s*(\d+)\s+entr(?:y|ies)\b")
TOPIC_LINK = re.compile(r"^\s*[-*]\s+\[[^\]]*\]\([^)/\s]+\.md\)")
INDEX_FORM = "- [Topic name](slug.md) — N entries — what it covers"
BACKTICKS = re.compile(r"`([^`]+)`")
LINE_SUFFIX = re.compile(r"(?::\d+(?:-\d+)?|#L\d+(?:-L?\d+)?)$")
GITHUB_REPO = re.compile(r"^[\w.-]+/[\w.-]+$")
NOT_A_PATH = re.compile(r"[\s(=\"*?\[]")
FILE_EXTENSIONS = frozenset("""
    bash bat c cc cfg cjs conf cpp cs css csv dart env ex exs go gradle h hpp htm html ini ipynb java jl js json
    jsx kt kts lock lua md mdx mjs mk php pl proto ps1 py pyi r rb rs rst sass scss sh sql svelte swift tf toml ts
    tsx txt vue xml yaml yml zsh
""".split())


@dataclass
class Entry:
    title: str
    fields: dict
    line: int


@dataclass
class Report:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.errors


def _load_config(repo):
    """Returns (config merged over DEFAULTS, errors, warnings). Invalid values fall back to the defaults."""
    cfg, errors, warnings = dict(DEFAULTS), [], []
    path = Path(repo) / CONFIG_NAME
    if path.is_symlink() or not path.is_file():
        if path.is_symlink():
            errors.append(f"{CONFIG_NAME}: is a symlink; refusing to read it")
        return cfg, errors, warnings
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        errors.append(f"{CONFIG_NAME}: invalid JSON ({exc})")
        return cfg, errors, warnings
    if not isinstance(data, dict):
        errors.append(f"{CONFIG_NAME}: must be a JSON object")
        return cfg, errors, warnings
    for key in sorted(set(data) - KNOWN_CONFIG_KEYS):
        warnings.append(f"{CONFIG_NAME}: unknown key '{key}' ignored")
    if "dir" in data:
        if isinstance(data["dir"], str) and data["dir"].strip():
            cfg["dir"] = data["dir"].strip()
        else:
            errors.append(f"{CONFIG_NAME}: 'dir' must be a non-empty string")
    if "maxPerTopic" in data:
        cap = data["maxPerTopic"]
        if isinstance(cap, int) and not isinstance(cap, bool) and cap >= 1:
            cfg["maxPerTopic"] = cap
        else:
            errors.append(f"{CONFIG_NAME}: 'maxPerTopic' must be an integer >= 1")
    if "language" in data:
        if isinstance(data["language"], str):
            cfg["language"] = data["language"]
        else:
            errors.append(f"{CONFIG_NAME}: 'language' must be a string")
    if "upstream" in data:
        up_errors = _upstream_errors(data["upstream"])
        if up_errors:
            errors.extend(f"{CONFIG_NAME}: {e}" for e in up_errors)
        else:
            cfg["upstream"] = data["upstream"]
    return cfg, errors, warnings


def _upstream_errors(up):
    """Problems with the `upstream` object; its values reach a shell command in promote, so they are strict."""
    if not isinstance(up, dict) or up.get("kind") not in UPSTREAM_KINDS:
        return [f"'upstream.kind' must be one of {', '.join(UPSTREAM_KINDS)}"]
    errors = []
    if up["kind"] == "github-issue":
        repo, label = up.get("repo"), up.get("label")
        if not (isinstance(repo, str) and GITHUB_REPO.match(repo)):
            errors.append("'upstream.repo' must be 'owner/name' (letters, digits, '_', '.', '-')")
        if not (isinstance(label, str) and label.strip() and not any(c in label for c in "\n\r`")):
            errors.append("'upstream.label' must be a non-empty string without newlines or backticks")
    elif not (isinstance(up.get("path"), str) and up["path"].strip()):
        errors.append("'upstream.path' must be a non-empty string")
    return errors


def load_config(repo):
    """Returns (config merged over the defaults, list of errors)."""
    cfg, errors, _ = _load_config(repo)
    return cfg, errors


def _inside(root, target):
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_dir(repo, rel):
    """The learnings directory as a Path, or None if it escapes the repo (absolute, `..`, or a symlink
    that resolves outside)."""
    if not rel or os.path.isabs(rel) or rel.startswith(("/", "\\", "~")) or re.match(r"^[A-Za-z]:", rel):
        return None
    if ".." in re.split(r"[\\/]", rel):
        return None
    root = Path(repo).resolve()
    target = (root / rel).resolve()
    return (root / rel) if _inside(root, target) else None


def parse_topic(text):
    """Entries of a topic file: each `## ` heading opens one, `- key: value` lines fill its fields."""
    entries, current, fenced = [], None, False
    for n, raw in enumerate(text.lstrip("﻿").splitlines(), 1):
        line = raw.rstrip()
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if line.startswith("## "):
            current = Entry(line[3:].strip(), {}, n)
            entries.append(current)
        elif current is not None:
            m = re.match(r"^\s*-\s+([A-Za-z][\w-]*)\s*:\s*(.*)$", line)
            if m:
                current.fields[m.group(1).lower()] = m.group(2).strip()
    return entries


def parse_index(text):
    """slug -> declared entry count, from the `- [Name](slug.md) — N entries — ...` lines."""
    out = {}
    for line in text.lstrip("﻿").splitlines():
        m = INDEX_LINE.match(line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def malformed_index_lines(text):
    """Numbers of the index lines that link a topic file but do not match the expected form."""
    return [n for n, line in enumerate(text.lstrip("﻿").splitlines(), 1)
            if TOPIC_LINK.match(line) and not INDEX_LINE.match(line)]


def _looks_like_secret(value):
    """The generic rule (provider patterns are separate). A value is flagged when, once surrounding quotes and
    trailing punctuation are dropped, it is not a backticked or UPPER_CASE variable name, not an expression
    (contains `(`), and either mixes letters with digits or is 12+ characters that are neither a plain word
    nor a dotted or quoted reference."""
    if value.startswith("`"):
        return False
    value = value.strip("'\"").rstrip(TRAILING_PUNCT)
    if not value or UPPER_NAME.match(value) or "(" in value:
        return False
    if any(c.isalpha() for c in value) and any(c.isdigit() for c in value):
        return True
    return len(value) >= 12 and not any(c in value for c in '."') and not PLAIN_WORD.match(value)


def find_secrets(text):
    """Numbers of the lines that look like they hold a secret value (a variable's name alone is fine)."""
    hits = []
    for n, line in enumerate(text.lstrip("﻿").splitlines(), 1):
        if any(p.search(line) for p in SECRET_PATTERNS):
            hits.append(n)
            continue
        if any(_looks_like_secret(m.group(1)) for m in GENERIC_SECRET.finditer(line)):
            hits.append(n)
    return hits


def _is_path_like(snippet):
    """A backticked snippet is probed as a path only if it has no spaces or code characters and either has a
    `/` or is a single file name with a known extension (`app.py`) or a dotfile (`.env`). Dotted identifiers
    such as `os.environ` or `user.id` are not paths."""
    if not snippet or snippet.startswith("http") or NOT_A_PATH.search(snippet):
        return False
    if "/" in snippet:
        return True
    if "." not in snippet:
        return False
    stem, ext = snippet.rsplit(".", 1)
    if not stem:
        return bool(ext)  # a dotfile: `.env`, `.gitignore`
    return ext.lower() in FILE_EXTENSIONS


def _evidence_paths(value):
    for snippet in BACKTICKS.findall(value):
        snippet = LINE_SUFFIX.sub("", snippet.strip())
        if _is_path_like(snippet):
            yield snippet


def _is_probeable(path):
    """False for paths that could point outside the repo: those are never existence-checked."""
    return bool(path) and not (os.path.isabs(path) or path.startswith(("/", "\\", "~"))
                               or re.match(r"^[A-Za-z]:", path) or ".." in re.split(r"[\\/]", path))


def _read(path):
    return path.read_text(encoding="utf-8-sig")


def _topic_name(text):
    """The `# ` title of a topic file, if it has one before the first entry (never one that looks like a secret,
    since it is echoed in a message)."""
    for line in text.lstrip("﻿").splitlines():
        if line.startswith("# "):
            return None if find_secrets(line) else line[2:].strip()
        if line.startswith("## "):
            return None
    return None


def _entries(n):
    return f"{n} entry" if n == 1 else f"{n} entries"


def _topic_files(directory):
    """Regular (non-symlink) topic files of the directory, as (slug, path), plus names skipped as symlinks."""
    topics, skipped = [], []
    for p in sorted(directory.glob("*.md")):
        if p.name.lower() == "readme.md":
            continue
        if p.is_symlink() or not p.is_file():
            skipped.append(p.name)
        else:
            topics.append((p.stem, p))
    return topics, skipped


def check(repo, today=None):
    repo = Path(repo)
    today = today or date.today()
    rep = Report()
    cfg, errors, warnings = _load_config(repo)
    rep.errors.extend(errors)
    rep.warnings.extend(warnings)
    directory = resolve_dir(repo, cfg["dir"])
    if directory is None:
        rep.errors.append(f"dir '{cfg['dir']}' escapes the repository (absolute, '..' or a symlink to outside)")
        return rep
    if not directory.is_dir():
        rep.notes.append("no learnings yet")
        return rep
    root = repo.resolve()
    rel_dir = cfg["dir"].rstrip("/")
    topics, skipped = _topic_files(directory)
    for name in skipped:
        rep.warnings.append(f"{rel_dir}/{name}: symlink or non-regular file skipped")

    index_path = directory / "README.md"
    declared, has_index = {}, index_path.is_file() and not index_path.is_symlink()
    if has_index:
        try:
            text = _read(index_path)
            declared = parse_index(text)
            for n in malformed_index_lines(text):
                rep.warnings.append(f"{rel_dir}/README.md:{n}: looks like a topic line but is not read as one; "
                                    f"expected \"{INDEX_FORM}\" (the word entry/entries stays in English)")
            for n in find_secrets(text):
                rep.errors.append(f"{rel_dir}/README.md:{n}: possible secret value; remove it")
        except (OSError, UnicodeDecodeError) as exc:
            rep.errors.append(f"{rel_dir}/README.md: cannot read ({exc})")

    counts, names = {}, {}
    for slug, path in topics:
        rel = f"{rel_dir}/{path.name}"
        try:
            text = _read(path)
        except (OSError, UnicodeDecodeError) as exc:
            rep.errors.append(f"{rel}: cannot read ({exc})")
            continue
        for n in find_secrets(text):
            rep.errors.append(f"{rel}:{n}: possible secret value; remove it")
        names[slug] = _topic_name(text) or slug
        entries = parse_topic(text)
        counts[slug] = len(entries)
        if len(entries) > cfg["maxPerTopic"]:
            rep.errors.append(f"{rel}: {len(entries)} > {cfg['maxPerTopic']} entries (maxPerTopic); "
                              "merge or retire entries")
        for e in entries:
            _check_entry(rep, repo, root, rel, e, today)

    for slug, _ in topics:
        if slug not in declared:
            line = f"- [{names.get(slug, slug)}]({slug}.md) — {_entries(counts.get(slug, 0))} — <what it covers>"
            rep.errors.append(f"{rel_dir}/{slug}.md: topic is missing from the index {rel_dir}/README.md; "
                              f"add a line like \"{line}\"")
        elif slug in counts and declared[slug] != counts[slug]:
            rep.errors.append(f"{rel_dir}/README.md: '{slug}' declares {declared[slug]} entries "
                              f"but {slug}.md has {counts[slug]}")
    known = {slug for slug, _ in topics}
    for slug in declared:
        if slug not in known:
            rep.errors.append(f"{rel_dir}/README.md: index points to '{slug}.md', which does not exist")
    return rep


def _check_entry(rep, repo, root, rel, e, today):
    where = f"{rel}:{e.line}"
    for key in REQUIRED_FIELDS:
        if not e.fields.get(key):
            rep.errors.append(f"{where}: entry '{e.title}' is missing required field '{key}'")
    for key in sorted(set(e.fields) - set(KNOWN_FIELDS)):
        rep.warnings.append(f"{where}: entry '{e.title}' has unknown field '{key}'")
    scope = e.fields.get("scope")
    if scope and scope not in SCOPES:
        rep.errors.append(f"{where}: entry '{e.title}' has scope '{scope}'; expected one of {', '.join(SCOPES)}")
    dates = {}
    for key in ("added", "verified"):
        val = e.fields.get(key)
        if not val:
            continue
        try:
            if not DATE_RE.match(val):
                raise ValueError(val)
            dates[key] = date.fromisoformat(val)
        except ValueError:
            rep.errors.append(f"{where}: entry '{e.title}' has {key} '{val}'; expected YYYY-MM-DD")
    if "verified" in dates and (today - dates["verified"]).days > STALE_DAYS:
        rep.warnings.append(f"{where}: entry '{e.title}' was last verified {dates['verified']} "
                            f"(over {STALE_DAYS} days ago); re-check it or retire it")
    for path in _evidence_paths(e.fields.get("evidence", "")):
        if not _is_probeable(path):
            continue
        target = (repo / path)
        if not _inside(root, target.resolve()):
            continue  # a symlink leading out of the repo: do not probe it
        if not target.exists():
            rep.warnings.append(f"{where}: entry '{e.title}' cites `{path}`, which does not exist")


def candidates(repo):
    """Entries with `scope: candidate` and no `promoted`, as {"topic", "title", "fields"}."""
    repo = Path(repo)
    cfg, _, _ = _load_config(repo)
    directory = resolve_dir(repo, cfg["dir"])
    if directory is None or not directory.is_dir():
        return []
    out = []
    topics, _ = _topic_files(directory)
    for slug, path in topics:
        try:
            entries = parse_topic(_read(path))
        except (OSError, UnicodeDecodeError):
            continue
        for e in entries:
            if e.fields.get("scope") == "candidate" and not e.fields.get("promoted"):
                out.append({"topic": slug, "title": e.title, "fields": e.fields})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, text in (("check", "validate the learnings; exit 1 on errors"),
                       ("candidates", "print unpromoted `scope: candidate` entries as JSON")):
        p = sub.add_parser(name, help=text)
        p.add_argument("--repo", default=".", help="repository root (default: current directory)")
    args = ap.parse_args(argv)
    repo = Path(args.repo)
    if args.cmd == "candidates":
        print(json.dumps(candidates(repo), ensure_ascii=False, indent=2))
        return 0
    rep = check(repo)
    for kind, items in (("error", rep.errors), ("warning", rep.warnings), ("note", rep.notes)):
        for item in items:
            print(f"{kind}: {item}")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())

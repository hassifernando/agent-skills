#!/usr/bin/env python3
"""Build the skills catalog in README.md from skills/*/SKILL.md, and validate each skill.

Standard library only.

    build_catalog.py            rewrite the catalog table between the README markers
    build_catalog.py --check    change nothing; exit 1 if a skill is invalid or the README is stale
"""
import argparse
import re
import sys
from pathlib import Path

START = "<!-- skills:start -->"
END = "<!-- skills:end -->"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def parse_frontmatter(text):
    """Parse the small YAML subset used by SKILL.md: scalar keys and one level of nested keys."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    data, current = {}, None
    for line in match.group(1).split("\n"):
        if not line.strip():
            continue
        if line.startswith((" ", "\t")):
            if current is not None and isinstance(data.get(current), dict):
                key, _, value = line.strip().partition(":")
                data[current][key.strip()] = value.strip().strip('"').strip("'")
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if value == "":
            data[key], current = {}, key
        else:
            data[key], current = value.strip('"').strip("'"), None
    return data


def first_sentence(text):
    match = re.search(r"(?<=[.!?])\s", text)
    return text[: match.start()] if match else text


def load_skills(skills_dir):
    """Return (skills, errors). Each skill is a dict with name, category, version, summary, path."""
    skills, errors = [], []
    for skill_md in sorted(Path(skills_dir).glob("*/SKILL.md")):
        folder = skill_md.parent.name
        data = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        if data is None:
            errors.append(f"{folder}: SKILL.md has no frontmatter")
            continue
        name, description = data.get("name", ""), data.get("description", "")
        meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        if name != folder:
            errors.append(f"{folder}: name '{name}' must equal the folder name")
        if not NAME_RE.match(name) or len(name) > 64:
            errors.append(f"{folder}: name '{name}' must be lowercase letters, digits and single hyphens, up to 64 chars")
        if not 1 <= len(description) <= 1024:
            errors.append(f"{folder}: description has {len(description)} chars, must be 1 to 1024")
        if not meta.get("version"):
            errors.append(f"{folder}: metadata.version is missing")
        if not meta.get("category"):
            errors.append(f"{folder}: metadata.category is missing")
        skills.append({
            "name": name or folder,
            "category": meta.get("category", "other"),
            "version": meta.get("version", "?"),
            "summary": first_sentence(description),
            "path": f"skills/{folder}",
        })
    return skills, errors


def render_table(skills):
    lines = ["| Skill | Category | Version | What it does |", "|---|---|---|---|"]
    for s in sorted(skills, key=lambda s: (s["category"], s["name"])):
        lines.append(f"| [`{s['name']}`]({s['path']}) | {s['category']} | {s['version']} | {s['summary']} |")
    return "\n".join(lines)


def replace_block(readme, table):
    if START not in readme or END not in readme:
        raise ValueError(f"README.md must contain {START} and {END}")
    head, rest = readme.split(START, 1)
    _, tail = rest.split(END, 1)
    return f"{head}{START}\n{table}\n{END}{tail}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="do not write; exit 1 if invalid or stale")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent), help="repository root")
    args = parser.parse_args(argv)

    root = Path(args.root)
    skills, errors = load_skills(root / "skills")
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 1
    if not skills:
        print("error: no skills found under skills/", file=sys.stderr)
        return 1

    readme_path = root / "README.md"
    current = readme_path.read_text(encoding="utf-8")
    try:
        updated = replace_block(current, render_table(skills))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if updated == current:
        print(f"catalog up to date ({len(skills)} skills)")
        return 0
    if args.check:
        print("error: README.md catalog is stale; run: python3 scripts/build_catalog.py", file=sys.stderr)
        return 1
    readme_path.write_text(updated, encoding="utf-8")
    print(f"catalog updated ({len(skills)} skills)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

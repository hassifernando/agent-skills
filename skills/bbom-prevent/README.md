# bbom-prevent

A Claude skill that keeps a codebase from turning into a Big Ball of Mud, **continuously**. Companion to `bbom-audit` (one-off diagnosis); this one prevents the degradation.

Persistence comes from the project, not the skill: a `.bbom/` ratchet (baseline + boundary rules) enforced by `scripts/bbom_check.py` in CI, pre-commit or a Claude Code hook, plus an `ARCHITECTURE.md`, ADRs and an instruction snippet so every future session follows the same rules.

- `SKILL.md`: set up, before-you-change guard, after-you-change check, drift report.
- `references/`: guard checklist, rules schema, wiring (CI / pre-commit / hook).
- `assets/`: ARCHITECTURE.md, ADR template, agent-instructions snippet.
- `scripts/bbom_check.py`: stdlib-only `init | check | ratchet | accept`. Enforces a size ceiling, forbidden-import boundaries, **import cycles (Python, JS/TS)** and top-level directory sprawl. Tested on Python 3.9 to 3.14 (`python3 -m unittest scripts/test_bbom_check.py`).
- `evals/`: test cases (`claude plugin eval .`).

## What it does not do
Cycles are detected for Python and JS/TS only (other languages are reported as "not analysed", never as clean). Boundaries are line-by-line regexes. It does not measure cohesion or semantic duplication; that is the judgment step before a change, and the `bbom-audit` skill covers a full diagnosis.

## Use it actively
Install the steering file (`assets/kiro-steering.md` -> `.kiro/steering/architecture.md` in Kiro, or the snippet in `CLAUDE.md`/`AGENTS.md` elsewhere) so every session is told to use the skill, wire `scripts/bbom_check.py` into CI or a hook, and invoke it by hand with `/bbom-prevent` when you start structural work.

## Install
Copy the folder to your harness's skills directory: `.kiro/skills/bbom-prevent/` or `~/.kiro/skills/` (Kiro), `.claude/skills/` or `~/.claude/skills/` (Claude Code).

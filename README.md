# agent-skills

Portable [Agent Skills](https://agentskills.io) (the open `SKILL.md` format) for architecture work. Each skill is a self-contained folder under `skills/` and uses only the Python standard library for its helper scripts.

| Skill | What it does |
|---|---|
| [`bbom-audit`](skills/bbom-audit) | Read-only architecture audit. Decides whether a codebase is a Big Ball of Mud, scores ten dimensions, ranks risks with file-level evidence and proposes a staged recovery plan. Never modifies the project. |
| [`bbom-prevent`](skills/bbom-prevent) | Keeps a codebase from degrading, across sessions. Sets up a `.bbom/` ratchet (size ceiling, forbidden-import boundaries, import cycles for Python and JS/TS, top-level directory sprawl), `ARCHITECTURE.md` and ADRs, and checks every structural change against them. |

The two are companions: audit once to learn where you stand, then prevent regressions.

## Sample output

This is an excerpt from `bbom-audit` run on a deliberately messy 36-line Flask/SQLite fixture (`skills/bbom-audit/evals/audits-messy-toy-shop`). The full report has 14 sections plus a summary for external review; the skill writes it in the language you use.

> **Is it a big ball of mud? Not yet, and not systemically.** With four files and 36 lines, a person can hold the whole system in their head. It is better described as a **partially disorganized architecture in miniature**: no protected core, and it already shows the BBoM seeds (a circular dependency, one business rule copied three times with three different thresholds, persistence reached from every layer, swallowed errors, zero tests). Confidence in the classification: **medium**.
>
> - **Risk index:** 70.4 / 100, band **Elevated** (9 dimensions assessed; heuristic on an ordinal scale, not comparable across projects).
> - **Findings:** 9 total. Critical 1, high 5, medium 2, low 1. Labels: 8 Confirmed, 1 Probable, 0 Unverified.
> - **Not recommended:** a rewrite, microservices, or Clean Architecture/DDD scaffolding. For 36 lines that is cost without benefit.
>
> **ARQ-04 VIP discount: three divergent copies, can apply twice** (critical, Confirmed). `orders.py:7` discounts above 100, `billing.py:6` above 120, `app.py:9` above 80 (dead branch). `place_order` passes the already-discounted total to `charge`, which discounts again, so the stored order total and the debited amount disagree.

Every finding carries a label (Confirmed, Probable, Unverified) and what could not be measured is listed under "Information gaps" instead of being guessed.

## Install

Copy the skill folder you want into your harness's skills directory. The folder name must match the skill `name`.

**Kiro**
- Workspace: `.kiro/skills/<skill>/`. Global (IDE only): `~/.kiro/skills/<skill>/`.
- Importing from GitHub: point the import at the skill's subdirectory (for example `skills/bbom-audit`), not the repository root.
- Custom Kiro agents do not load skills by default. Add a `skill://` URI to the agent's `resources`.
- For `bbom-prevent`, copy `assets/kiro-steering.md` to `.kiro/steering/architecture.md` so every session is told to use the skill.

**Claude Code**
- Project: `.claude/skills/<skill>/`. Personal: `~/.claude/skills/<skill>/`.

**Other harnesses** that read the Agent Skills format should work the same way; only Kiro and Claude Code have been checked.

```sh
git clone https://github.com/hassifernando/agent-skills.git
cp -r agent-skills/skills/bbom-audit   your-project/.kiro/skills/
cp -r agent-skills/skills/bbom-prevent your-project/.kiro/skills/
```

## Requirements

`python3` (standard library only) and, optionally, `git`.

## Tests

```sh
cd skills/bbom-prevent
python3 -m unittest scripts/test_bbom_check.py
```

## Layout

```
skills/
  bbom-audit/     SKILL.md, references/, scripts/repo_stats.py, evals/
  bbom-prevent/   SKILL.md, references/, assets/, scripts/bbom_check.py, evals/
```

## License

[MIT](LICENSE)

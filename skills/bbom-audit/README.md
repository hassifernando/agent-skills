# bbom-audit

A Claude skill that runs a **read-only architecture audit** and decides whether a codebase is a Big Ball of Mud. It scores ten dimensions, ranks the top risks with file-level evidence and proposes a staged recovery plan, without modifying the project.

- `SKILL.md`: the workflow and ground rules.
- `references/`: the ten dimensions, BBoM signals, scoring method, report template.
- `scripts/repo_stats.py`: stdlib-only, read-only metrics (languages, largest files, git churn, co-change, test ratio, CI/docs/agent-file presence).
- `evals/`: test cases (`claude plugin eval .` runs them).

Install: copy this folder to your harness's skills directory (`.kiro/skills/`, `~/.kiro/skills/`, `.claude/skills/`, `~/.claude/skills/`). Companion skill: `bbom-prevent`, which keeps the structure from degrading after the audit.

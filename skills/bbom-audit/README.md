# bbom-audit

Read-only architecture audit. It decides whether a codebase is a Big Ball of Mud (BBoM), scores ten dimensions, ranks the top risks with file-level evidence and proposes a staged recovery plan. It never modifies the project: the only file it writes is the report, at the path you give.

Companion skill: [`bbom-prevent`](../bbom-prevent), which keeps the structure from degrading after the audit.

## What is inside

- `SKILL.md`: the workflow and ground rules.
- `references/`: the ten dimensions, BBoM signals, scoring method, report template.
- `scripts/repo_stats.py`: stdlib-only, read-only metrics (languages, largest files, git churn, co-change, test ratio, CI/docs/agent-file presence).
- `evals/`: test cases.

## Use it

Ask in plain language:

```text
Do an architecture audit of this project and tell me if it's a big ball of mud. Write the report to ./audit-report.md.
```

The report follows 14 sections plus a self-contained "Summary for External Review", in the language of your request. Every finding is labeled Confirmed, Probable or Unverified. What could not be measured is listed under "Information gaps".

## Sample output

An excerpt from a run on a deliberately messy 36-line Flask/SQLite fixture (`evals/audits-messy-toy-shop`):

> **Is it a big ball of mud? Not yet, and not systemically.** With four files and 36 lines, a person can hold the whole system in their head. It is better described as a **partially disorganized architecture in miniature**: no protected core, and it already shows the BBoM seeds (a circular dependency, one business rule copied three times with three different thresholds, persistence reached from every layer, swallowed errors, zero tests). Confidence in the classification: **medium**.
>
> - **Risk index:** 70.4 / 100, band **Elevated** (9 dimensions assessed; heuristic on an ordinal scale, not comparable across projects).
> - **Findings:** 9 total. Critical 1, high 5, medium 2, low 1. Labels: 8 Confirmed, 1 Probable, 0 Unverified.
> - **Not recommended:** a rewrite, microservices, or Clean Architecture/DDD scaffolding. For 36 lines that is cost without benefit.
>
> **ARQ-04 VIP discount: three divergent copies, can apply twice** (critical, Confirmed). `orders.py:7` discounts above 100, `billing.py:6` above 120, `app.py:9` above 80 (dead branch). `place_order` passes the already-discounted total to `charge`, which discounts again, so the stored order total and the debited amount disagree.

This excerpt comes from the first eval run, before cycle detection and a fix that makes the summary use the final index.

## Instructions for AI agents

1. The user asks for an architecture audit, or whether a codebase is a Big Ball of Mud.
2. Follow `SKILL.md` in this folder. In short: run `scripts/repo_stats.py <repo> --json <out.json>` (write the JSON outside the project), read the code, score the ten dimensions with `references/`, verify each finding, then write the report.
3. Write the report in the language the user wrote in. Keep paths and code unchanged.
4. Never modify the audited project. Never copy secret values from `.env` or similar files.
5. Label every finding Confirmed, Probable or Unverified. List what could not be measured. Do not invent numbers.

## Install

See [the repository README](../../README.md#quick-start). Copy this whole folder, not only `SKILL.md`.

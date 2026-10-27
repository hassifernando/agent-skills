# bbom-prevent

Keeps a codebase from turning into a Big Ball of Mud, **continuously**. Companion to [`bbom-audit`](../bbom-audit) (one-off diagnosis). This one prevents the degradation.

Persistence comes from the project, not the skill: a `.bbom/` ratchet (baseline plus boundary rules) enforced by `scripts/bbom_check.py` in CI, pre-commit or an agent hook, plus an `ARCHITECTURE.md`, ADRs and an instruction snippet so every future session follows the same rules.

<p align="center">
  <img src="docs/how-it-works.svg" alt="Flow: bbom-audit writes a report, bbom-prevent sets up a baseline, a check runs after every change, and ratchet lowers the baseline when things improve" width="100%">
</p>

## What is inside

- `SKILL.md`: set up, before-you-change guard, after-you-change check, drift report.
- `references/`: guard checklist, rules schema, wiring (CI, pre-commit, agent hooks).
- `assets/`: `ARCHITECTURE.md`, ADR template, agent-instructions snippet, Kiro steering file.
- `scripts/bbom_check.py`: stdlib-only `init | check | ratchet | accept`. Enforces a size ceiling, forbidden-import boundaries, **import cycles (Python, JS/TS)** and top-level directory sprawl. Tests: `python3 -m unittest scripts/test_bbom_check.py`.
- `evals/`: test cases.

## Use it

```text
Set up bbom-prevent for this project. Show me the boundary rules and what files you will create before writing anything.
```

Then, before structural work: `I'm adding a payments module. Run the bbom-prevent before-you-change step first.` After a change: `Run the architecture check and tell me if my change made the structure worse.`

By hand, `/bbom-prevent` invokes it where the harness has slash commands. To make it active without being asked, install the steering file or snippet and wire `scripts/bbom_check.py` into CI or a hook (see `references/wiring.md`).

## What it does not do

Cycles are detected for Python and JS/TS only. Other languages are reported as "not analysed", never as clean. Boundaries are line-by-line regexes. It does not measure cohesion or semantic duplication. That is the judgment step before a change, and `bbom-audit` covers a full diagnosis.

## Instructions for AI agents

1. Before any structural change (new module, abstraction, dependency, cross-module import, or editing a file over the size ceiling), follow the "Before you change" step in `SKILL.md`.
2. Setup runs `python3 scripts/bbom_check.py init <repo>`, which writes `.bbom/rules.json` and `.bbom/baseline.json`. Ask the user before creating files in their project. Review the boundary rules with them.
3. After every change run `python3 <path>/bbom_check.py check <repo>` and report the result. Exit code 1 means the structure got worse than the baseline.
4. Never edit `.bbom/baseline.json` and never loosen `.bbom/rules.json` to make a check pass. If a regression is deliberate, use `accept --reason "..."` and add an ADR.
5. Start any hook non-blocking (`|| true`). Make it blocking only after the baseline has been quiet on real work.

## Install

See [the repository README](../../README.md#quick-start). Copy this whole folder, not only `SKILL.md`.

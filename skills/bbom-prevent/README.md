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

### Install and set up in one prompt

Check that `git status` is clean, open your agent in the project root, and paste. If you already ran [`bbom-audit`](../bbom-audit) and have an `audit-report.md`, the agent bases the boundary rules on it.

```text
Install the bbom-prevent skill from https://github.com/hassifernando/agent-skills and set it up for this project.

STEP 1: Install
- Clone the repository into a temporary directory outside this project, then read AGENTS.md from that clone and follow it.
- Copy skills/bbom-prevent, the whole folder, into the skills directory of the harness I am using: .claude/skills/ for Claude Code, .kiro/skills/ for Kiro. If you are not sure which harness this is, ask me.
- Run the verification steps from AGENTS.md and show me the real output.

STEP 2: Set up the ratchet (I authorize these writes, and only these)
- Use the bbom-prevent skill. If ./audit-report.md exists, base the boundary rules in .bbom/rules.json on it. Otherwise base them only on imports you verified in the code. Do not invent boundaries.
- Create: .bbom/, docs/ARCHITECTURE.md, docs/adr/, and tools/bbom_check.py (copied from the skill).
- Claude Code: append the snippet from skills/bbom-prevent/assets/agent-instructions-snippet.md to CLAUDE.md (create it if missing), and add a Stop hook to .claude/settings.json that runs "python3 tools/bbom_check.py check . --stop-hook". If that file exists, merge into it and keep what is there.
- Kiro: copy skills/bbom-prevent/assets/kiro-steering.md to .kiro/steering/architecture.md, and create .kiro/hooks/bbom-check.json following the Kiro section of skills/bbom-prevent/references/wiring.md. Do not touch existing hooks.
- The Claude Code hook uses --stop-hook: it blocks the stop once with the report on stderr and cannot loop. The Kiro hook stays non-blocking (|| true) because Kiro's exit-code behavior is not verified.
- Run "python3 tools/bbom_check.py check ." once and show me the output.

RULES
- Do not commit or push anything, and do not change any file outside the list above.
- Do not edit .bbom/baseline.json by hand or loosen the rules to make a check pass.
- Never copy secret values from .env or similar files into any file.

FINISH with: the files created or changed (from git status), the boundary rules you wrote marked as a first draft I must review, whether you could confirm the hook format, and how the Claude Code hook behaves (blocks once per attempt) and what the Kiro hook does.
```

Review `.bbom/rules.json` with your team before trusting it. In Kiro CLI, use an agent that has a `tools` field (see the [repository README](../../README.md#kiro-cli-notes)).

## What it does not do

Cycles are detected for Python and JS/TS only. Other languages are reported as "not analysed", never as clean. A file that cannot be parsed is reported as "NOT parsed" and keeps `ratchet` from lowering the cycle baseline. `cycle_scope: "load-time"` applies to Python only. Symlinks are never followed. Boundaries are line-by-line regexes. It does not measure cohesion or semantic duplication. That is the judgment step before a change, and `bbom-audit` covers a full diagnosis.

## Instructions for AI agents

1. Before any structural change (new module, abstraction, dependency, cross-module import, or editing a file over the size ceiling), follow the "Before you change" step in `SKILL.md`.
2. Setup runs `python3 scripts/bbom_check.py init <repo>`, which writes `.bbom/rules.json` and `.bbom/baseline.json`. Ask the user before creating files in their project. Review the boundary rules with them.
3. After every change run `python3 <path>/bbom_check.py check <repo>` and report the result. Exit code 1 means the structure got worse than the baseline.
4. Never edit `.bbom/baseline.json` and never loosen `.bbom/rules.json` to make a check pass. If a regression is deliberate, use `accept --reason "..."` and add an ADR.
5. Claude Code: wire the Stop hook with `check . --stop-hook` (exit 2 and stderr block the stop once, then it lets go). Kiro: keep the hook non-blocking (`|| true`) until you have seen how your version treats exit codes.

## Install

See [the repository README](../../README.md#quick-start). Copy this whole folder, not only `SKILL.md`.

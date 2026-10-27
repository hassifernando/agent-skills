---
name: bbom-prevent
license: MIT
compatibility: Requires python3 (standard library only) and, optionally, git. Follows the open Agent Skills format. Evals were run in Claude Code; other harnesses are untested.
description: Keeps a codebase from degrading into a Big Ball of Mud, continuously, across sessions. Before any structural change (new module, new abstraction, new dependency, new feature spanning layers, moving or splitting code) it runs a short placement-and-duplication check; after the change it runs an architecture ratchet that fails when files grow past their ceiling, module boundaries are crossed or the tree sprawls. Sets up persistent guardrails in the project (.bbom/ baseline and rules, architecture rules, ADRs, CI/pre-commit/hook wiring). Use when starting work in a project that should stay maintainable, when the user says "add a feature", "create a new module/service/helper", "where should this go?", "refactor", "keep the architecture clean", "prevent technical debt", "set up architecture guardrails/fitness functions", or when an AI agent is making many changes to the same codebase, even if they never mention Big Ball of Mud. Not for a one-off diagnosis of an existing mess (use bbom-audit for that).
---

# BBoM Prevent

A Big Ball of Mud is not built in one commit. It is built by hundreds of changes that each looked reasonable: one more helper beside the three that exist, one more import across a boundary, one more branch in the 3,000-line file. This skill makes each change answer to the structure, and moves the memory of that structure out of anyone's head and into the repository, where it survives between sessions and between agents.

A skill only runs when it is loaded, so persistence comes from two things in the project, not from this text:
- **Files** (`.bbom/rules.json`, `.bbom/baseline.json`, architecture rules and ADRs) that record the intended structure.
- **An automatic check** (`scripts/bbom_check.py`) wired to CI, pre-commit or an agent hook (Claude Code, Kiro, etc.), which enforces it when nobody is thinking about it.

## Which mode applies

- **No `.bbom/` in the project yet** -> run *Set up* once (see below), with the user's go-ahead.
- **About to change structure** -> run *Before you change* (a few minutes of reading, no tooling needed).
- **Just changed code** -> run *After you change*.
- **User asks how the project is doing** -> run *Drift report*.

"Structural" means: adding a file or directory, a new class/function that does something similar to existing code, a new import across modules, a new dependency, a new config or table, moving or splitting code, or touching a file already over the size ceiling. A one-line bug fix inside one function does not need the ceremony; the After check still takes seconds.

## Set up (once per project)

Ask first: this writes files into the project.

1. Run `python3 scripts/bbom_check.py init <repo>` (path relative to this skill's folder; use the absolute path of wherever the harness installed it, or the copy in the project). It records today's state as the baseline: which files are already too big, which boundary violations and import cycles already exist, which top-level directories exist. Existing mess is *grandfathered*, not hidden, so the check can be strict about anything new from day one without demanding a rewrite.
2. Open `.bbom/rules.json` and replace the example boundary with the project's real ones (read `references/rules-schema.md`). Boundaries are the part that needs a human: "the listener must not import the API layer", "UI code never touches the database". Propose them from what the code already shows (the dominant direction of imports), and let the user confirm. A wrong boundary is worse than none because people learn to override it.
3. Create the architecture rules and decision log from `assets/` (`ARCHITECTURE.md`, `adr-template.md`) in the project's docs folder, adapted to its language and layout. Keep `ARCHITECTURE.md` short: a map of modules and the allowed direction of dependencies.
4. Add the snippet in `assets/agent-instructions-snippet.md` to the file this harness reads for standing project instructions (`CLAUDE.md`, `AGENTS.md`, or a Kiro steering file; see `assets/kiro-steering.md`) so every future session is told to follow this skill.
5. Wire the check so it runs without anyone remembering: see `references/wiring.md` (CI job, pre-commit, and the agent hook of your harness). Suggest one; do not install a hook into the user's settings without asking.
6. Commit `.bbom/`. The baseline is a project artifact, reviewed like code.

## Before you change (placement and duplication)

Spend the effort here, because after the code exists it is already the path of least resistance. Work through `references/guard-checklist.md`; in short:

1. **Does this already exist?** Search for the concept under its other names before writing anything. Two helpers that do the same thing, written by two sessions that did not see each other, is the most common way a codebase turns to mud. Extend the existing one or say why not.
2. **Where does it belong?** Name the module that owns this responsibility. If none does, that is a design decision to surface, not a reason to put it in the nearest file.
3. **Which way does the dependency point?** Check `ARCHITECTURE.md` and `.bbom/rules.json`. Lower layers must not learn about higher ones.
4. **Who owns this rule?** If the change adds or alters a business rule, find every place that already implements it. One owner, everyone else calls it.
5. **Is the target already too big?** If the file is in the baseline's `big_files`, add the new code in a new module and leave the old file smaller or equal, never larger.
6. **Does it need a decision record?** New top-level directory, new dependency, new cross-module contract, or a deliberate rule break -> write an ADR from the template (context, decision, consequences) before or with the change.
7. **How will we know it still works?** Name the test that protects the behavior you are about to touch; add a characterization test first if none exists.

Say what you found in two or three sentences before editing. If the honest answer is "it belongs in the big file because splitting it is out of scope", say that, and record it with `accept` rather than letting it slide.

## After you change

1. Run `python3 scripts/bbom_check.py check <repo>` (or the project's copy, `tools/bbom_check.py`).
2. On failure, fix the structure (split the file, route through the owning module, remove the import). Only if the regression is truly deliberate, run `accept --reason "..."` with a real reason; it is stored in `.bbom/baseline.json` history so the next person sees why. Never edit the baseline by hand to make the check pass, and never loosen `rules.json` for the same purpose: the check exists to be uncomfortable.
3. If it reports improvements, run `ratchet` to lock them in, so the ceiling only ever moves down.
4. If the change altered the module map, a boundary or a contract, update `ARCHITECTURE.md` in the same change. A map that lies is read first and believed.

## Drift report

When asked how the project is doing, or periodically: run `check`, then summarize how many files sit over the ceiling and whether that number is falling, grandfathered boundary violations remaining, accepted regressions in `history` and their reasons, and any signal that structure is eroding faster than it is being repaid (growing `accept` list, ratchet never lowered). If the trend is bad or the baseline has gone stale, recommend a full diagnosis with the `bbom-audit` skill rather than improvising one.

## Using it actively (do not wait to be asked)

A guard that only runs when someone remembers it is not a guard. Treat this skill as standing practice for the whole session, not as something the user must summon:

- **At the start of work in a project that has `.bbom/`**, read `.bbom/rules.json` and `docs/ARCHITECTURE.md` once, so the boundaries are in your head before the first edit.
- **Before each structural change, run *Before you change* without being prompted**, and say in two or three sentences what you found. Silence means the step was skipped.
- **After each change, run `check`** and report the result. If the project has no `.bbom/` and the work is non-trivial, suggest *Set up* once and let the user decide.
- **For the human:** in Kiro, invoke it by hand with `/bbom-prevent` (add what you are about to do after the name); keep the steering file from `assets/kiro-steering.md` in `.kiro/steering/` so every session is told to use it; and a custom Kiro agent only sees the skill if its `resources` lists a `skill://` URI for it. `references/wiring.md` has the rest (CI, pre-commit, hook).

## What the check does not do

Say these limits out loud when reporting, so a green check is not read as "the architecture is healthy":
- Import cycles are detected for Python and JS/TS only. Other languages are listed as "not analysed", never as clean. Non-relative JS imports (aliases such as `@/`) are not resolved.
- Boundaries are line-by-line regexes on source text, so they catch what they are written for and nothing else.
- It does not measure coupling beyond cycles, cohesion, or semantic duplication (two functions doing the same thing under different names). That part is the *Before you change* judgment, and a full `bbom-audit` covers it.
- The baseline is only as honest as the review of changes to `.bbom/`.

## Principles behind the rules

- **Prevention is cheaper than recovery**, but only if it is enforced where changes land. Advice that lives in a document nobody reads decays; a failing check does not.
- **Ratchet, don't demand perfection.** Grandfathering today's debt makes the check adoptable on a real project; forbidding it from growing makes the debt shrink.
- **Friction should be proportional.** The check is fast and mostly silent. The ceremony is for structural changes only. A guard that cries wolf is switched off within a week.
- **Make the deliberate exception cheap and visible**, not impossible. `accept --reason` keeps a record; a blocked developer with a deadline edits the baseline instead.
- **Do not turn this into rewriting.** The goal is that new code stops making things worse and old code improves when touched. If recovery is the real need, hand off to `bbom-audit`.

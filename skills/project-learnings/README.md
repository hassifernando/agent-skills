# project-learnings

Keeps a small, curated set of project lessons in the repository, so the next agent does not repeat a mistake or redo a long investigation. When the user corrects an agent or a problem takes real digging, the skill decides whether the lesson is worth keeping and in what form: a test or lint rule first, a code comment next, a short text entry last. Most sessions should end with nothing written.

Persistence comes from the project, not the skill: entries are plain Markdown under `docs/learnings/` (configurable), versioned and reviewed like code, plus an instruction snippet so every future session reads the index first.

## What is inside

- `SKILL.md`: the modes (capture, refresh, promote, set up), the worthiness test and the rules for running without a user.
- `references/`: `entry-format.md`, `capture.md`, `refresh.md`, `promote.md`.
- `assets/`: `config.example.json`, `index-template.md`, `agent-instructions-snippet.md`.
- `scripts/learnings_check.py`: stdlib-only, read-only. `check` validates config, entries, index, caps, dates, evidence paths and likely secrets. `candidates` lists entries that could be promoted. Tests: `python3 -m unittest scripts/test_learnings_check.py` from the skill folder.
- `evals/`: seven test cases. They have not been run in any harness yet.

## What it writes to your project

Only with your go-ahead for setup, and nothing outside the project without approval in that run.

- `.project-learnings.json` (optional): `dir`, `maxPerTopic`, `language`, `upstream`.
- `<dir>/README.md`: the index, one line per topic.
- `<dir>/<slug>.md`: one topic file, up to `maxPerTopic` entries. Each entry has the rule, why, evidence, scope and dates.
- Proposed tests, lint rules or code comments. The skill proposes them and the task makes the change; it does not edit production code on its own.
- An issue in the configured `upstream` repository, or an append to an `upstream` file, only after you approve it (promote mode).
- A short snippet in your standing agent instructions (`AGENTS.md`, `CLAUDE.md` or the equivalent) during setup.

It never records sessions on its own, installs hooks or runs a background service.

## Use it

```text
Capture what we just learned.
```

```text
Refresh the learnings.
```

```text
Promote the candidate learnings.
```

By hand, `/project-learnings` invokes it where the harness has slash commands. Another agent (an orchestrator at the end of a task, for example) can call it with no user present; it then ends with a line such as `learning: written <path>` or `learning: skipped <reason>`.

### Install and first use in one prompt

Check that `git status` is clean, open your agent in the project root, and paste.

```text
Install the project-learnings skill from https://github.com/hassifernando/agent-skills and set it up for this project.

STEP 1: Install
- Clone the repository into a temporary directory outside this project, then read AGENTS.md from that clone and follow it.
- Copy skills/project-learnings, the whole folder, into the skills directory of the harness I am using: .claude/skills/ for Claude Code, .kiro/skills/ for Kiro. If you are not sure which harness this is, ask me.
- Run the verification steps from AGENTS.md and show me the real output.

STEP 2: Set up (I authorize these writes, and only these)
- Use the project-learnings skill in set-up mode. Create <dir>/README.md from assets/index-template.md. Use the default dir (docs/learnings) unless I say otherwise. Create .project-learnings.json only if the defaults do not fit.
- Append the snippet from skills/project-learnings/assets/agent-instructions-snippet.md to AGENTS.md or CLAUDE.md (create it if missing, keep what is there), with <dir> filled in.
- Do not create any topic file yet.
- Run "python3 -I <skill folder>/scripts/learnings_check.py check" and show me the output.

RULES
- Do not commit or push anything, and do not change any file outside the list above.
- Never copy secret values from .env or similar files into any file.
- Do not set an upstream. I will configure promote later.

FINISH with: the files created or changed (from git status) and the output of the check.
```

Then, after a correction or a hard investigation: `Run the project-learnings capture step on what we just figured out.`

## What it does not do

- It does not search past sessions or keep personal preferences. Those belong to the harness's own memory.
- It does not judge content in the script: `learnings_check.py` only validates the format and warns about stale evidence. Deciding what is worth keeping is the agent's job.
- It does not install a hook or run on its own. To enforce the format, run `learnings_check.py check` in CI or a hook yourself.
- Evidence paths are checked for existence only; whether a rule still holds is found by refresh, by reading the code.

## Instructions for AI agents

1. Run capture only after a user correction, a problem that took real investigation, or an entry that proved wrong. Apply the worthiness test in `SKILL.md` first; if either answer is "no", write nothing and say why in one line.
2. Pick the medium that needs the least upkeep: a test or lint rule, then a code comment, then an entry. For the first two, propose the change and do not edit production code on your own.
3. Read `references/entry-format.md` before writing any entry. Update a duplicate instead of adding one, respect `maxPerTopic` (refresh the topic first, never raise the cap), and mark `candidate` only for rules that name nothing of the project.
4. Never put a secret, token, credential or personal data in an entry. Name the variable, not its value.
5. After any write under `<dir>/` or to `.project-learnings.json`, run `python3 -I <skill>/scripts/learnings_check.py check` and fix every `error:` line.
6. Ask the user before creating files in their project. Promote sends nothing without explicit approval in that run, and never puts learning text inside a shell string.
7. When called by another agent, ask nothing and end with one of the `learning:` lines defined in `SKILL.md`.

## Inspiration

The text and the script in this skill are original; only ideas were reused.

- [blader/napkin](https://github.com/blader/napkin): a curated runbook, not a session log, with a cap on items per category.
- [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (its `ce-compound` skill): a worthiness test before writing, choosing the lowest-upkeep medium for the lesson, and a refresh that prunes what went stale.
- [affaan-m/ECC](https://github.com/affaan-m/ECC) (its `continuous-learning-v2` skill): promoting what was learned in one project to a place that serves many.

## Install

See [the repository README](../../README.md#quick-start). Copy this whole folder, not only `SKILL.md`.

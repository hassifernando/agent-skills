# Instructions for AI agents

This file tells an AI coding agent how to install and use the skills in this repository. Follow the steps in order. Do not skip the verification steps.

## What this repository is

Two Agent Skills (open `SKILL.md` format). Each one is a self-contained folder:

| Folder | Use it when the user wants to... | Writes to the user's project? |
|---|---|---|
| `skills/bbom-audit/` | know whether a codebase is a Big Ball of Mud and how healthy its architecture is | No. Read-only. The only file it writes is the report, at the path the user gives. |
| `skills/bbom-prevent/` | stop a codebase from getting structurally worse, or check a change against the structure rules | Yes, only after the user agrees: `.bbom/`, `docs/ARCHITECTURE.md`, `docs/adr/`, an instructions snippet, optionally a hook. |

Requirements: `python3` (standard library only). `git` is optional.

## Install a skill into a project

1. Ask the user which skill or skills to install, and which agent harness they use. If they do not say, ask. Do not guess.
2. Copy the skill **folder** (not only `SKILL.md`) into the harness's skills directory. The folder name must stay equal to the skill name.

| Harness | Project directory | Notes |
|---|---|---|
| Kiro (IDE and CLI) | `.kiro/skills/<skill>/` | `~/.kiro/skills/` is IDE only. For the CLI, use the project directory. |
| Claude Code | `.claude/skills/<skill>/` | Personal: `~/.claude/skills/<skill>/`. |
| Any other harness | see that harness's documentation | Not tested here. Do not assume the path. |

Example (Kiro or Claude Code, run from the project root):

```sh
mkdir -p .kiro/skills
cp -R /path/to/agent-skills/skills/bbom-audit .kiro/skills/
cp -R /path/to/agent-skills/skills/bbom-prevent .kiro/skills/
```

3. Remove nothing from the copied folder. Do not edit `SKILL.md` unless the user asks.

## Kiro CLI: custom agents and tools

- The default Kiro agent loads skills from `.kiro/skills/` automatically.
- A custom agent must list the skills in `resources`, and **must have a `tools` field**. An agent file with `allowedTools` but no `tools` made the model announce actions and stop without running any tool. Do not edit the user's existing agent files. Propose a change and wait for approval, or create a separate project agent.

```json
{
  "name": "bbom-agent",
  "tools": ["*"],
  "allowedTools": ["@builtin"],
  "resources": ["file://.kiro/steering/**/*.md", "skill://.kiro/skills/*/SKILL.md"]
}
```

Save it as `.kiro/agents/bbom-agent.json` and start it with `kiro-cli chat --agent bbom-agent`.

## Verify the install

Run these and report the real output to the user. Do not claim success without them.

1. Check the folder: `ls <skills-dir>/bbom-audit/SKILL.md <skills-dir>/bbom-prevent/SKILL.md`. Expected: both paths printed, no error.
2. Check the scripts run: `python3 <skills-dir>/bbom-audit/scripts/repo_stats.py --help` and `python3 <skills-dir>/bbom-prevent/scripts/bbom_check.py --help`. Expected: a usage message, exit code 0.
3. Check discovery: ask the agent for an architecture audit of a small project. The agent should name `bbom-audit` and read its `SKILL.md` first.

## Use `bbom-audit`

1. The user asks for an architecture audit, or asks whether a codebase is a Big Ball of Mud.
2. Follow `SKILL.md` in the skill folder. In short: run `scripts/repo_stats.py <repo> --json <out.json>` (write the JSON outside the project), read the code, score ten dimensions with `references/`, verify each finding, then write the report.
3. Write the report in the language the user wrote in. Keep paths and code unchanged.
4. Never modify the audited project. Never copy secret values from `.env` or similar files.
5. Label every finding Confirmed, Probable or Unverified. List what could not be measured. Do not invent numbers.

## Use `bbom-prevent`

1. Before any structural change (new module, abstraction, dependency, cross-module import, or editing a file over the size ceiling), follow the "Before you change" step in `SKILL.md`.
2. Setup runs `python3 scripts/bbom_check.py init <repo>`, which writes `.bbom/rules.json` and `.bbom/baseline.json`. Ask the user before creating files in their project. Review the boundary rules with them.
3. After every change run `python3 <path>/bbom_check.py check <repo>` and report the result. Exit code 1 means the structure got worse than the baseline.
4. Never edit `.bbom/baseline.json` and never loosen `.bbom/rules.json` to make a check pass. If a regression is deliberate, use `accept --reason "..."` and add an ADR.
5. Start any hook non-blocking (`|| true`). Make it blocking only after the baseline has been quiet on real work.

## Rules for working in this repository

- Code, documentation, skills and commit messages are written in English.
- Do not create a GitHub repository, push, tag or publish unless the user asks in that same message.
- Keep each skill `description` at or below 1024 characters. `bbom-prevent` is close to the limit; do not grow it.
- Run the tests before committing: `cd skills/bbom-prevent && python3 -m unittest scripts/test_bbom_check.py`. Expected: `OK`.
- `HANDOFF.md` and `*-workspace/` are local only and are ignored by git.

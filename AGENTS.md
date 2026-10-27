# Instructions for AI agents

This file tells an AI coding agent how to install, verify, use and add the skills in this repository. Follow the steps in order. Do not skip the verification steps.

## What this repository is

A collection of Agent Skills (open `SKILL.md` format). Each skill is a self-contained folder under `skills/<name>/`. The list of skills is the table in `README.md`, generated from each skill's `SKILL.md`. Each skill's own `README.md` says what it writes to the user's project, with example prompts and instructions for agents.

Requirements for the skills' scripts: `python3` (standard library only). `git` is optional.

## Install a skill into a project

1. Ask the user which skills to install, and which agent harness they use. If they do not say, ask. Do not guess.
2. Read `skills/<name>/README.md` for each chosen skill, so you know what it will write to the user's project.
3. Copy the skill **folder** (not only `SKILL.md`) into the harness's skills directory. The folder name must stay equal to the skill name.

| Harness | Project directory | Notes |
|---|---|---|
| Kiro (IDE and CLI) | `.kiro/skills/<skill>/` | Kiro's skills page lists `~/.kiro/skills/` as supported in the IDE and the CLI, but only the project directory was tested here. Prefer the project directory. |
| Claude Code | `.claude/skills/<skill>/` | Personal: `~/.claude/skills/<skill>/`. |
| Any other harness | see that harness's documentation | Not tested here. Do not assume the path. |

Example (run from the project root, with the repository cloned outside the project):

```sh
mkdir -p .claude/skills
cp -R /path/to/agent-skills/skills/<skill-name> .claude/skills/
```

4. Remove nothing from the copied folder. Do not edit `SKILL.md` unless the user asks.

## Kiro CLI: custom agents and tools

- The default Kiro agent loads skills from `.kiro/skills/` automatically.
- Kiro's docs disagree on whether a custom agent gets skills by default (skills page: no; configuration reference: it inherits default resources). List the skills in `resources`; that is safe either way.
- A custom agent should have a `tools` field. On `kiro-cli` 2.34.2, an agent file with `allowedTools` but no `tools` made the model announce actions and stop without running any tool. The configuration reference calls `allowedTools` a CLI 2.x field and says CLI 3.0 uses `permissions.rules`, so re-check after upgrading. Do not edit the user's existing agent files. Propose a change and wait for approval, or create a separate project agent.

```json
{
  "name": "my-agent",
  "tools": ["*"],
  "allowedTools": ["@builtin"],
  "resources": ["file://.kiro/steering/**/*.md", "skill://.kiro/skills/*/SKILL.md"]
}
```

Save it as `.kiro/agents/my-agent.json` and start it with `kiro-cli chat --agent my-agent`.

## Verify the install

Run these and report the real output to the user. Do not claim success without them.

1. Check each installed skill: `ls <skills-dir>/<skill>/SKILL.md`. Expected: the path printed, no error.
2. For each script the skill ships under `scripts/`, run `python3 <skills-dir>/<skill>/scripts/<script>.py --help`. Expected: a usage message, exit code 0.
3. Check discovery: ask for a task the skill covers (the skill's README has example prompts). The agent should name the skill and read its `SKILL.md` first.

## Use a skill

1. Match the user's request to a skill by its `description` in `SKILL.md`.
2. Read that skill's `SKILL.md` and follow it. Read its `references/` files only when `SKILL.md` points to them.
3. Follow the "Instructions for AI agents" section in the skill's `README.md`.
4. Ask before writing anything the skill's README says it writes to the user's project. Never commit, push or publish on the user's behalf unless they ask in that message.

## Add a skill to this repository

1. Create `skills/<name>/SKILL.md`. The folder name must equal `name`. Frontmatter needs `name`, `description` (1 to 1024 characters), `license: MIT`, and `metadata` with `category` and `version` (a quoted string, for example `"0.1.0"`).
2. Add `skills/<name>/README.md` with what the skill does, what it writes to the user's project, example prompts, ready-to-paste prompts (install plus first use), and an "Instructions for AI agents" section. Put any diagram or sample output in `skills/<name>/docs/`. Do not edit `docs/banner.svg` for a new skill.
3. Run `python3 scripts/build_catalog.py`. It rewrites the skills table in `README.md` and fails if a skill is invalid. Then run `python3 scripts/build_catalog.py --check`. Expected: `catalog up to date`.
4. Run the tests: `cd scripts && python3 -m unittest test_build_catalog`, plus the tests of any skill you changed. Expected: `OK`.
5. Stop here. Commit only if the user asked for a commit in that message, and create a release tag (`<name>-v<version>`) only if they asked for the tag.

## Rules for working in this repository

- Code, documentation, skills and commit messages are written in English.
- Do not create a GitHub repository, push, tag or publish unless the user asks in that same message.
- Keep each skill `description` at or below 1024 characters. `bbom-prevent` is close to the limit. Do not grow it.
- `HANDOFF.md` and `*-workspace/` are local only and are ignored by git.

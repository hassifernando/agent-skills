# Wiring the check so it runs without anyone remembering

A check that depends on someone remembering to run it is documentation. Pick at least one trigger that fires on its own; two is better (a fast local one and CI as the backstop). Copy `scripts/bbom_check.py` into the project (e.g. `tools/bbom_check.py`) so CI does not depend on the skill being installed.

## CI (the backstop; cannot be skipped by one person)

GitHub Actions:
```yaml
name: architecture
on: [pull_request]
jobs:
  bbom:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python3 tools/bbom_check.py check .
```
Make it a required status check so `accept` has to be visible in the diff of `.bbom/baseline.json`, where a reviewer sees the reason.

## Pre-commit (fast feedback before the code leaves the machine)

`.git/hooks/pre-commit` (or your hook manager of choice):
```sh
#!/bin/sh
python3 tools/bbom_check.py check . || exit 1
```

## Agent hook (catches agent-made changes as they happen)

Hooks are harness-specific; the command they run is always the same, `python3 tools/bbom_check.py check .`.

### Claude Code

In `.claude/settings.json`, run the check when the agent finishes a turn, so a degrading change is flagged while the context is still fresh:
```json
{
  "hooks": {
    "Stop": [
      { "hooks": [ { "type": "command", "command": "python3 tools/bbom_check.py check . --stop-hook" } ] }
    ]
  }
}
```
`--stop-hook` follows Claude Code's hook contract ([hooks reference](https://code.claude.com/docs/en/hooks)): on a regression the script exits **2** and writes the report to **stderr**, which stops the agent from finishing and hands it the report. A plain exit 1 does not block a Stop event, and neither does stdout, so `check . || true` would run the check but never tell the agent. The script reads the hook input and exits 0 when `stop_hook_active` is true (the agent is already continuing because of this hook), so it blocks once per attempt and cannot loop. It only blocks when the baseline got worse, so right after `init` it is quiet. If you prefer observation only, rely on CI or pre-commit: a hook that cannot block has no way to reach the model.

### Kiro (IDE and CLI)
To make the skill active rather than on-demand, combine three things: the steering file (always included, tells every session to use the skill), the hook (runs the check without anyone asking), and the skill itself, installed in the **workspace**. By hand, `/bbom-prevent` invokes it.

Where things live (from Kiro's docs):
Sources are Kiro's pages on [skills](https://kiro.dev/docs/skills/), [steering](https://kiro.dev/docs/steering/) and the [agent configuration reference](https://kiro.dev/docs/custom-agents/configuration-reference/), read 2026-10-27. Only the custom-agent file below was tested, on `kiro-cli` 2.34.2. Kiro CLI 3.0 was announced with changes (the configuration reference says `allowedTools` is the CLI 2.x field and V3 profiles use `permissions.rules`), so re-check after upgrading.
- Skills: `.kiro/skills/<name>/` in the project is listed as supported in the IDE and the CLI. The skills page lists `~/.kiro/skills/` (global) as IDE only, so use the workspace copy if the CLI must see it.
- Steering: copy `assets/kiro-steering.md` to `.kiro/steering/architecture.md`. The steering page lists workspace steering for the IDE and the CLI, and global steering (`~/.kiro/steering/`) for the IDE and the CLI too. It also says that in CLI V1/V2 only `inclusion: always` files load automatically, which is what this file uses.
- Custom agents: the default agent loads skills on its own. For a custom agent the docs disagree: the skills page says custom agents do not load skills by default, while the configuration reference says they inherit default resources (steering, skills, `AGENTS.md`) unless `chat.disableInheritingDefaultResources` is set. Listing both in `resources` is safe in either case. A complete agent file, `.kiro/agents/<name>.json`, that was tested running `bbom-audit` in `kiro-cli` 2.34.2:
```json
{
  "name": "bbom-agent",
  "description": "Runs the bbom skills",
  "tools": ["*"],
  "allowedTools": ["@builtin"],
  "toolsSettings": { "shell": { "autoAllowReadonly": true }, "write": { "allowedPaths": ["**"] } },
  "resources": [
    "file://.kiro/steering/**/*.md",
    "skill://.kiro/skills/*/SKILL.md"
  ]
}
```
Start it with `kiro-cli chat --agent bbom-agent`. Always include `"tools"`: in testing on 2.34.2, an agent file that had `allowedTools` but no `tools` field made the model announce actions ("Let me read the skill") and stop without executing any. If the agent only narrates and never acts, check that field first.
- Hook: a file `.kiro/hooks/bbom-check.json` (workspace hooks work in the IDE and the CLI). The format below follows the example in Kiro's hooks page; `PostFileSave` runs after the agent saves or edits a file. Kiro's docs do not say what a non-zero exit does, so keep `|| true` until you have seen how it behaves in your version.
```json
{
  "version": "v1",
  "hooks": [
    {
      "name": "bbom-check",
      "trigger": "PostFileSave",
      "matcher": "\\.(py|js|jsx|ts|tsx|mjs|cjs)$",
      "action": { "type": "command", "command": "python3 tools/bbom_check.py check . || true" }
    }
  ]
}
```
Not verified: whether your Kiro CLI version reads standalone `.kiro/hooks/*.json` files (the docs describe older 2.x agents keeping hooks inside the agent JSON, convertible with `/upgrade-agent`), and the complete list of trigger names. If the hook does not fire, create it from Kiro's hooks panel or check the version, and rely on CI or pre-commit meanwhile.

### Codex, Cursor, Copilot, Gemini CLI and others
Put the snippet from `assets/agent-instructions-snippet.md` in the instructions file the tool reads (check its docs; `AGENTS.md` is a common choice), and rely on CI or pre-commit for enforcement. Those two triggers do not depend on any harness.

Only add any of these with the user's agreement, and tell them which file you changed.

## Keeping it honest
- Review `.bbom/baseline.json` changes in every PR: it should shrink, or grow only with a reason in `history`.
- Run `ratchet` whenever a refactor lowers a number, in the same commit, so the gain cannot be spent again.
- If `accept` entries pile up, that is the signal the structure is eroding; run a full `bbom-audit`.

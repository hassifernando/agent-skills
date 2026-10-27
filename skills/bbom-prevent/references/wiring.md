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
      { "hooks": [ { "type": "command", "command": "python3 tools/bbom_check.py check . || true" } ] }
    ]
  }
}
```
Drop the `|| true` to make a failure block the stop and feed the message back to the agent. Start without it, and make it blocking only after the baseline has proven quiet on real work; a noisy blocking hook gets removed.

### Kiro
To make the skill active rather than on-demand, combine three things: the steering file below (always included, tells every session to use the skill), the hook (runs the check without anyone asking), and, for custom Kiro agents, a `skill://` entry in `resources` since they do not load skills by default. By hand, `/bbom-prevent` invokes it.

Kiro keeps agent hooks as files in `.kiro/hooks/` (create one from Kiro's hooks panel rather than hand-writing the JSON, since the schema is Kiro's). Choose a trigger that fires after the agent changes files (for example on file save, or after a tool use) and make the action run the command above. For standing instructions use a steering file: copy `assets/kiro-steering.md` to `.kiro/steering/architecture.md`. Skills live in `.kiro/skills/<name>/` (workspace) or `~/.kiro/skills/` (global, IDE only); a custom Kiro agent only sees a skill if its `resources` lists a `skill://` URI for it.

### Codex, Cursor, Copilot, Gemini CLI and others
Put the snippet from `assets/agent-instructions-snippet.md` in the file the tool reads (`AGENTS.md` for most), and rely on CI or pre-commit for enforcement. Those two triggers do not depend on any harness.

Only add any of these with the user's agreement, and tell them which file you changed.

## Keeping it honest
- Review `.bbom/baseline.json` changes in every PR: it should shrink, or grow only with a reason in `history`.
- Run `ratchet` whenever a refactor lowers a number, in the same commit, so the gain cannot be spent again.
- If `accept` entries pile up, that is the signal the structure is eroding; run a full `bbom-audit`.

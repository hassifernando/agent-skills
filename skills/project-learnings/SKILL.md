---
name: project-learnings
license: MIT
compatibility: Requires python3 (standard library only); git is optional; gh is needed only to promote to a GitHub issue. Follows the open Agent Skills format. Other harnesses are untested.
description: Keeps a small, curated set of project lessons in the repository so the next agent does not repeat a mistake or redo a long investigation. Capture decides whether a lesson is worth keeping and which medium holds it with the least upkeep (an automated guard such as a test or lint rule first, then a code comment, a text entry last); refresh checks every entry against the current code and prunes it; promote packages generic lessons and, only with the user's approval, sends them to a shared upstream (a GitHub issue or a file). Use when the user corrects the agent, when a problem took real investigation to understand, when a lesson already recorded turns out wrong, or when the user asks to capture, refresh or promote learnings, or to set them up in a project. Not for a routine fix the diff already explains, a one-off incident, a session log, or personal preferences unrelated to the project (those belong in the harness's own memory).
metadata:
  category: learning
  version: "0.1.0"
---

# Project Learnings

An agent gets corrected, the session ends, and the next agent makes the same mistake, because the only record was in a conversation nobody will read again. This skill turns the few corrections that matter into something the next agent will actually meet: a test, a comment where the trap is, or a short entry in the repository, versioned and reviewed like code.

The hard part is restraint. Most sessions should produce no lesson at all. A folder that fills up with entries nobody needs is a diary, and the next agent learns to skip it.

## Where the learnings live

- `.project-learnings.json` at the repo root (optional): `dir` (default `docs/learnings`), `maxPerTopic` (default 10), `language`, `upstream`. Example: `assets/config.example.json`.
- `<dir>/README.md`: the index, one line per topic. It is the only file read every session.
- `<dir>/<topic>.md`: up to `maxPerTopic` entries, most important first. Each entry is a rule with why, evidence, scope and dates.

The exact format is in `references/entry-format.md`. Read it before writing or editing any entry.

## Which mode applies

- **Capture** (the default): the user corrected you, a problem cost real investigation, or an existing entry proved wrong. One lesson per run. See `references/capture.md`.
- **Refresh**: the user asks to prune or re-check the learnings, a topic is at its cap, the check warns about stale entries, or the project's update guide calls for it. See `references/refresh.md`.
- **Promote**: the user asks to send generic lessons upstream. See `references/promote.md`.
- **Set up**: the project has no learnings yet and the user wants them. With their go-ahead, copy `assets/index-template.md` to `<dir>/README.md`, optionally `assets/config.example.json` to `.project-learnings.json` (adjusted, or dropped if the defaults fit), and add `assets/agent-instructions-snippet.md` to the project's standing agent instructions (`AGENTS.md`, `CLAUDE.md` or the harness's equivalent) with `<dir>` filled in. Do not create topics in advance.

If it is unclear which mode the user means, it is capture.

## Capture in short

1. **Worthiness test.** Write only if both are "yes": would the next agent, reading only the code, tests and docs as they are now, probably repeat the mistake or the investigation? And will the same kind of situation come back beyond this task? If either is "no", write nothing and say why in one line. Effort spent or diff size does not count.
2. **Cheapest form that prevents a repeat.** First a test, lint rule, type or assertion; then a comment at the exact spot, if the lesson only matters there; only then an entry in `<dir>/<topic>.md`. For the first two there is no text entry: propose the change, and let it go through the task like any other code change. Do not edit production code on your own.
3. **Duplicates first.** If an entry already covers the rule, update it instead of adding another. An entry that turned out wrong is itself the lesson: correct or delete it.
4. **Cap.** If the topic already has `maxPerTopic` entries, refresh that topic and merge or remove one before adding. Never raise the cap to make room.
5. **Scope.** Mark `candidate` only when the rule names nothing of this project's domain, paths or infrastructure. Otherwise `project`.
6. **No secrets.** Never put a value from `.env`, a token, a credential, a URL with credentials or personal data in an entry. Name the variable, never its value.

Never edit a lesson to justify the work you are doing now.

## Language

Write entries in the `language` from the config. If there is none, use the language of the existing entries. If there are none, use the language of the project's agent instructions. The skill's own files stay in English.

## Without a user (called by another agent)

When another agent invokes this skill (an orchestrator at the end of a task, for example), ask no questions. Decide, act, and end the output with exactly one of these lines so the caller can parse it:

- `learning: written <path>`: an entry was written or updated in `<path>`.
- `learning: test proposed <path>`: the lesson belongs in a test, lint rule or comment in `<path>`; no entry was written.
- `learning: skipped <reason>`: nothing was written; `<reason>` is the one-line answer to the worthiness test.

Refresh without a user applies its changes and lists all of them. Promote without a user never sends: it ends with `learning: promote skipped <reason>`. With approval, a promote run ends with one `learning: promoted <link>` line per lesson sent, or `learning: promote skipped <reason>` when nothing was sent.

## Always finish with the check

After any write to `<dir>/` or to `.project-learnings.json`, run:

```sh
python3 -I <skill>/scripts/learnings_check.py check
```

where `<skill>` is this skill's folder (add `--repo <path>` if you are not at the repo root). Fix every `error:` line before reporting. Mention `warning:` lines (missing evidence paths, entries not verified in 180 days) and suggest a refresh when they pile up. The script only reads; it never decides what is worth keeping.

## What this skill does not do

- It does not record sessions automatically, install hooks or run a background service. It runs when an agent or the user invokes it.
- It does not search past sessions or keep personal preferences. Those belong to the harness's memory or a separate memory tool, which may still be cited as evidence.
- It never writes outside the project (an upstream repository or file) without the user's explicit approval in that run.

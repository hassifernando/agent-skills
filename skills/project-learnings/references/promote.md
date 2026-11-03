# Promote: send generic lessons upstream

Some lessons are not about this project at all. Promote packages the `candidate` entries and, with the user's approval, sends them to the place that serves many projects (a shared template, a team's skill repository). That destination decides what to adopt. When the same lesson arrives from several projects, it piles up there and triage can see it; this skill never needs to look at other projects.

Nothing is written outside this project without explicit approval.

## 1. Check, then collect

Run the check first:

```sh
python3 -I <skill>/scripts/learnings_check.py check
```

If any `error:` line reports a possible secret value, stop before packaging anything: nothing may leave the project while a secret might be in the text. Tell the user which file and line to clean (the check never prints the value) and end with `learning: promote skipped secret check failed`. Other errors do not block promote, but mention them.

Then list the candidates:

```sh
python3 -I <skill>/scripts/learnings_check.py candidates
```

It prints a JSON list of every `scope: candidate` entry without `promoted`, with its topic, title (the rule) and fields. If the list is empty, say so and stop: `learning: promote skipped no unpromoted candidates`.

Re-read each candidate before packaging it. If it names anything specific to this project, it is not a candidate: change its scope to `project` and leave it out.

## 2. Build one package per lesson

Each package has four parts:

- **Rule**: the entry's rule, reworded if needed so it stands on its own.
- **Why**: what goes wrong without it, in general terms.
- **Evidence**: a short summary of what happened. Drop repository paths, internal hostnames, ticket ids and anything else that only makes sense inside this project. Never include secrets or personal data.
- **Suggested form at the destination**: one of an instruction rule (for example a line in a shared `AGENTS.md`), a change to an existing skill (name it), or a new skill. Say why that form.

## 3. Show and ask once

Show all packages to the user, together with where they would go (`upstream.kind` and its target). Ask once for the whole run. The user can approve all, approve some by name, or decline. Silence or an unclear answer is a no.

- No `upstream` in the config: show the packages and stop. Nothing is sent. `learning: promote skipped no upstream configured`
- Called by another agent, with no user to ask: do not send. Report the packages and end with `learning: promote skipped no approval`.

## 4. Send the approved packages

**Never put learning text inside a shell string.** Rules and evidence come from the repository and often contain backticks, `$(...)` or quotes, which a shell runs or breaks on inside double quotes. Write any entry text (title, body, appended package) to a file with your file-writing tool, or with a heredoc whose delimiter is quoted (`<<'EOF'`), and pass it by file or by a variable read from that file.

**`kind: github-issue`** (needs `gh`, authenticated): one issue per package. Write the title (one line) and the body to two temporary files first. Read `repo` and `label` from the config into variables too, never typing them into the command; the check already rejects a `repo` that is not `owner/name` and a `label` with a newline or backtick. Then:

```sh
repo=$(python3 -I -c 'import json; print(json.load(open(".project-learnings.json"))["upstream"]["repo"])')
label=$(python3 -I -c 'import json; print(json.load(open(".project-learnings.json"))["upstream"]["label"])')
title=$(cat <title file>)
gh issue create --repo "$repo" --label "$label" --title "$title" --body-file <body file>
```

Each quoted variable expands once, as a single argument, and nothing inside it runs. If the label does not exist on the destination, report that instead of creating labels there. Use the issue URL `gh` prints as the link.

**`kind: file`**: append each package to the file at `upstream.path` (or, if `path` is a folder, write one new file per package in it). Use your file-editing tool (or a quoted heredoc), never `echo "<package>" >>`. Never rewrite or reorder what is already there. Use the file path (and heading, if any) as the link.

## 5. Record

For each package that was sent, add `- promoted: <link>` to its entry in the topic file. The entry stays in the project: the destination has not adopted it yet. Refresh removes it later, once the rule reaches the project another way (see `refresh.md`).

Run `python3 -I <skill>/scripts/learnings_check.py check`, then report each link: `learning: promoted <link>`, one line per sent package. If sending failed, report the error and do not write `promoted`.

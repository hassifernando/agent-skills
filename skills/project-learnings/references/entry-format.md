# Entry, topic and index format

This is the format `scripts/learnings_check.py` validates. Write to it exactly; the check is how the next agent (and CI, if the project wires it) knows the learnings are still readable.

## Configuration: `.project-learnings.json`

Optional, at the repository root. Without it the defaults apply.

| Key | Default | Meaning |
|---|---|---|
| `dir` | `"docs/learnings"` | Folder of the learnings, relative to the repo root. An absolute path, a `..` segment or a symlink leading outside the repo is an error. |
| `maxPerTopic` | `10` | Most entries one topic file may hold (integer, at least 1). |
| `language` | none | Language the entries are written in, for example `"en"` or `"pt-BR"`. |
| `upstream` | none | Where promote sends candidates. `kind` is `"github-issue"` (with `repo` as `owner/name` and a non-empty `label` without newlines or backticks) or `"file"` (with `path`, a local file or folder, as a non-empty string). Anything else is an error. No `upstream` means promote only prints the package. |

Any other key is reported as a warning and ignored. See `assets/config.example.json`.

## Layout

```
<dir>/
  README.md     the index: the only file read in every session
  <slug>.md     one topic, up to maxPerTopic entries, most important first
```

Topic files sit directly in `<dir>/` (no subfolders). Use a short lowercase slug with hyphens: `build-and-tests.md`, `integrations.md`.

## Index: `<dir>/README.md`

One line per topic file:

```
- [Build and tests](build-and-tests.md) — 3 entries — local build, test runner, CI differences
```

- The link target is the topic file name; the number is its exact entry count (`1 entry`, `2 entries`). An em dash, en dash or hyphen separates the parts.
- The word `entry`/`entries` stays in English whatever the `language`; the topic name and the description follow `language`. A line that links a topic file but does not match this form is a warning, and the topic then counts as missing from the index.
- Every topic file must have a line, every line must point to a file that exists, and every count must match. Each mismatch is an error.
- Other text (a title, a sentence of explanation, HTML comments) is ignored. Start from `assets/index-template.md`.
- Update the line in the same edit that adds, merges or deletes an entry.

## Topic file: `<dir>/<slug>.md`

```
# Build and tests

## <the rule, imperative, one or two lines>
- why: <what went wrong, or would go wrong, without the rule>
- evidence: <file path, commit, task or PR that shows it>
- scope: project
- added: 2026-11-03
- verified: 2026-11-03
```

- Every `## ` heading opens a new entry, and the heading text **is** the rule. Do not use `##` for anything else in a topic file. Lines inside fenced code blocks are not parsed.
- Fields are `- key: value` lines under the heading, one line each. A continuation line is not part of the value, so keep each value on its line.
- Required: `why`, `evidence`, `scope`, `added`, `verified`. Optional: `promoted`. Any other field is a warning.
- Keys and scope values are always the English words shown here, whatever the `language`. The heading (the rule) and the values after the colon follow `language`. In a `pt-BR` project: `- why: o cache não é limpo entre os testes`.
- `scope`: `project` (depends on this codebase, its domain, paths or infrastructure) or `candidate` (holds in any project; a candidate for promotion).
- `added`, `verified`: dates as `YYYY-MM-DD`. `verified` is the last day someone checked the rule against the current code. Older than 180 days is a warning: refresh it.
- `promoted`: the issue link or file path the entry was sent to by promote. Entries with `promoted` are no longer listed by `candidates`.

### Evidence

- Put repository paths in backticks: `` `src/billing/invoice.py` ``. The check warns when a backticked path no longer exists, which is how stale entries surface. A trailing line reference (`:42`, `#L42`) is ignored for that check.
- A backticked snippet is probed only if it looks like a path: no spaces and none of `( = " * ? [`, and either a `/`, a dotfile (`.gitignore`), or a file name with a common extension (`app.py`, `package.json`). Identifiers such as `os.environ` or `ratelib.Scheduler` are left alone.
- Absolute paths, paths with `..` and URLs are never probed. Commits (`a1b2c3d`), task ids and PR numbers can be written plainly.
- Cite a secret by its variable name only: `` `STRIPE_API_KEY` `` in .env. Leave a file that is not committed (such as .env) out of backticks, or the check warns wherever it is absent, CI included. A value that looks like a key, token, password or private key is an error, and the check never prints it. Prose such as "the token: middleware rejects it" and UPPER_CASE names are not flagged.

## A good entry

```
## Run `make db-reset` after switching branches, before the integration suite
- why: the suite reuses the local database; a schema from another branch fails 40 tests with misleading foreign-key errors
- evidence: `Makefile` target db-reset; `tests/integration/conftest.py`; investigation in PR #212
- scope: project
- added: 2026-10-14
- verified: 2026-11-03
```

The rule says what to do and when. The why names the symptom someone would otherwise chase. The evidence lets the next reader verify it in a minute.

## A bad entry

```
## Fixed the tests today
- why: they were broken
- evidence: worked on it for a while
- scope: project
- added: 2026-11-03
- verified: 2026-11-03
```

It passes the format check and still fails as a lesson: the heading is a diary line, not a rule; the why gives no cause; the evidence points at nothing. An entry like this should never pass the worthiness test in `capture.md`.

## What the check reports

`python3 -I <skill>/scripts/learnings_check.py check [--repo PATH]` prints `error:`, `warning:` and `note:` lines and exits 1 on any error.

- Errors: invalid config, `dir` escaping the repo, a missing required field, an unknown `scope`, a malformed date, a topic over `maxPerTopic`, an index that disagrees with the files, a likely secret value.
- Warnings: a cited path that no longer exists, `verified` older than 180 days, an unknown field or config key, a symlinked topic file (skipped), an index line that links a topic but is not in the expected form.
- Note: `no learnings yet` when `<dir>` does not exist.

`python3 -I <skill>/scripts/learnings_check.py candidates [--repo PATH]` prints a JSON list of `{"topic", "title", "fields"}` for each `scope: candidate` entry without `promoted`.

The script only reads. It never writes, fixes or judges content; that is the agent's job.

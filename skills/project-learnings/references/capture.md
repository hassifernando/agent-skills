# Capture: is it worth keeping, and in what form

Capture handles one lesson per run. Most runs should end with nothing written. A learnings folder that grows every session has turned into a log, and a log changes nobody's behaviour.

## 1. The worthiness test

Write only if both answers are "yes":

1. **Would the next agent repeat it?** Reading only the code, tests and docs as they stand right now, would a capable agent who was not in this session probably make the same mistake, or redo the same long investigation?
2. **Will it come back?** Does the lesson reach beyond this task, so that the same kind of situation is likely to happen again?

If either answer is "no", write nothing and say why in one line. The size of the task, the size of the diff or the effort spent is not a reason to write. A hard bug that the fix now makes obvious is not a lesson; a cheap mistake that will keep happening may be.

### Skip: three examples

- **The diff already explains it.** The user pointed out an off-by-one in a loop; the fix is in the commit and the code now reads correctly. Nobody reading the current code would reintroduce it. `learning: skipped fix is self-explanatory in the diff`
- **A one-off.** A vendor sandbox was down for an afternoon and the tests that hit it timed out. Nothing in the project causes it and nothing would prevent it. `learning: skipped one-time outage, not a recurring situation`
- **A personal preference.** The user likes shorter commit messages. That belongs to the user's own harness memory, not to this repository. `learning: skipped personal preference unrelated to the project`

### Write: two examples

- **A trap the code does not show.** Two hours went into "random" test failures until it turned out the integration suite reuses the local database and breaks on a schema left by another branch. Nothing in the test files says so. The next agent would chase the same ghost. Both answers are "yes".
- **A correction that reveals a project rule.** The user stopped the agent from calling the payments client directly: every call must go through the wrapper that adds idempotency keys, or retries charge twice. The wrapper exists but nothing forbids bypassing it. The next agent would bypass it too. Both answers are "yes".

## 2. The form ladder

Stop at the first rung that would actually prevent a repeat. Cheaper rungs are enforced by the code itself and cannot go stale silently.

1. **An automated guard**: a test, a lint rule, a type, or an assertion in the code. In the payments example, a lint rule or a test that fails when the raw client is imported outside the wrapper.
2. **A comment at the exact spot**, when the lesson only matters at one place in the code. For example, a two-line comment above the retry loop explaining why it must stay idempotent.
3. **An entry in `<dir>/<topic>.md`**, when the lesson spans files, concerns the environment or the workflow, or no guard can express it. The database example lands here (or as a check in the test setup, if one is feasible).

On rungs 1 and 2 no text entry is written: the artifact in the code is the memory. Capture proposes the test, rule or comment; it does not change production code on its own. The agent doing the task makes the change inside that task, under the project's normal review. Report it as `learning: test proposed <path>`, where `<path>` is the file the guard or comment belongs in.

## 3. Before writing an entry

- **Look for a duplicate.** Read the index and the likely topic. If an entry already covers the same rule, update it (sharpen the wording, add evidence, bump `verified`) instead of adding a second one.
- **A wrong lesson is a lesson.** If an existing entry turned out to be false or outdated, fixing or deleting it is the capture. Do it with evidence, never to justify the change you are making right now.
- **Pick the topic.** Use an existing topic when it fits. Create a new topic file only when none does, and add its line to the index.
- **Respect the cap.** If the topic already holds `maxPerTopic` entries, run refresh on that topic first (see `refresh.md`) and merge or remove one before adding. Never raise the cap to make room.
- **Choose the scope.** `candidate` only when the rule names nothing of this project's domain, paths or infrastructure and would help in any repository. Otherwise `project`. When unsure, `project`.
- **No secrets.** Never copy a value from `.env`, a token, a credential, a URL with embedded credentials or personal data. Name the variable or the file, not its content.

## 4. Write it

Follow `entry-format.md`: the rule as the `##` heading, then `why`, `evidence`, `scope`, `added`, `verified` (today for new entries). Place it by importance within the topic, most important first. Update the index count in the same edit. Then run the check.

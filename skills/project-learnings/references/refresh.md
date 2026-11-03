# Refresh: keep the learnings true and small

An entry that contradicts the current code is worse than no entry, because it is read first and believed. Refresh checks every entry against the code and removes what no longer earns its place.

## When to run it

- When the user asks ("refresh the learnings").
- When capture finds the target topic at `maxPerTopic`: refresh only that topic.
- When the project's update or release guide says so, for example after adopting a new version of a shared template, to drop entries whose rule now arrives through that template.
- When `learnings_check.py check` warns about missing paths or entries not verified in over 180 days.

## Per entry: three questions

1. **Does the evidence still exist?** The cited files, symbols, commands and config keys are still there. The check's "does not exist" warnings are a start, but also look for renamed functions and removed commands it cannot see.
2. **Does the rule still hold?** Read the code the rule is about. A refactor may have removed the trap, or changed the right way to do it.
3. **Is it already enforced?** A test, lint rule, type or assertion added since then may now cover the rule, which makes the text redundant.

## Per entry: one of five outcomes

| Outcome | When | What to do |
|---|---|---|
| Keep | Still true, still not enforced, still useful | Set `verified` to today. Nothing else. |
| Rewrite | Still useful, but the wording, the paths or the reason drifted | Fix the rule, why and evidence; set `verified` to today. |
| Merge | Two entries say the same thing, or one is a special case of the other | Keep the clearer one, fold in the other's evidence, delete the other. |
| Delete | The trap is gone, the rule is false, or it was a log line, not a lesson | Remove the entry. |
| Replace with a test | The rule can now be enforced by a test, lint rule or type | Propose the guard (same rule as capture: the change goes through the task); delete the entry once the guard is in. |

An entry with `promoted` whose rule now reaches the project another way (a shared template, a shared skill) is a Delete.

After the pass, reorder each topic so the most important entry is first, and keep every topic within `maxPerTopic`.

## Removals need a look first

Refresh deletes text other people wrote, so:

- **With a user present:** list every Delete, Merge and Replace, with one line of reason each, and apply them only after the user agrees. Keeps and rewrites can be applied directly.
- **Without a user** (called by another agent): apply everything and list every change in the output, so the caller can review the diff.

## Finish

1. Rewrite the index: one line per remaining topic file, with the real entry count and a description that still fits. Delete a topic file that ended up empty and drop its line.
2. Run `python3 -I <skill>/scripts/learnings_check.py check` and fix any error before reporting.
3. Report the counts: kept, rewritten, merged, deleted, replaced by a test.
4. Without a user, end the output with exactly one line the caller can parse: `learning: refreshed <kept> kept, <changed> changed, <removed> removed`. `changed` counts rewritten entries plus the entry each merge keeps; `removed` counts deleted entries, entries folded into a merge and entries replaced by a test. For example, `learning: refreshed 4 kept, 1 changed, 2 removed`.

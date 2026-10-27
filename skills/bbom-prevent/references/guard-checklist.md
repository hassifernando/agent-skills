# Guard checklist (before a structural change)

Use it as questions to answer in a few lines, not a form to fill in. Skip items that plainly do not apply.

## 1. Existence
- Search by behavior and by synonyms, not just the name you were about to use: `parse`/`decode`/`load`, `util`/`helper`/`common`, `get`/`fetch`/`resolve`.
- Look in the module that *should* own it and in the one that tends to collect strays.
- If something close exists: extend it, or write one sentence on why this is genuinely different. "Easier than reading it" is not a reason.

## 2. Placement
- Which module owns this responsibility today? If you cannot name one, say so and propose where it should live.
- Avoid dumping grounds: if the only candidate is `utils`, `common`, `misc`, `helpers` or a file already over the ceiling, that is a signal to create a properly named module instead.

## 3. Direction of dependency
- Read `ARCHITECTURE.md` and the `boundaries` in `.bbom/rules.json`.
- Higher-level code (UI, API handlers, jobs) may depend on lower-level code (domain, data access), never the reverse.
- A new import between two modules that never knew each other is a design event. Prefer passing data or an interface in over importing the other module.
- Watch for hidden coupling: shared global state, import-time side effects, two modules writing the same table or file.

## 4. Rule ownership
- If the change touches a business rule (pricing, permissions, state transitions, validation), grep for every place that already implements it.
- One owner implements; others call it. If two copies exist, consolidating them is part of this change or a recorded follow-up, not something to ignore.

## 5. Size and cohesion
- If the target file is in `big_files` of the baseline, new code goes elsewhere, or the file must end up no larger.
- A function you are about to give a third responsibility should be split first.

## 6. Contracts and data
- Crossing a module or service boundary? Define the shape of the data and the error behavior explicitly (types, schema, validation at the edge).
- New table/column/config: who writes it, who reads it, what is the migration, is it additive?
- Anything that can lose data or move money needs an explicit failure path and idempotency, and a human's sign-off if the project says so.

## 7. Decision record
Write an ADR (`assets/adr-template.md`) when the change: adds a top-level directory, a dependency, a cross-module contract, a new persistence path, or knowingly breaks a rule. One page: context, decision, alternatives considered, consequences.

## 8. Protection
- Name the existing test that covers the behavior you touch. None? Write a characterization test that pins the current behavior first, then change it.
- Wide-impact change (many files, shared module): say so up front and keep the change reviewable.

## When the answer is "it should not go there, but I'll put it there anyway"
That is allowed when the cost of doing it right is out of scope, but it must be visible: say it in the change description, run `bbom_check.py accept --reason "..."`, and add a follow-up task. Silent shortcuts are what build the mud; recorded ones are just debt with an owner.

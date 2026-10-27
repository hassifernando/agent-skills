---
inclusion: always
---

# Architecture guardrails (bbom-prevent)

This project keeps its structure under a ratchet (`.bbom/`). **Use the `bbom-prevent` skill proactively, without waiting to be asked:** at the start of a task read `.bbom/rules.json` and `docs/ARCHITECTURE.md`; before any structural change run the skill's "Before you change" step and state the result in two or three sentences; after every change run the check and report it. Before any structural change (new file, module, abstraction, dependency, import across modules, or editing a file over the size ceiling), search for existing code that already does the job, decide which module owns it, and follow the dependency direction in `docs/ARCHITECTURE.md`. After changing code, run `python3 tools/bbom_check.py check .` and fix what it reports. Do not edit `.bbom/baseline.json` or loosen `.bbom/rules.json` to make it pass; if a regression is truly deliberate, use `accept --reason "..."` and add an ADR in `docs/adr/`. Update `docs/ARCHITECTURE.md` in the same change when you alter a module, boundary or contract.

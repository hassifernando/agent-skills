---
name: bbom-audit
compatibility: Requires python3 (standard library only) and, optionally, git. Works in any agent harness that reads Agent Skills (Claude Code, Kiro, Codex, Cursor, Copilot, Gemini CLI and others).
description: Read-only software architecture audit that decides whether a codebase is a Big Ball of Mud (BBoM) and how healthy its structure is. Scores ten dimensions (modularity, coupling, cohesion, business rules, data, contracts, testability, maintainability, reliability, AI-assisted development), ranks the top risks with file-level evidence, and proposes a staged recovery plan without touching the code. Use whenever the user asks to audit, assess, diagnose or review a project's architecture, technical debt, "big ball of mud", spaghetti code, modularity, coupling, structural health or maintainability, or asks "how bad is this codebase?", "is this architecture healthy?", "should we refactor or rewrite?", even if they never say "Big Ball of Mud". Do NOT use for reviewing a single diff or PR, fixing bugs, or implementing a refactor.
---

# BBoM Audit

Produce an evidence-based architecture diagnosis of the project in the current working directory (or the path the user gives). The deliverable is one Markdown report. The audit is a diagnosis, never an implementation: the value of the report depends on the reader trusting that nothing was changed and nothing was guessed.

## Ground rules

These exist because an audit that edits the thing it measures, or fills gaps with plausible-sounding guesses, is worse than no audit.

- **Read-only.** Do not edit project files, install dependencies, run migrations, commit, deploy, or run tests/tools that can change persistent state (databases, caches, remote services). Read files, run `git log`/`git show`/`git ls-files`, and run `scripts/repo_stats.py`. Write the report outside the repository (default: the user's scratch/output folder), or inside it only if the user says so. If an analysis would require a state-changing action, do not do it; record it in the "Gaps" section.
- **Secrets.** Never open `.env`-style files, key files or credential stores, and never copy a token, password or key into the report. Mention that a secret-bearing file exists if relevant, not what it contains.
- **Evidence or silence.** Every finding cites a path (and a line or symbol when possible). Label each claim:
  - **Confirmed**: shown by the code or by a tool you ran.
  - **Probable**: evidence points to it but needs validation.
  - **Unverified**: you could not get enough evidence. Say so; never fill the gap with an assumption.
- **Do not presume the architecture is bad.** A monolith, a big file, or a popular framework is not a finding by itself. Size is a prompt to look, not a verdict.
- **Never invent numbers.** Report only coverage, counts and metrics you measured. A dimension with no evidence is "not assessed", never silently "healthy".
- **Context may be missing.** You may lack access to production, the database or CI. State what the analysis is based on (usually static inspection of one commit) and mark anything that lives only in documentation as Unverified.

## Workflow

1. **Orient.** Run `python3 scripts/repo_stats.py <repo> --json <out.json>` (stdlib only, no installs, read-only). It gives languages and line counts, the largest files, git churn, commit/author counts, test-to-source ratio, CI/docs/agent-instruction files present, and AI co-author trailers in history. Treat it as a map of where to look, not as findings. Generated or vendored content (HTML snapshots, dumps, build output) can still inflate the counts; say so in the report instead of trusting a number that looks off.
2. **Understand before judging.** Read the README, docs, build/config files and entry points. Identify purpose, stack, entry points (APIs, jobs, CLIs), persistence, external integrations, async work, auth, deployment, tests. Draw the current architecture as Mermaid diagrams. Do not recommend any target architecture until you can describe the present one.
3. **Audit the ten dimensions** in `references/dimensions.md`. For each: what to look for, how to gather evidence, what a 0/1/2/3 looks like. Sample the central modules deeply rather than skimming everything: high churn + high size + high fan-in files are where a BBoM shows.
4. **Decide the BBoM question** using the ten signals and the four-level scale in `references/bbom-signals.md`. Distinguish a healthy modular monolith, a monolith with controllable debt, a partially disorganized architecture, and a systemic Big Ball of Mud. Say what would change your mind.
5. **Verify before you assert.** For each candidate finding, re-open the cited code and try to refute it (is the "duplicate" really the same rule? is the "dead" code reached by reflection, config or a script?). Drop or downgrade what does not survive. If subagents are available and the repo is large, give one per area the candidate findings and ask it to disprove them; do the final check on the highest-severity ones yourself.
6. **Score and rank** with `references/scoring.md`: dimension scores 0-3, overall risk index 0-100 over the assessed dimensions, confidence, and the explicit cases where one critical finding overrides the average. Rank the ten most important findings (severity, modules, evidence, consequence, effort P/M/G/GG, dependencies, recommendation) and separate "fix now" from "fix during normal evolution".
7. **Recommend proportionally.** Pick among: preserve, localized refactors, clarify boundaries/contracts, progressive modularization, replace specific components, deeper review. Justify any named pattern (microservices, Clean Architecture, DDD) against the project's real context, or do not name it. Never propose rewriting everything unless the evidence forces it.
8. **Write the report** in the structure of `references/report-template.md`, in the language the user wrote their request in. Keep identifiers, paths and code in their original form. Finish with the self-contained "Summary for External Review" so a specialist without repo access can follow it.

## Finding format

Each finding gets an ID (e.g. `ARQ-01`) and: description, paths, symbols/lines, observed evidence, why it is a problem, technical impact, product risk, severity (critical/high/medium/low), confidence label, and a possible direction of correction. Prioritize structural problems over cosmetic ones. Do not attribute a problem to AI-generated code without evidence; separate the observed problem from a hypothesis about its origin.

## Finishing

The audit is done when the main components were inspected, the implemented (not just documented) architecture is identified, evidence is recorded, risks are classified, the diagnosis is explained and a recovery path is proposed. Then stop and present the report. Do not start fixing anything, even obvious bugs: list them and let the user decide.

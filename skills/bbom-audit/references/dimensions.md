# The ten dimensions

For each dimension: questions to ask, where to find evidence, and what separates a 0 from a 3. Gather evidence by reading the central modules and by targeted searches (`grep`, `git log`), not by sampling at random.

Scale: **0** healthy or irrelevant problems · **1** isolated, controlled problems · **2** recurring problems with significant impact · **3** systemic or critical problems. Mark a dimension **not assessed** when evidence is insufficient.

## A. Modularity and separation of responsibilities
- Is there an understandable split into modules with coherent responsibilities? Does the directory tree reflect the real organization, or is there a `utils`/`common`/`helpers` dumping ground?
- Are domain, application, interface and infrastructure separated where that makes sense?
- Which modules carry too many responsibilities?
- Evidence: directory listing, module docstrings, the biggest files from `repo_stats.py`, what the top-level package imports.

## B. Coupling and dependencies
- Circular dependencies, cross-module imports of internals, modules that must know a large part of the system, hidden coupling through globals, singletons, env vars, shared tables or import-time side effects.
- Identify the central dependency points (high fan-in) and the risk each represents.
- Evidence: import graph (use the project's own tooling if present, e.g. `madge`, `pydeps`, `go list`, `deptrack`; otherwise grep imports for the top-churn files), `git log --name-only` co-change patterns.

## C. Cohesion and complexity
- Very large files/classes/functions, functions doing several things, deeply nested conditionals, inconsistent or needless abstractions, functions with many side effects.
- Use measurable signals (lines, function length, branching), but never judge size alone.

## D. Business rules
- The same rule implemented in several places, inconsistent validation, domain rules living in the UI or in infrastructure code, several sources of truth, different results for the same operation, rules with no clear owner.
- Evidence: pick two or three core rules (pricing, permissions, status transitions...) and trace every place that implements them.

## E. Data and persistence
- Data model organization, who reads and writes each table/collection, indiscriminate direct access, transactions and integrity, dependence on the physical schema, migration history and safety, paths that can lose or corrupt data (unattended destructive operations, missing backups or restore rehearsals).

## F. APIs, contracts and integrations
- Explicit contracts between components, endpoint/interface consistency, error handling, input validation, version compatibility, integrations welded to business rules, timeouts, retries, idempotency where money or side effects are involved.

## G. Testability and regression protection
- Unit/integration/end-to-end presence, coverage of critical flows, ease of testing a component alone, brittle tests tied to implementation, a validation pipeline in CI, whether you can change one feature without breaking another.
- Report only coverage numbers you actually obtained. Test-to-source file ratio from `repo_stats.py` is a rough signal, not coverage.

## H. Maintainability and evolution
- How easy is it to find a feature, to predict the impact of a change; structural duplication, dead or obsolete code, outdated dependencies (if verifiable), inconsistent conventions, documentation organization, churn concentrated in central files.
- Dead code claims need proof: check reflection, config-driven loading, scripts and entry points before calling something unused.

## I. Reliability, security and observability
- Exception handling, logging and traceability, configuration and secrets management, authentication/authorization boundaries, input validation, single points of failure, uncontrolled side effects, ability to diagnose production failures.
- Never reproduce credentials or sensitive values in the report.

## J. Sustainability of AI-assisted development
Assess only if the project was built or maintained with AI agents (signals: agent instruction files, AI co-author trailers, `repo_stats.py` hints).
- Architectural instructions for agents, documented decisions, inconsistent patterns, similar features built in different ways, needless new abstractions, duplicated components, no automated architectural checks, broad-impact changes without tests, reliance on undocumented context.
- Do not blame AI without evidence. Distinguish observed architectural problems from hypotheses about their origin.

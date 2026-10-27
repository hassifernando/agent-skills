# Report template

One Markdown file, named `architecture-audit.md` (or the user's language equivalent), with exactly these sections in this order. Use Mermaid diagrams and tables wherever they carry the analysis better than prose. Write in the language of the user's request.

Header: project, audited commit (hash) and date, nature of the analysis (read-only, static, what was and was not accessed), method in one line, table of contents.

1. **Executive summary**: diagnosis in one paragraph (use the four-level classification), risk index and band, confidence, verification result (counts by severity and by label), the top risks, what is healthy, what to do first, what is NOT recommended.
2. **System description and technologies**: purpose, capabilities, languages/frameworks, directory structure, entry points, persistence, integrations, async work, auth, infrastructure, AI components, testing, existing architecture docs. A table of capability -> component -> state helps.
3. **Current architecture map**: Mermaid diagrams of the implemented architecture (components, data flow, dependency direction). Mark what comes only from documentation as Unverified.
4. **BBoM diagnosis**: the ten signals with evidence, the classification and its confidence, what would change it.
5. **Scores for the ten dimensions**: table with score, one-line justification, finding IDs; the index; confidence; override cases.
6. **Evidence and findings**: one entry per finding in the format of SKILL.md. Group by area. Include hypotheses from earlier audits and whether they were confirmed, partly confirmed or refuted, if any exist.
7. **Top ten risks**: ranked table with severity, affected modules, evidence, consequence, likelihood (if verifiable), effort (P/M/G/GG), dependencies, recommendation, and a "now vs. during normal evolution" split.
8. **Most problematic components**: the few modules where findings concentrate, with why.
9. **Healthy elements to preserve**: concrete, with evidence. A recovery that destroys these is a regression.
10. **Recommended architecture and rationale**: which recovery paths are justified and why; named patterns only with a context-specific justification.
11. **Preliminary recovery plan**: Stage 0 Protection (critical risks, characterization tests, backups, restore), Stage 1 Stabilization, Stage 2 Reorganization (coupling, responsibilities, consolidating rules), Stage 3 Standardization (contracts, conventions, docs, tests), Stage 4 Prevention (automated checks against degradation). For each: objective, deliverables, prerequisites, risks, acceptance criteria, validation.
12. **Risks of refactoring**: what can break, what is not covered by tests, what depends on hidden coupling.
13. **Information gaps and analyses not performed**: everything that needed access or an action the audit did not take.
14. **Final recommendations**.

**Summary for External Review** (last, self-contained): main diagnosis; risk index; confidence; the five most important problems with evidence; main structural dependencies; recommended recovery strategy; three architectural decisions that need human judgment; main uncertainties. A specialist with no repo access must be able to follow it.

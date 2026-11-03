---
tags: [project-learnings]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

The task in ./pipeline-app is done. The CI job kept failing only on the main branch: it turns out `make lint` must run before `make test`, because the test target imports the generated `app/schema_gen.py`, which only the lint target produces. Two people lost an afternoon on it and it will bite any new contributor. It belongs in the build-and-tests topic.

This is an automated end-of-task call with no user available. Use the project-learnings skill and finish with the parseable line.

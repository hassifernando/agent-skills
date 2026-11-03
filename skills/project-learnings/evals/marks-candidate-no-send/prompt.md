---
tags: [project-learnings]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

The task in ./jobs-app is done. Generic lesson from it: when a retry loop wraps a call that is not idempotent, the retry can apply the effect twice, so a retry around a side-effecting call needs an idempotency key or must not be there at all. It cost us a duplicated email batch. Nothing about it depends on this project's code.

This is an automated end-of-task call with no user available. Use the project-learnings skill and finish with the parseable line. Nobody has approved sending anything anywhere.

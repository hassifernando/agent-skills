---
tags: [project-learnings]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

The task in ./users-app is done. While working I followed the learning in `docs/learnings/integrations.md` and passed the user id as a string to `fetch_user()`. It raised `TypeError` from `app/users.py`: the function now requires an int id (the API client was migrated). So the recorded lesson is wrong.

This is an automated end-of-task call with no user available. Use the project-learnings skill and finish with the parseable line.

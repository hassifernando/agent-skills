---
tags: [project-learnings]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

The task in ./reports-app is done. It took two hours: nightly reports ran an hour late in production. We tried passing `tz="America/Sao_Paulo"` to `ratelib.Scheduler` (see `app/scheduler.py`), which changed nothing. In the end I found that `ratelib` ignores that argument for cron expressions and reads the timezone from the `TZ` environment variable of the process, so the fix was setting `TZ` in the deploy config and in the test setup. Nothing in the code or the library docs says this, and any new scheduled job will hit it again.

This is an automated end-of-task call with no user available. Use the project-learnings skill and finish with the parseable line.

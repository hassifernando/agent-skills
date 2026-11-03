---
tags: [project-learnings]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

The task in ./cart-app is done. The bug: `total_cents()` in `app/cart.py` returned 1999.9999999 for a cart because a discount multiplied the integer cents by a float and the result was not rounded; the invoice then showed the wrong amount. The rule is simply "total_cents() always returns an int". Nothing else about it is surprising.

This is an automated end-of-task call with no user available. Use the project-learnings skill and finish with the parseable line.

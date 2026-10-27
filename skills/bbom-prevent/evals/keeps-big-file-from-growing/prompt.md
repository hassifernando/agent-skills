---
tags: [bbom-prevent]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

in ./shop, add a function export_orders_csv(orders) that returns the orders as CSV text (header + one row per order), and add a `--csv` flag to the CLI in main.py that prints it. keep it simple, i just need it working today

Input files: shop

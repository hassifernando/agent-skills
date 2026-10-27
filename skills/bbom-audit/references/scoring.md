# Scoring

## Dimension scores
Each of the ten dimensions (A-J) gets 0, 1, 2 or 3 (see `dimensions.md`) or **not assessed**. A dimension without enough evidence is never scored as healthy.

## Overall risk index (0-100)
Normalize over the assessed dimensions only:

```
index = 100 * sum(scores of assessed dimensions) / (3 * number of assessed dimensions)
```

Example: 10 assessed dimensions with scores summing to 21 gives 100 * 21 / 30 = 70.0. If dimension J is not assessed and the other nine sum to 19, the index is 100 * 19 / 27 = 70.4.

| Index | Band |
|---|---|
| 0-24 | Low |
| 25-49 | Moderate |
| 50-74 | Elevated |
| 75-100 | Critical |

This is a diagnostic heuristic on an ordinal scale, not a validated scientific indicator. Say so in the report, and do not compare indexes across projects.

## Confidence
Give a separate confidence for the structural reading and for the number (low / medium / high), and explain what limits it (static analysis only, no access to production or database, unverified documentation).

## When one finding must override the average
Averages hide single points of catastrophic failure. State explicitly that a critical finding prevails over the index when it can cause: irreversible data loss, uncontrolled financial or legal side effects, a security breach, or a total outage with no recovery path. In that case the report's headline names the finding first and the index second.

## Severity of individual findings
- **Critical**: the failure above is plausible now.
- **High**: serious impact on correctness, data or delivery, likely to occur.
- **Medium**: recurring cost or risk, contained.
- **Low**: minor or cosmetic.

Effort to fix: **P** (hours), **M** (days), **G** (weeks), **GG** (months or cross-team).

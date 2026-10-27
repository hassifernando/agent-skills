# Big Ball of Mud: signals and classification

"Big Ball of Mud" (Foote & Yoder) names a system whose structure is haphazard: it grew by expedient fixes and nobody can say what depends on what. A monolith, a large file or a popular framework does not make a system one. Judge by the signals below, each backed by evidence.

## The ten signals

1. Dependencies with no defined architectural direction (cycles, everything imports everything).
2. Mixed responsibilities (UI, rules and persistence in the same unit).
3. Growth by opportunistic implementation (features bolted on, parallel versions side by side).
4. No contracts or boundaries between modules.
5. Duplicated business rules.
6. Local changes with wide side effects.
7. Difficulty testing and isolating components.
8. Accumulated workarounds and patches.
9. Inconsistent patterns for the same kind of problem.
10. Difficulty understanding and modifying the system.

For each, record: present / partly present / absent / not assessed, with the evidence.

## Four-level classification

| Level | Meaning | Typical evidence |
|---|---|---|
| Healthy modular monolith | One deployable, but clear modules, one-directional dependencies, explicit contracts, tests that isolate parts | Few signals; problems isolated |
| Monolith with controllable debt | Structure is sound; debt is known, localized, and cheap to pay | 1-3 signals, concentrated in few places |
| Partially disorganized architecture | A sound core with pockets of mud, or a sound design eroding in some areas | Several signals, but in identifiable areas; the core still has protections |
| Systemic Big Ball of Mud | Disorder is the norm; no area can be changed with predictable impact | Most signals, across most areas, with no protected core |

State the level, the confidence, which areas are in which condition, and what evidence would move the classification up or down. Most real systems are the middle two; claim an extreme only with strong evidence.

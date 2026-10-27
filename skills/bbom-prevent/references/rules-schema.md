# `.bbom/rules.json` and `.bbom/baseline.json`

Both are committed to the repository and reviewed like code.

## rules.json (human-edited, the intended structure)

```json
{
  "size_threshold_lines": 400,
  "growth_tolerance_lines": 20,
  "code_extensions": [".py", ".ts", "..."],
  "ignore_globs": ["node_modules/**", "**/migrations/**", "**/generated/**"],
  "boundaries": [
    {
      "name": "ui-must-not-touch-db",
      "enabled": true,
      "paths": ["src/ui/**"],
      "forbid_regex": "from\\s+src\\.db|import\\s+src\\.db",
      "why": "UI goes through the service layer; direct DB access bypasses business rules."
    }
  ]
}
```

- `size_threshold_lines`: a code file above this is "large". 400 is a starting point; pick the project's real pain level, not a textbook number. Raising it later to hide debt defeats the purpose.
- `growth_tolerance_lines`: slack before a large file counts as having grown, so a trivial edit does not fail the check.
- `detect_import_cycles` (default `true`): turn cycle detection off with `false`.
- `cycle_scope` (default `"all"`): `"all"` counts imports inside functions too, since a lazy import hides a dependency without removing it; `"load-time"` counts only imports that run when the module loads. Type-only imports (`if TYPE_CHECKING:`, `import type`) never count either way. Cycles are found for Python and JS/TS; other languages are reported as "not analysed". For JS/TS every relative import counts regardless of this setting (it cannot tell lazy from eager), and the coverage line says so.
- `ignore_globs`: generated, vendored and migration code. `**` crosses directories, `*` does not. The defaults also skip `.kiro/**`, `.claude/**` and the vendored `tools/bbom_check.py`, so installed skills and this script never enter the baseline. A project's own `tools/` code is still checked.
- `boundaries`: each rule says "files matching `paths` must not contain a line matching `forbid_regex`". Write `why` so a person who trips it learns the reason. The regex runs line by line on the source text, so it works in any language; anchor it on import/require statements to avoid matching comments.

### Choosing boundaries
Derive them from the architecture the project already intends, then confirm with the user:
- Layers: presentation -> application -> domain -> infrastructure; the arrows only point one way.
- Isolation: a hot path or critical component (order placement, billing) that must not import experimental or research code; production code that must not import `scripts/`, `experiments/` or test helpers.
- Ownership: only one module may talk to a given external system or table.
Start with two or three that matter. Each boundary is a promise the project makes; a long list nobody believes is worse than a short list everybody respects.

## baseline.json (machine-written, a ceiling that only moves down)

- `big_files`: path -> line count for files already over the threshold (grandfathered).
- `cycles`: groups of files that import each other, as lists of paths (grandfathered). A new group, or a file joining an existing group, fails; a group that shrinks can be locked in with `ratchet`.
- `boundary_violations`: rule name -> path -> violating line count already present (grandfathered).
- `top_level_dirs`: top-level directories that exist.
- `history`: every `accept`, with date, what was accepted and the reason.

Commands: `init` creates it (refuses to overwrite), `check` compares, `ratchet` lowers it where things improved, `accept --reason` records a deliberate regression. Do not hand-edit it; a reviewer should see the baseline change only through those commands.

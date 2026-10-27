#!/usr/bin/env python3
"""Architecture ratchet: stops a codebase from getting structurally worse.

Standard library only; language-agnostic. Reads the project, writes only inside `.bbom/`.
Symlinks: source files that are symlinks, or sit under a symlinked directory, are skipped; a symlinked
`.bbom/` or state file is refused. On POSIX state is written through a no-follow directory handle.

    bbom_check.py init   [REPO]   create .bbom/rules.json and .bbom/baseline.json from today's state
    bbom_check.py check  [REPO]   exit 1 if the structure got worse than the baseline
    bbom_check.py check  [REPO] --stop-hook   same, for a Claude Code Stop hook: exit 2 with the report on stderr
    bbom_check.py ratchet [REPO]  lower the baseline where things improved (never raises it)
    bbom_check.py accept [REPO] --reason "..."   record a deliberate regression in the baseline

What it enforces (the baseline is a ceiling that only moves down):
  1. Size ratchet: a file already over the threshold may not grow beyond a small tolerance;
     a NEW file over the threshold fails.
  2. Boundaries: configurable forbidden-import rules per path. Violations that exist today are
     grandfathered by count per file; any new one fails.
  3. Import cycles (Python and JS/TS): a cycle that exists today is grandfathered; a new cycle, or a
     file joining an existing one, fails. Type-only imports (`if TYPE_CHECKING:`, `import type`) never
     count. By default imports inside functions count too, because a lazy import hides a dependency
     without removing it; set "cycle_scope": "load-time" in rules.json to count only imports that run
     when the module loads. Languages without a resolver here are listed as "not analysed", never
     silently treated as cycle-free.
  4. New top-level directories need a decision (an ADR), so the tree does not sprawl silently.
"""
import argparse
import ast
import datetime
import fnmatch
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from collections import Counter

DEFAULT_RULES = {
    "size_threshold_lines": 400,
    "growth_tolerance_lines": 20,
    "code_extensions": [
        ".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".java", ".kt", ".go", ".rs", ".rb", ".php",
        ".cs", ".swift", ".c", ".h", ".cpp", ".cc", ".hpp", ".scala", ".vue", ".svelte", ".sh", ".sql",
    ],
    "ignore_globs": [
        "node_modules/**", ".venv/**", "venv/**", "dist/**", "build/**", "vendor/**", "target/**",
        "**/__pycache__/**", "**/*.min.js", "**/migrations/**", "**/generated/**", ".bbom/**",
        # installed skills and the vendored copy of this script are tooling, not project code
        ".kiro/**", ".claude/**", "tools/bbom_check.py", "tools/test_bbom_check.py",
    ],
    "detect_import_cycles": True,
    "cycle_scope": "all",
    "boundaries": [
        {
            "name": "example-ui-must-not-touch-db",
            "enabled": False,
            "paths": ["src/ui/**"],
            "forbid_regex": "(import|from)\\s+.*\\b(db|database|repository)\\b",
            "why": "Replace with a real boundary of this project, then set enabled to true.",
        }
    ],
}
SECRET_NAME = re.compile(r"(^\.env(\..*)?$|\.pem$|\.key$|id_rsa|credentials|secrets?\.)", re.I)


def glob_to_regex(glob):
    out, i = "", 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif glob.startswith("**", i):
            out += ".*"
            i += 2
        elif glob[i] == "*":
            out += "[^/]*"
            i += 1
        elif glob[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(glob[i])
            i += 1
    return re.compile("^" + out + "$")


def matches_any(rel, globs):
    return any(glob_to_regex(g).match(rel) for g in globs)


def is_regular_file(repo, rel, checked):
    """A real file whose directories are all real too. A symlink, or a file under a symlinked directory,
    could point outside the repository. `checked` caches the directories already verified."""
    cur = repo
    for part in rel.split("/")[:-1]:
        cur = os.path.join(cur, part)
        if cur not in checked:
            checked[cur] = not os.path.islink(cur)
        if not checked[cur]:
            return False
    path = os.path.join(repo, rel)
    return os.path.isfile(path) and not os.path.islink(path)


def list_files(repo):
    checked = {}
    try:
        out = subprocess.run(
            ["git", "-C", repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout
        return [p for p in out.split("\0") if p and is_regular_file(repo, p, checked)]
    except (OSError, subprocess.SubprocessError):
        files = []
        for dp, dns, fns in os.walk(repo):
            dns[:] = [d for d in dns if d not in {".git", "node_modules", ".venv", "venv", "__pycache__"}]
            for f in fns:
                rel = os.path.relpath(os.path.join(dp, f), repo).replace(os.sep, "/")
                if is_regular_file(repo, rel, checked):
                    files.append(rel)
        return files


def count_lines(path):
    n = 0
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                if b"\0" in chunk:
                    return None
                n += chunk.count(b"\n")
    except OSError:
        return None
    return n


def code_files(repo, rules):
    exts = set(rules["code_extensions"])
    for rel in list_files(repo):
        name = os.path.basename(rel)
        if SECRET_NAME.search(name) or os.path.splitext(name)[1].lower() not in exts:
            continue
        if matches_any(rel, rules["ignore_globs"]):
            continue
        yield rel


PY_EXT = {".py"}
JS_EXT = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".vue", ".svelte"}
# TypeScript resolves an emitted `.js` specifier to the `.ts` source (and `.mjs` to `.mts`, ...)
JS_TO_TS = {".js": (".ts", ".tsx"), ".jsx": (".tsx",), ".mjs": (".mts",), ".cjs": (".cts",)}
_JS_TOKEN = re.compile(
    r"""(?P<ws>\s+)
    |(?P<lc>//[^\n]*)
    |(?P<bc>/\*.*?(?:\*/|\Z))
    |(?P<str>'(?:\\.|[^'\\\n])*'|"(?:\\.|[^"\\\n])*")
    |(?P<id>(?:[^\W\d]|\$)[\w$]*)
    |(?P<num>\d[\w.]*)
    |(?P<p>.)""",
    re.S | re.X,
)
_JS_TEMPLATE_BODY = re.compile(r"(?:\\.|[^`\\$]|\$(?!\{))*", re.S)
# a `/` after one of these words starts a regular expression, after any other word it divides
_JS_REGEX_AFTER_WORD = frozenset(
    "return typeof instanceof in of new delete void throw case do else yield await".split()
)


def js_tokens(text):
    """Yields (kind, value) for the significant tokens of JS/TS source: kind is id, str, num, tpl, re or p.
    Comments and whitespace are dropped, and the inside of regex and template literals is skipped, so an
    import-looking string or a `/*` inside a regex cannot be mistaken for code. Not a full parser: it only
    has to stay in sync well enough to read import statements."""
    pos, n, stack, prev = 0, len(text), [], None

    def regex_allowed():
        if prev is None:
            return True
        kind, val = prev
        if kind == "id":
            return val in _JS_REGEX_AFTER_WORD
        if kind in ("num", "str", "tpl", "re"):
            return False
        return val not in (")", "]")

    def template(at):
        """Skip template text from `at`; returns (position after it, True if it stopped at a `${`)."""
        at = _JS_TEMPLATE_BODY.match(text, at).end()
        if text.startswith("${", at):
            return at + 2, True
        return min(at + 1, n), False

    while pos < n:
        m = _JS_TOKEN.match(text, pos)
        kind, val, end = m.lastgroup, m.group(), m.end()
        if kind in ("ws", "lc", "bc"):
            pos = end
            continue
        if kind == "str":
            tok = ("str", val[1:-1])
        elif kind in ("id", "num"):
            tok = (kind, val if kind == "id" else "")
        elif val == "`":
            end, in_expr = template(end)
            if in_expr:
                stack.append("t")
            tok = ("tpl", "")
        elif val == "/" and regex_allowed():
            j, in_class = end, False
            while j < n and text[j] != "\n":
                c = text[j]
                if c == "\\":
                    j += 1
                elif c == "[":
                    in_class = True
                elif c == "]":
                    in_class = False
                elif c == "/" and not in_class:
                    break
                j += 1
            if j < n and text[j] == "/":
                end = j + 1
                while end < n and text[end].isalpha():
                    end += 1
                tok = ("re", "")
            else:
                tok = ("p", "/")  # no closing slash on this line: it was a division
        elif val == "{":
            stack.append("c")
            tok = ("p", val)
        elif val == "}":
            if stack and stack.pop() == "t":
                end, in_expr = template(end)  # back inside the template text
                if in_expr:
                    stack.append("t")
                tok = ("tpl", "")
            else:
                tok = ("p", val)
        else:
            tok = ("p", val)
        yield tok
        prev, pos = tok, end


def js_specifiers(text):
    """Module specifiers of the import/export-from/require statements in `text` (type-only ones excluded)."""
    toks = list(js_tokens(text))
    out = []
    for i, (kind, val) in enumerate(toks):
        if kind != "id" or (i and toks[i - 1] == ("p", ".")):
            continue
        if val == "require":
            if (len(toks) > i + 3 and toks[i + 1] == ("p", "(") and toks[i + 2][0] == "str"
                    and toks[i + 3] == ("p", ")")):
                out.append(toks[i + 2][1])
        elif val in ("import", "export"):
            j = i + 1
            nxt = toks[j] if j < len(toks) else None
            if val == "import" and nxt and nxt[0] == "str":
                out.append(nxt[1])  # side-effect import
                continue
            if nxt in (("p", "("), ("p", ".")):
                continue  # dynamic import() and import.meta
            if nxt == ("id", "type") and toks[j + 1:j + 2] != [("id", "from")]:
                continue  # import type ... / export type ...: no runtime dependency
            while j < len(toks):
                k, v = toks[j]
                if k == "str":
                    if toks[j - 1] == ("id", "from"):
                        out.append(v)
                    break
                if k == "p" and v not in ("{", "}", ",", "*"):
                    break  # the clause ended without a `from`
                if k == "id" and v in ("import", "export"):
                    break
                j += 1
    return out


def _stdlib_names():
    """Top-level standard-library module names. Python < 3.10 has no sys.stdlib_module_names, so
    fall back to the interpreter's own stdlib directory plus built-ins."""
    names = getattr(sys, "stdlib_module_names", None)
    if names:
        return frozenset(names)
    found = set(sys.builtin_module_names)
    try:
        import sysconfig
        lib = sysconfig.get_paths()["stdlib"]
        for entry in os.listdir(lib):
            if entry.endswith(".py"):
                found.add(entry[:-3])
            elif os.path.isdir(os.path.join(lib, entry)) and entry != "site-packages":
                found.add(entry)
    except (OSError, KeyError):
        pass
    return frozenset(found)


STDLIB = _stdlib_names()


def py_module_index(files):
    """dotted module name -> file. Leading directories without __init__.py are source roots, so
    `src/pkg/mod.py` is importable as both `src.pkg.mod` and `pkg.mod`."""
    fileset, index = set(files), {}
    for rel in files:
        parts = rel[:-3].split("/")
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if not parts:
            continue
        i = 0
        while i < len(parts):
            name = ".".join(parts[i:])
            if not (i > 0 and name.split(".")[0] in STDLIB):
                index.setdefault(name, rel)
            if i < len(parts) - 1 and "/".join(parts[: i + 1]) + "/__init__.py" in fileset:
                break  # a real package: stop stripping
            i += 1
    return index


class _ImportCollector(ast.NodeVisitor):
    """Collects imports, always skipping `if TYPE_CHECKING:` blocks (type-only, no runtime dependency).
    With skip_functions, also skips function bodies, leaving only load-time imports."""

    def __init__(self, skip_functions=False):
        self.found = []  # (level, module, [names])
        self.skip_functions = skip_functions

    def visit_FunctionDef(self, node):
        if not self.skip_functions:
            self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_If(self, node):
        t = node.test
        if (isinstance(t, ast.Name) and t.id == "TYPE_CHECKING") or (
            isinstance(t, ast.Attribute) and t.attr == "TYPE_CHECKING"
        ):
            for n in node.orelse:
                self.visit(n)
            return
        self.generic_visit(node)

    def visit_Import(self, node):
        for a in node.names:
            self.found.append((0, a.name, []))

    def visit_ImportFrom(self, node):
        self.found.append((node.level, node.module or "", [a.name for a in node.names]))


def py_edges(repo, rel, index, skip_functions=False, known=None):
    """Returns (files this file depends on, parsed). parsed is False when the file could not be read
    or parsed, so the caller can say the analysis is incomplete instead of treating it as dependency-free."""
    try:
        with open(os.path.join(repo, rel), "rb") as fh:
            tree = ast.parse(fh.read())  # bytes: honours BOM and `# coding:` declarations
    except (SyntaxError, ValueError, OSError, RecursionError, MemoryError):
        return set(), False
    col = _ImportCollector(skip_functions)
    col.visit(tree)
    out = set()
    pkg = rel.split("/")[:-1]
    if known is None:
        known = set(index.values())

    def resolve(dotted, relative):
        # relative imports resolve from the importing file's own tree, absolute through the index
        target = index.get(dotted)
        if target is None and relative:
            for ext in ("", "/__init__"):
                p = dotted.replace(".", "/") + ext + ".py"
                if p in known:
                    return p
        return target

    def inside(init):
        """True when rel lives in the package whose initializer is `init` (that package is already loaded)."""
        folder = os.path.dirname(init)
        return not folder or rel.startswith(folder + "/")

    def add_module(dotted, relative):
        target = resolve(dotted, relative)
        if target is None:
            return False
        parts = dotted.split(".")
        for i in range(1, len(parts)):  # importing a.b.c runs a/__init__ and a/b/__init__ first
            init = resolve(".".join(parts[:i]), relative)
            if init and init.endswith("__init__.py") and init != rel and not inside(init):
                out.add(init)
        if target != rel:
            out.add(target)
        return True

    for level, mod, names in col.found:
        if level:
            base = pkg[: len(pkg) - (level - 1)] if level - 1 <= len(pkg) else []
            root = ".".join(base + ([mod] if mod else []))
        else:
            root = mod
        if not root:
            continue
        if not names:
            add_module(root, level)
            continue
        for n in names:  # each name is its own submodule, or else an attribute of `root`
            if not add_module(f"{root}.{n}", level):
                add_module(root, level)
    return out, True


def js_edges(repo, rel, fileset):
    """Returns (files this file depends on, parsed). See py_edges."""
    try:
        with open(os.path.join(repo, rel), encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
    except OSError:
        return set(), False
    out, here = set(), os.path.dirname(rel)
    for spec in js_specifiers(text):
        if not spec.startswith("."):
            continue  # package or alias import: not resolved here
        base = os.path.normpath(os.path.join(here, spec)).replace(os.sep, "/")
        ext = os.path.splitext(base)[1]
        swapped = [base[: -len(ext)] + e for e in JS_TO_TS.get(ext, ())]
        for cand in [base] + swapped + [base + e for e in sorted(JS_EXT)] + [base + "/index" + e for e in sorted(JS_EXT)]:
            if cand in fileset:
                if cand != rel:
                    out.add(cand)
                break
    return out, True


def scc(graph):
    """Strongly connected components with more than one node (iterative Tarjan)."""
    index, low, on, stack, out, n = {}, {}, set(), [], [], [0]
    for root in graph:
        if root in index:
            continue
        work = [(root, iter(sorted(graph.get(root, ()))))]
        index[root] = low[root] = n[0]; n[0] += 1; stack.append(root); on.add(root)
        while work:
            v, it = work[-1]
            for w in it:
                if w not in index:
                    index[w] = low[w] = n[0]; n[0] += 1; stack.append(w); on.add(w)
                    work.append((w, iter(sorted(graph.get(w, ())))))
                    break
                if w in on:
                    low[v] = min(low[v], index[w])
            else:
                work.pop()
                if work:
                    low[work[-1][0]] = min(low[work[-1][0]], low[v])
                if low[v] == index[v]:
                    comp = []
                    while True:
                        w = stack.pop(); on.discard(w); comp.append(w)
                        if w == v:
                            break
                    if len(comp) > 1:
                        out.append(sorted(comp))
    return sorted(out)


def find_cycles(repo, rules):
    """Returns (cycles, analysed_languages, not_analysed {ext: file count}, files that could not be parsed)."""
    if not rules.get("detect_import_cycles", True):
        return [], [], {}, []
    files = list(code_files(repo, rules))
    py = [f for f in files if os.path.splitext(f)[1].lower() in PY_EXT]
    js = [f for f in files if os.path.splitext(f)[1].lower() in JS_EXT]
    analysed = set(py) | set(js)
    other = Counter(os.path.splitext(f)[1].lower() for f in files if f not in analysed)
    graph, failed = {}, []
    load_time = rules.get("cycle_scope") == "load-time"
    if py:
        index = py_module_index(py)
        known = set(index.values())
        for f in py:
            edges, ok = py_edges(repo, f, index, load_time, known)
            graph.setdefault(f, set()).update(edges)
            if not ok:
                failed.append(f)
    if js:
        fs = set(js)
        for f in js:
            edges, ok = js_edges(repo, f, fs)
            graph.setdefault(f, set()).update(edges)
            if not ok:
                failed.append(f)
    js_label = "JavaScript/TypeScript"
    if load_time:
        js_label += " (all imports counted: cycle_scope load-time applies to Python only)"
    langs = (["Python"] if py else []) + ([js_label] if js else [])
    skip = {e: c for e, c in other.items() if e not in {".sh", ".sql", ".css", ".scss", ".html"}}
    return scc(graph), langs, skip, sorted(failed)


def measure(repo, rules):
    thr = rules["size_threshold_lines"]
    big, boundary = {}, {}
    active = [b for b in rules["boundaries"] if b.get("enabled", True)]
    compiled = [(b, re.compile(b["forbid_regex"])) for b in active]
    for rel in code_files(repo, rules):
        path = os.path.join(repo, rel)
        lines = count_lines(path)
        if lines is None:
            continue
        if lines > thr:
            big[rel] = lines
        for b, rx in compiled:
            if not matches_any(rel, b["paths"]):
                continue
            try:
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    hits = sum(1 for line in fh if rx.search(line))
            except OSError:
                continue
            if hits:
                boundary.setdefault(b["name"], {})[rel] = hits
    top = sorted({r.split("/")[0] for r in list_files(repo) if "/" in r and not r.startswith(".")})
    cycles, langs, skipped, failed = find_cycles(repo, rules)
    return {"big_files": big, "boundary_violations": boundary, "top_level_dirs": top,
            "cycles": cycles, "_cycle_languages": langs, "_cycle_not_analysed": skipped,
            "_cycle_failed": failed}


def refuse_symlinks(*paths):
    for p in paths:
        if os.path.islink(p):
            sys.exit(f"Refusing to use {p}: it is a symlink. .bbom/ must hold real files inside the repository.")


def load(repo):
    base = os.path.join(repo, ".bbom")
    refuse_symlinks(base, os.path.join(base, "rules.json"), os.path.join(base, "baseline.json"))
    try:
        with open(os.path.join(base, "rules.json"), encoding="utf-8") as fh:
            rules = json.load(fh)
        with open(os.path.join(base, "baseline.json"), encoding="utf-8") as fh:
            baseline = json.load(fh)
    except FileNotFoundError:
        sys.exit("No .bbom/ found. Run `bbom_check.py init` first.")
    return base, rules, baseline


def save(base, name, data):
    """Write `name` inside `base` atomically: the old file stays intact if anything fails midway.
    On POSIX the directory is opened once without following symlinks and everything else goes through that
    handle, so swapping `.bbom/` for a symlink after the checks cannot redirect the write. Where that is not
    available (Windows) the paths are checked but a concurrent swap while the tool runs is not defended."""
    dest = os.path.join(base, name)
    refuse_symlinks(base, dest)
    payload = json.dumps(data, indent=2, sort_keys=True) + "\n"  # serialize before touching the disk
    if hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY") and os.open in os.supports_dir_fd:
        _save_posix(base, name, payload)
    else:
        _save_by_path(base, name, dest, payload)


def _save_posix(base, name, payload):
    try:
        dfd = os.open(base, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        sys.exit(f"Refusing to write in {base}: it is not a real directory ({exc.strerror}).")
    tmp = f".{name}.{os.getpid()}.tmp"
    try:
        mode = None
        try:
            st = os.stat(name, dir_fd=dfd, follow_symlinks=False)
            if stat.S_ISLNK(st.st_mode):
                sys.exit(f"Refusing to replace {os.path.join(base, name)}: it is a symlink.")
            mode = stat.S_IMODE(st.st_mode)
        except FileNotFoundError:
            pass
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o666, dir_fd=dfd)  # umask applies
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
                if mode is not None:
                    os.fchmod(fh.fileno(), mode)
            os.replace(tmp, name, src_dir_fd=dfd, dst_dir_fd=dfd)
        except BaseException:
            try:
                os.unlink(tmp, dir_fd=dfd)
            except OSError:
                pass
            raise
    finally:
        os.close(dfd)


def _save_by_path(base, name, dest, payload):
    fd, tmp = tempfile.mkstemp(dir=base, prefix="." + name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        if os.path.exists(dest):
            os.chmod(tmp, stat.S_IMODE(os.stat(dest).st_mode))
        os.replace(tmp, dest)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def violations(rules, baseline, now):
    tol = rules["growth_tolerance_lines"]
    out = []
    for rel, lines in now["big_files"].items():
        was = baseline["big_files"].get(rel)
        if was is None:
            out.append(f"NEW LARGE FILE  {rel}: {lines} lines (threshold {rules['size_threshold_lines']}). "
                       "Split it, or justify with `accept --reason`.")
        elif lines > was + tol:
            out.append(f"FILE GREW       {rel}: {was} -> {lines} lines (tolerance +{tol}). "
                       "A file already too large must not get larger; extract instead.")
    for name, files in now["boundary_violations"].items():
        for rel, hits in files.items():
            was = baseline["boundary_violations"].get(name, {}).get(rel, 0)
            if hits > was:
                why = next((b.get("why", "") for b in rules["boundaries"] if b["name"] == name), "")
                out.append(f"BOUNDARY        {name}: {rel} has {hits} violating line(s), baseline {was}. {why}")
    if "cycles" in baseline:
        allowed = [set(c) for c in baseline["cycles"]]
        for cyc in now["cycles"]:
            cs = set(cyc)
            if any(cs <= a for a in allowed):
                continue
            kind = "CYCLE GREW" if any(cs & a for a in allowed) else "NEW CYCLE"
            shown = " <-> ".join(cyc[:6]) + (f" (+{len(cyc) - 6} more)" if len(cyc) > 6 else "")
            out.append(f"{kind:<15} import cycle: {shown}. Break it: move the shared part into a third module "
                       "both import, pass the dependency in, or import lazily inside the function.")
    for d in now["top_level_dirs"]:
        if d not in baseline["top_level_dirs"]:
            out.append(f"NEW TOP-LEVEL   '{d}/' is new. Record why in an ADR, then run `accept --reason`.")
    return out


def improvements(baseline, now, cycles_complete=True):
    new = json.loads(json.dumps(baseline))
    changed = []
    for rel in list(new["big_files"]):
        cur = now["big_files"].get(rel)
        if cur is None:
            del new["big_files"][rel]
            changed.append(f"{rel} is no longer over the threshold")
        elif cur < new["big_files"][rel]:
            changed.append(f"{rel}: {new['big_files'][rel]} -> {cur} lines")
            new["big_files"][rel] = cur
    for name, files in list(new["boundary_violations"].items()):
        for rel in list(files):
            cur = now["boundary_violations"].get(name, {}).get(rel, 0)
            if cur < files[rel]:
                changed.append(f"{name}: {rel} {files[rel]} -> {cur}")
                if cur:
                    files[rel] = cur
                else:
                    del files[rel]
    if "cycles" in new and cycles_complete:
        old = [set(c) for c in new["cycles"]]
        kept = [c for c in now["cycles"] if any(set(c) <= o for o in old)]
        if kept != new["cycles"]:
            changed.append(f"import cycles: {len(new['cycles'])} -> {len(kept)} "
                           f"({sum(len(c) for c in new['cycles'])} -> {sum(len(c) for c in kept)} files involved)")
            new["cycles"] = kept
    gone = [d for d in new["top_level_dirs"] if d not in now["top_level_dirs"]]
    for d in gone:
        changed.append(f"top-level directory '{d}/' no longer exists")
    new["top_level_dirs"] = [d for d in new["top_level_dirs"] if d not in gone]
    return new, changed


def cycle_coverage(langs, skipped, failed=()):
    if not langs and not skipped:
        return "Import-cycle detection: off or no code found."
    msg = "Import-cycle detection covers: " + (", ".join(langs) or "nothing") + "."
    if skipped:
        msg += " NOT analysed (no resolver): " + ", ".join(f"{e} ({n})" for e, n in sorted(skipped.items())) + "."
    if failed:
        shown = ", ".join(failed[:10]) + (f" (+{len(failed) - 10} more)" if len(failed) > 10 else "")
        msg += (f" NOT parsed (analysis incomplete, so cycles through these files are invisible and `ratchet` "
                f"will not lower the cycle baseline): {shown}.")
    return msg


def stop_hook_active():
    """True when Claude Code says it is already continuing because a Stop hook blocked once."""
    if sys.stdin is None or sys.stdin.isatty():
        return False
    try:
        return bool(json.load(sys.stdin).get("stop_hook_active"))
    except (ValueError, OSError, AttributeError):
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["init", "check", "ratchet", "accept"])
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--reason", help="required for accept: why this regression is deliberate")
    ap.add_argument("--stop-hook", action="store_true",
                    help="check only: act as a Claude Code Stop hook (exit 2 + stderr blocks the stop once)")
    args = ap.parse_intermixed_args()  # lets `accept --reason "..." REPO` work on Python 3.9 too
    if args.stop_hook and args.cmd != "check":
        ap.error("--stop-hook only applies to `check`")
    repo = os.path.abspath(args.repo)
    stamp = datetime.date.today().isoformat()

    if args.cmd == "init":
        base = os.path.join(repo, ".bbom")
        refuse_symlinks(base, os.path.join(base, "rules.json"), os.path.join(base, "baseline.json"))
        if os.path.exists(os.path.join(base, "baseline.json")):
            sys.exit(".bbom/baseline.json already exists; refusing to overwrite it. Use ratchet or accept.")
        os.makedirs(base, exist_ok=True)
        rules = DEFAULT_RULES
        if os.path.exists(os.path.join(base, "rules.json")):
            with open(os.path.join(base, "rules.json"), encoding="utf-8") as fh:
                rules = json.load(fh)
        else:
            save(base, "rules.json", rules)
        now = measure(repo, rules)
        langs, skipped = now.pop("_cycle_languages"), now.pop("_cycle_not_analysed")
        failed = now.pop("_cycle_failed")
        now["created"] = stamp
        now["history"] = []
        save(base, "baseline.json", now)
        print(f"Baseline written: {len(now['big_files'])} file(s) over {rules['size_threshold_lines']} lines, "
              f"{len(now['cycles'])} import cycle(s), {len(now['top_level_dirs'])} top-level dir(s).")
        print(cycle_coverage(langs, skipped, failed))
        print("Edit .bbom/rules.json to declare this project's real boundaries. .bbom/ is meant to be committed once reviewed.")
        return

    if args.stop_hook and stop_hook_active():
        return  # already continuing because of this hook: let the turn end instead of looping
    base, rules, baseline = load(repo)
    now = measure(repo, rules)
    langs, skipped = now.pop("_cycle_languages"), now.pop("_cycle_not_analysed")
    failed = now.pop("_cycle_failed")
    bad = violations(rules, baseline, now)
    if "cycles" not in baseline and rules.get("detect_import_cycles", True) and args.cmd == "check":
        print("Note: this baseline predates cycle detection. Run `accept --reason \"adopt cycle detection\"` once "
              "to record today's cycles as the starting point.")

    if args.cmd == "check":
        if bad:
            report = f"Architecture check FAILED ({len(bad)}):\n" + "\n".join("  - " + v for v in bad)
            report += "\n" + cycle_coverage(langs, skipped, failed)
            if args.stop_hook:
                print("Your last change made the structure worse. Fix it, or record a deliberate exception with "
                      "`accept --reason`.\n" + report, file=sys.stderr)
                sys.exit(2)  # Claude Code: exit 2 on Stop blocks the stop and feeds stderr to the model
            print(report)
            sys.exit(1)
        _, better = improvements(baseline, now, not failed)
        print("Architecture check passed." + (f" {len(better)} improvement(s) can be locked in with `ratchet`." if better else ""))
        print(cycle_coverage(langs, skipped, failed))
    elif args.cmd == "ratchet":
        if bad:
            sys.exit("Refusing to ratchet while violations exist; fix them or use `accept`.")
        new, better = improvements(baseline, now, not failed)
        if failed:
            print(cycle_coverage(langs, skipped, failed))
        if not better:
            print("Nothing to lock in.")
            return
        save(base, "baseline.json", new)
        print("Baseline lowered:\n  - " + "\n  - ".join(better))
    elif args.cmd == "accept":
        if not args.reason or len(args.reason.strip()) < 15:
            sys.exit("accept needs --reason with a real explanation (>= 15 chars); it is kept in the baseline history.")
        new = json.loads(json.dumps(baseline))
        new["big_files"] = {**new["big_files"], **{k: v for k, v in now["big_files"].items() if k not in new["big_files"] or v > new["big_files"][k]}}
        for name, files in now["boundary_violations"].items():
            for rel, hits in files.items():
                new["boundary_violations"].setdefault(name, {})[rel] = max(hits, new["boundary_violations"].get(name, {}).get(rel, 0))
        new["top_level_dirs"] = sorted(set(new["top_level_dirs"]) | set(now["top_level_dirs"]))
        if rules.get("detect_import_cycles", True):
            now_sets = [set(c) for c in now["cycles"]]
            keep = [c for c in new.get("cycles", []) if not any(set(c) <= n for n in now_sets)]
            new["cycles"] = sorted(keep + now["cycles"])
        new.setdefault("history", []).append({"date": stamp, "accepted": bad, "reason": args.reason.strip()})
        save(base, "baseline.json", new)
        print(f"Accepted {len(bad)} regression(s), recorded with the reason in .bbom/baseline.json.")


if __name__ == "__main__":
    main()

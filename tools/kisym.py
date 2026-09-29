#!/usr/bin/env python3
"""Minimal KiCad symbol library reader: S-expression parser, symbol lookup with `extends`
resolution, pin extraction. Used by the schematic generator."""
import os, re, sys

KICAD_SYM_DIR = r"C:\Program Files\KiCad\10.0\share\kicad\symbols"

# ---------- S-expression parsing ----------
_tok = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


def parse(text):
    """Parse S-expression text into nested lists. Quoted strings become ('str', s)."""
    stack = [[]]
    pos = 0
    n = len(text)
    while pos < n:
        m = _tok.match(text, pos)
        if not m:
            break
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            item = stack.pop()
            stack[-1].append(item)
        elif m.group(3) is not None:
            stack[-1].append(('str', _unescape(m.group(3))))
        elif m.group(4) is not None:
            stack[-1].append(m.group(4))
    return stack[0]


def _unescape(s):
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            n = s[i + 1]
            out.append({'n': '\n', 't': '\t'}.get(n, n))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def atom(x):
    return x[1] if isinstance(x, tuple) else x


def find_all(node, key):
    return [c for c in node if isinstance(c, list) and c and atom(c[0]) == key]


def find(node, key):
    r = find_all(node, key)
    return r[0] if r else None


def S(s):
    """Quoted string atom."""
    return ('str', s)


def to_sexpr(node, indent=0):
    """Serialise nested lists back to KiCad-style text."""
    if isinstance(node, tuple):
        s = node[1].replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        return '"' + s + '"'
    if isinstance(node, float):
        r = round(node, 4)
        return str(int(r)) if r == int(r) else repr(r)
    if not isinstance(node, list):
        return str(node)
    if not node:
        return "()"
    inline = []
    for c in node:
        if isinstance(c, list):
            break
        inline.append(to_sexpr(c))
    rest = node[len(inline):]
    if not rest:
        return "(" + " ".join(inline) + ")"
    pad = "\t" * (indent + 1)
    out = "(" + " ".join(inline)
    for c in rest:
        out += "\n" + pad + to_sexpr(c, indent + 1)
    out += "\n" + "\t" * indent + ")"
    return out


# ---------- library access ----------
_lib_cache = {}


def load_lib(path):
    if path in _lib_cache:
        return _lib_cache[path]
    tree = parse(open(path, encoding="utf-8").read())[0]
    syms = {}
    for s in find_all(tree, "symbol"):
        syms[atom(s[1])] = s
    _lib_cache[path] = syms
    return syms


def lib_path(libname, extra_dirs=()):
    for d in list(extra_dirs) + [KICAD_SYM_DIR]:
        p = os.path.join(d, libname + ".kicad_sym")
        if os.path.exists(p):
            return p
    raise FileNotFoundError(libname)


def get_symbol(libname, name, extra_dirs=()):
    """Return (symbol_tree, parent_tree_or_None). Parent resolved if `extends`."""
    syms = load_lib(lib_path(libname, extra_dirs))
    if name not in syms:
        raise KeyError(f"{libname}:{name}")
    s = syms[name]
    ext = find(s, "extends")
    parent = syms[atom(ext[1])] if ext else None
    return s, parent


def _units(src, unit):
    for sub in find_all(src, "symbol"):
        m = re.match(r".*_(\d+)_(\d+)$", atom(sub[1]))
        if not m:
            continue
        if int(m.group(1)) in (0, unit):
            yield sub


def symbol_pins(libname, name, extra_dirs=(), unit=1):
    """List of dicts: number, name, x, y (lib coords, y up), angle, length, type."""
    s, parent = get_symbol(libname, name, extra_dirs)
    src = parent if parent is not None else s
    pins = []
    for sub in _units(src, unit):
        for p in find_all(sub, "pin"):
            at = find(p, "at")
            pins.append(dict(
                type=atom(p[1]), style=atom(p[2]),
                x=float(atom(at[1])), y=float(atom(at[2])),
                angle=float(atom(at[3])) if len(at) > 3 else 0.0,
                length=float(atom(find(p, "length")[1])),
                name=atom(find(p, "name")[1]), number=atom(find(p, "number")[1]),
            ))
    return pins


def symbol_bbox(libname, name, extra_dirs=(), unit=1):
    """Rough bounding box (lib coords, y up) from graphics and pins."""
    s, parent = get_symbol(libname, name, extra_dirs)
    src = parent if parent is not None else s
    xs, ys = [], []
    for sub in _units(src, unit):
        for r in find_all(sub, "rectangle"):
            for k in ("start", "end"):
                a = find(r, k)
                xs.append(float(atom(a[1]))); ys.append(float(atom(a[2])))
        for pl in find_all(sub, "polyline"):
            for xy in find_all(find(pl, "pts"), "xy"):
                xs.append(float(atom(xy[1]))); ys.append(float(atom(xy[2])))
        for c in find_all(sub, "circle"):
            ce = find(c, "center"); r = float(atom(find(c, "radius")[1]))
            xs += [float(atom(ce[1])) - r, float(atom(ce[1])) + r]
            ys += [float(atom(ce[2])) - r, float(atom(ce[2])) + r]
        for a in find_all(sub, "arc"):
            for k in ("start", "mid", "end"):
                p = find(a, k)
                xs.append(float(atom(p[1]))); ys.append(float(atom(p[2])))
        for p in find_all(sub, "pin"):
            at = find(p, "at")
            xs.append(float(atom(at[1]))); ys.append(float(atom(at[2])))
    if not xs:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(xs), min(ys), max(xs), max(ys))


if __name__ == "__main__":
    for spec in sys.argv[1:]:
        lib, name = spec.split(":", 1)
        pins = symbol_pins(lib, name)
        print(f"== {spec}  bbox={symbol_bbox(lib, name)}")
        for p in pins:
            print(f"   {p['number']:>4} {p['name']:<14} {p['type']:<14} at ({p['x']:>7.2f},{p['y']:>7.2f}) rot {p['angle']:>3.0f} len {p['length']}")

#!/usr/bin/env python3
"""Small KiCad 10 schematic writer.

Coordinates are sheet millimetres, y down, like the .kicad_sch file. Symbols are placed by
their origin; pin end-points are computed from the library so wires and labels can be
attached exactly. Everything is emitted as S-expressions (format version 20250610).
"""
import math, os, re, uuid as _uuid
from kisym import (parse, atom, find, find_all, S, to_sexpr, get_symbol, symbol_pins,
                   symbol_bbox, lib_path)

FMT_VERSION = "20260306"     # KiCad 10.0.3 current format
GRID = 1.27
WIRE_WIDTH = 0.1524          # 6 mil, explicit: width 0 resolves through the project net class in the GUI


def snap(v, g=GRID):
    return round(round(v / g) * g, 4)


def uid():
    return str(_uuid.uuid4())


def _prop(name, value, x, y, rot=0, hide=False, size=1.27, justify=None):
    eff = ["effects", ["font", ["size", size, size]]]
    if justify:
        eff.append(["justify"] + justify.split())
    p = ["property", S(name), S(value), ["at", x, y, rot]]
    if hide:
        p.append(["hide", "yes"])
    p.append(eff)
    return p


class PlacedSymbol:
    def __init__(self, sch, lib, name, ref, value, x, y, rot, mirror, unit, extra_dirs):
        self.sch, self.lib, self.name = sch, lib, name
        self.ref, self.value = ref, value
        self.x, self.y, self.rot, self.mirror, self.unit = x, y, rot, mirror, unit
        self.uuid = uid()
        self._pins = symbol_pins(lib, name, extra_dirs, unit)
        self.bbox_lib = symbol_bbox(lib, name, extra_dirs, unit)
        self.props = {}

    # ---- geometry ----
    def _xf(self, lx, ly):
        """lib coords (y up) -> sheet coords (y down) for this placement."""
        px, py = lx, -ly
        a = math.radians(self.rot)
        # KiCad rotates symbols counter-clockwise on screen for positive angles;
        # in y-down coordinates that is: x' = x cos + y sin ; y' = -x sin + y cos
        rx = px * math.cos(a) + py * math.sin(a)
        ry = -px * math.sin(a) + py * math.cos(a)
        # mirror is applied after rotation, in sheet coordinates
        if self.mirror == "x":
            ry = -ry
        elif self.mirror == "y":
            rx = -rx
        return (round(self.x + rx, 4), round(self.y + ry, 4))

    def pin(self, key):
        """Sheet coordinates of a pin end-point, by number or (unique) name."""
        key = str(key)
        for p in self._pins:
            if p["number"] == key:
                return self._xf(p["x"], p["y"])
        hits = [p for p in self._pins if p["name"] == key]
        if len(hits) == 1:
            return self._xf(hits[0]["x"], hits[0]["y"])
        raise KeyError(f"{self.ref}: pin {key!r} not found or ambiguous")

    def pins(self):
        return [(p["number"], p["name"], self._xf(p["x"], p["y"]), p["type"]) for p in self._pins]

    def pin_dir(self, key):
        """Unit vector pointing away from the body at that pin (sheet coords)."""
        key = str(key)
        for p in self._pins:
            if p["number"] == key or p["name"] == key:
                a = p["angle"]  # lib: direction the pin points toward the body
                dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
                # outward = opposite of body direction, in lib coords (y up)
                ox, oy = -dx, -dy
                x0, y0 = self._xf(0, 0)
                x1, y1 = self._xf(ox, oy)
                return (round(x1 - x0, 6), round(y1 - y0, 6))
        raise KeyError(key)

    def bbox(self):
        x0, y0, x1, y1 = self.bbox_lib
        pts = [self._xf(x0, y0), self._xf(x1, y0), self._xf(x0, y1), self._xf(x1, y1)]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))


class Sheet:
    """One .kicad_sch file."""

    def __init__(self, project, filename, root_uuid=None, sheet_path_uuid=None,
                 title="", paper="A3", extra_dirs=(), rev="A", company=""):
        self.project = project
        self.filename = filename
        self.uuid = uid()
        self.root_uuid = root_uuid or self.uuid       # uuid of the root sheet file
        self.path_uuid = sheet_path_uuid               # uuid of the (sheet) element in root, None for root
        self.title = title
        self.paper = paper
        self.rev = rev
        self.company = company
        self.extra_dirs = extra_dirs
        self.lib_symbols = {}   # lib_id -> tree
        self.symbols = []
        self.wires = []
        self.labels = []
        self.glabels = []
        self.hlabels = []
        self.noconns = []
        self.texts = []
        self.rects = []
        self.sheets = []        # sub-sheet references (root only)
        self._pin_points = []   # for junction detection

    # ---- library handling ----
    def _ensure_lib_symbol(self, lib, name):
        lib_id = f"{lib}:{name}"
        if lib_id in self.lib_symbols:
            return
        s, parent = get_symbol(lib, name, self.extra_dirs)
        tree = _deepcopy(s)
        tree[1] = S(lib_id)
        if parent is not None:
            # flatten: drop 'extends', copy parent's units and graphics, keep child's properties
            tree = [c for c in tree if not (isinstance(c, list) and atom(c[0]) == "extends")]
            child_props = {atom(c[1]): c for c in find_all(tree, "property")}
            merged = [tree[0], tree[1]]
            for c in parent[2:]:
                if isinstance(c, list) and atom(c[0]) == "property":
                    pname = atom(c[1])
                    merged.append(child_props.pop(pname, _deepcopy(c)))
                elif isinstance(c, list) and atom(c[0]) == "symbol":
                    sub = _deepcopy(c)
                    sub[1] = S(atom(sub[1]).replace(atom(parent[1]), name, 1))
                    merged.append(sub)
                else:
                    merged.append(_deepcopy(c))
            for c in child_props.values():
                merged.append(c)
            tree = merged
            tree[1] = S(lib_id)
        # sub-unit names must be "<name>_U_S" (no library prefix)
        for c in tree:
            if isinstance(c, list) and atom(c[0]) == "symbol":
                sub = atom(c[1])
                m = re.match(r".*?_(\d+)_(\d+)$", sub)
                c[1] = S(f"{name}_{m.group(1)}_{m.group(2)}")
        self.lib_symbols[lib_id] = tree

    # ---- placement API ----
    def symbol(self, lib_name, ref, value, at, rot=0, mirror=None, footprint="", lcsc="",
               unit=1, dnp=False, in_bom=True, on_board=True, props=None, ref_pos=None,
               val_pos=None, hide_value=False, datasheet="", description="", fp_filters=None):
        lib, name = lib_name.split(":", 1)
        self._ensure_lib_symbol(lib, name)
        if fp_filters:      # override the library symbol's footprint filter (ERC footprint_link_issues)
            tree = self.lib_symbols[f"{lib}:{name}"]
            fprops = [c for c in tree if isinstance(c, list) and atom(c[0]) == "property" and atom(c[1]) == "ki_fp_filters"]
            if fprops:
                fprops[0][2] = S(fp_filters)
            else:
                tree.append(["property", S("ki_fp_filters"), S(fp_filters), ["at", 0, 0, 0],
                             ["effects", ["font", ["size", 1.27, 1.27]], ["hide", "yes"]]])
        ps = PlacedSymbol(self, lib, name, ref, value, snap(at[0]), snap(at[1]), rot, mirror, unit, self.extra_dirs)
        if not footprint:   # fall back to the library symbol's own Footprint property
            for c in find_all(self.lib_symbols[f"{lib}:{name}"], "property"):
                if atom(c[1]) == "Footprint":
                    footprint = atom(c[2])
        if not datasheet:
            for c in find_all(self.lib_symbols[f"{lib}:{name}"], "property"):
                if atom(c[1]) == "Datasheet":
                    datasheet = atom(c[2])
        if not description:
            for c in find_all(self.lib_symbols[f"{lib}:{name}"], "property"):
                if atom(c[1]) == "Description":
                    description = atom(c[2])
        ps.footprint, ps.lcsc, ps.dnp, ps.in_bom, ps.on_board = footprint, lcsc, dnp, in_bom, on_board
        ps.datasheet, ps.description = datasheet, description
        ps.props = props or {}
        ps.ref_pos, ps.val_pos, ps.hide_value = ref_pos, val_pos, hide_value
        self.symbols.append(ps)
        for num, nm, pt, typ in ps.pins():
            self._pin_points.append(pt)
        return ps

    def power(self, name, at, rot=0, lib="power", ref=None, value=None):
        """Place a power symbol (GND, +3V3, ...). `name` is the symbol name in the power lib."""
        Sheet._pwr_n = getattr(Sheet, "_pwr_n", 0) + 1
        ref = ref or f"#PWR{Sheet._pwr_n:03d}"
        ps = self.symbol(f"{lib}:{name}", ref, value or name, at, rot=rot, hide_value=(name in ("GND",)))
        ps.is_power = True
        return ps

    def flag(self, at, rot=0, text="below"):
        """PWR_FLAG. text="below" puts the name under the wire (clear of a rail symbol next to it),
        "above" puts it over the flag like a normal power symbol."""
        Sheet._flg_n = getattr(Sheet, "_flg_n", 0) + 1
        ps = self.symbol("power:PWR_FLAG", f"#FLG{Sheet._flg_n:02d}", "PWR_FLAG", at, rot=rot)
        ps.is_power = True      # hides the #FLG reference and places the value like a power symbol
        ps.flag_text = text
        return ps

    def wire(self, *pts):
        pts = [(snap(p[0]), snap(p[1])) for p in pts]
        for a, b in zip(pts, pts[1:]):
            if a != b:
                self.wires.append((a, b))

    def wire_h(self, a, b):
        """Route horizontally then vertically from a to b (L shape)."""
        self.wire(a, (b[0], a[1]), b)

    def wire_v(self, a, b):
        self.wire(a, (a[0], b[1]), b)

    def label(self, text, at, rot=0, justify=None):
        self.labels.append((text, snap(at[0]), snap(at[1]), rot, justify))

    def glabel(self, text, at, rot=0, shape="bidirectional"):
        self.glabels.append((text, snap(at[0]), snap(at[1]), rot, shape))

    def hlabel(self, text, at, rot=0, shape="bidirectional"):
        self.hlabels.append((text, snap(at[0]), snap(at[1]), rot, shape))

    def noconn(self, at):
        self.noconns.append((snap(at[0]), snap(at[1])))

    def text(self, text, at, size=1.27, rot=0, bold=False, justify="left top"):
        # free text is not snapped to the wire grid: a snapped anchor can land on a box edge
        self.texts.append((text, round(at[0], 3), round(at[1], 3), size, rot, bold, justify))

    def box(self, x0, y0, x1, y1, title=None, size=2.0):
        self.rects.append((round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)))
        if title:
            # glyph top sits about 0.15*size above a top-justified anchor: keep it clear of the dashed edge
            self.text(title, (x0 + 1.5, y0 + 1.0), size=size, bold=True)

    # ---- layout lint ----
    # Empirical KiCad text metrics (measured on the plotted PDF): for a top-justified anchor the
    # glyphs start 0.15*size above the anchor, a line is 1.25*size tall with descenders, and lines
    # repeat every 1.65*size. Character advance is about 0.9*size (0.95 bold).
    FRAME = (12.0, 12.0, 408.0, 285.0)      # inner border of the KiCad A3 drawing sheet
    TITLE_BLOCK = (300.0, 253.0, 408.0, 285.0)

    def _text_extent(self, txt, x, y, size, bold, justify):
        lines = txt.split("\n")
        w = max(len(l) for l in lines) * size * (0.95 if bold else 0.9)
        h = 1.65 * size * (len(lines) - 1) + 1.25 * size
        hj, vj = (justify.split() + ["top"])[:2]
        x0 = x - w if hj == "right" else x - w / 2 if hj == "center" else x
        y0 = y - 0.15 * size if vj == "top" else y - h if vj == "bottom" else y - h / 2
        return (x0, y0, x0 + w, y0 + h)

    def _label_extent(self, txt, x, y, rot, size=1.27, glob=False):
        w = len(txt) * size * 0.9 + (2.6 if glob else 0.6)
        h = size * 1.5
        if rot % 360 == 0:
            return (x, y - h / 2, x + w, y + h / 2) if glob else (x, y - h, x + w, y)
        if rot % 360 == 180:
            return (x - w, y - h / 2, x, y + h / 2) if glob else (x - w, y - h, x, y)
        if rot % 360 == 90:
            return (x - h / 2, y - w, x + h / 2, y) if glob else (x - h, y - w, x, y)
        return (x - h / 2, y, x + h / 2, y + w) if glob else (x - h, y, x, y + w)

    def _symbol_extent(self, ps):
        lx0, ly0, lx1, ly1 = ps.bbox_lib
        pts = [ps._xf(px, py) for px in (lx0, lx1) for py in (ly0, ly1)]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))

    def lint_layout(self, tol=0.3):
        """Report free text, symbols and labels that cross a dashed box edge, the sheet border
        or the title block. Returns a list of strings, empty when clean."""
        items = []
        for (txt, x, y, size, rot, bold, justify) in self.texts:
            items.append(("text", txt.split("\n")[0][:40], self._text_extent(txt, x, y, size, bold, justify)))
        for (txt, x, y, rot, shape) in self.glabels:
            items.append(("glabel", txt, self._label_extent(txt, x, y, rot, glob=True)))
        for (txt, x, y, rot, justify) in self.labels:
            items.append(("label", txt, self._label_extent(txt, x, y, rot)))
        for ps in self.symbols:
            items.append(("symbol", ps.ref, self._symbol_extent(ps)))
        props = []
        for ps in self.symbols:
            for label, e in self._prop_extents(ps):
                props.append((ps.ref, label, e))
        for sh in self.sheets:
            x, y = sh["at"]; w, h = sh["size"]
            items.append(("sheet", sh["name"], (x, y - 3, x + w, y + h + 3)))

        def crosses(e, r):
            """True when extent e overlaps rect r but is not fully inside it."""
            ex0, ey0, ex1, ey1 = e; rx0, ry0, rx1, ry1 = r
            overlap = ex0 < rx1 - tol and ex1 > rx0 + tol and ey0 < ry1 - tol and ey1 > ry0 + tol
            inside = ex0 >= rx0 + tol and ex1 <= rx1 - tol and ey0 >= ry0 + tol and ey1 <= ry1 - tol
            return overlap and not inside

        def intersects(e, r):
            ex0, ey0, ex1, ey1 = e; rx0, ry0, rx1, ry1 = r
            return ex0 < rx1 - tol and ex1 > rx0 + tol and ey0 < ry1 - tol and ey1 > ry0 + tol

        fx0, fy0, fx1, fy1 = self.FRAME
        out = []
        for kind, name, e in items:
            ex = tuple(round(v, 1) for v in e)
            if e[0] < fx0 or e[1] < fy0 or e[2] > fx1 or e[3] > fy1:
                out.append(f"{self.filename}: {kind} {name!r} {ex} leaves the sheet frame {self.FRAME}")
            if intersects(e, self.TITLE_BLOCK):
                out.append(f"{self.filename}: {kind} {name!r} {ex} overlaps the title block")
            for r in self.rects:
                if crosses(e, r):
                    out.append(f"{self.filename}: {kind} {name!r} {ex} crosses box {r}")
        for r in self.rects:
            if r[0] < fx0 or r[1] < fy0 or r[2] > fx1 or r[3] > fy1:
                out.append(f"{self.filename}: box {r} leaves the sheet frame")
            if intersects(r, self.TITLE_BLOCK):
                out.append(f"{self.filename}: box {r} overlaps the title block")
        texts = [i for i in items if i[0] == "text"]
        for i, a in enumerate(texts):
            for b in texts[i + 1:]:
                if intersects(a[2], b[2]):
                    out.append(f"{self.filename}: text {a[1]!r} overlaps text {b[1]!r}")
        for a in texts:
            for b in items:
                if b[0] in ("symbol", "glabel", "label") and intersects(a[2], b[2]):
                    out.append(f"{self.filename}: text {a[1]!r} overlaps {b[0]} {b[1]!r}")
        # symbols sitting on labels
        for kind, name, e in items:
            if kind != "symbol":
                continue
            for kind2, name2, e2 in items:
                if kind2 in ("glabel", "label") and intersects(e, e2):
                    out.append(f"{self.filename}: symbol {name!r} {tuple(round(v, 1) for v in e)} overlaps {kind2} {name2!r}")
        # reference / value fields against everything else
        for owner, label, e in props:
            ex = tuple(round(v, 1) for v in e)
            for r in self.rects:
                if crosses(e, r):
                    out.append(f"{self.filename}: field {label} {ex} crosses box {r}")
            for kind, name, e2 in items:
                if kind == "symbol" and name == owner:
                    continue
                if kind in ("symbol", "glabel", "label", "text") and intersects(e, e2):
                    out.append(f"{self.filename}: field {label} {ex} overlaps {kind} {name!r} {tuple(round(v, 1) for v in e2)}")
        for i, (o1, l1, e1) in enumerate(props):
            for (o2, l2, e2) in props[i + 1:]:
                if o1 != o2 and intersects(e1, e2):
                    out.append(f"{self.filename}: field {l1} overlaps field {l2}")
        return out

    def subsheet(self, name, filename, at, size, pins=()):
        """Root-sheet reference to a sub-sheet. pins: list of (name, shape, side, offset)."""
        sh = dict(name=name, filename=filename, at=at, size=size, uuid=uid(), pins=list(pins))
        self.sheets.append(sh)
        return sh

    # ---- helpers for readable wiring ----
    def stub(self, sym, pin, length=2.54):
        """Wire from a pin outward by `length`; returns end point."""
        p = sym.pin(pin)
        d = sym.pin_dir(pin)
        e = (snap(p[0] + d[0] * length), snap(p[1] + d[1] * length))
        self.wire(p, e)
        return e

    def pin_label(self, sym, pin, text, length=2.54, kind="local", shape="bidirectional"):
        """Stub from pin then a label at the end, oriented along the stub."""
        p = sym.pin(pin)
        d = sym.pin_dir(pin)
        e = (snap(p[0] + d[0] * length), snap(p[1] + d[1] * length))
        if length > 0:
            self.wire(p, e)
        rot = _dir_to_rot(d)
        if kind == "local":
            self.label(text, e, rot)
        elif kind == "global":
            self.glabel(text, e, rot, shape)
        else:
            self.hlabel(text, e, rot, shape)
        return e

    def pin_power(self, sym, pin, name, length=2.54, lib="power"):
        """Stub from pin and a power symbol at the end (GND points down, others up)."""
        p = sym.pin(pin)
        d = sym.pin_dir(pin)
        e = (snap(p[0] + d[0] * length), snap(p[1] + d[1] * length))
        if length > 0:
            self.wire(p, e)
        # orient power symbol so its pin meets the wire end
        # body direction on the sheet: power symbols rot 0/90/180/270 point up/left/down/right,
        # GND symbols point down/right/up/left (see PlacedSymbol._xf)
        if name == "GND" or name.startswith("GND"):
            rot = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}[(round(d[0]), round(d[1]))]
        else:
            rot = {(0, -1): 0, (0, 1): 180, (1, 0): 270, (-1, 0): 90}[(round(d[0]), round(d[1]))]
        return self.power(name, e, rot, lib=lib)

    def pin_nc(self, sym, pin):
        self.noconn(sym.pin(pin))

    # ---- emit ----
    def _connection_points(self):
        pts = set(self._pin_points)
        for a, b in self.wires:
            pts.add(a); pts.add(b)
        for lst in (self.labels, self.glabels, self.hlabels):
            for item in lst:
                pts.add((item[1], item[2]))
        return pts

    def _normalize_wires(self):
        """Make the wire list canonical, the way the KiCad editor stores it: no zero-length or
        duplicate segments, and every segment split wherever another item connects to its
        interior (wire end, pin, label). The editor breaks wires at such points itself; a file
        that relies on a junction dot over an unsplit wire is not treated as connected by the
        GUI's load-time cleanup, although kicad-cli ERC accepts it."""
        pts = self._connection_points()
        out = []
        for a, b in self.wires:
            if a == b:
                continue
            inner = [p for p in pts if p != a and p != b and _on_segment(p, a, b)]
            inner.sort(key=lambda p: (p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2)
            chain = [a] + inner + [b]
            for s, e in zip(chain, chain[1:]):
                seg = (s, e)
                if seg not in out and (e, s) not in out:
                    out.append(seg)
        self.wires = out
        for a, b in self.wires:            # self-check: nothing may sit on a segment interior now
            for p in pts:
                assert not (p != a and p != b and _on_segment(p, a, b)), (self.filename, p, a, b)

    def _junctions(self):
        """Junction dots by KiCad's rule: three or more distinct exits at a point, where each wire
        end contributes its direction and each pin contributes one more (junction_helpers.cpp)."""
        exits = {}
        for a, b in self.wires:
            for p, q in ((a, b), (b, a)):
                ang = round(math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))) % 360
                exits.setdefault(p, set()).add(ang)
        for i, p in enumerate(self._pin_points):
            if p in exits:
                exits[p].add(10000 + i)
        return [p for p, ex in exits.items() if len(ex) >= 3]

    def _sym_tree(self, ps):
        lib_id = f"{ps.lib}:{ps.name}"
        t = ["symbol", ["lib_id", S(lib_id)], ["at", ps.x, ps.y, ps.rot]]
        if ps.mirror:
            t.append(["mirror", ps.mirror])
        t += [["unit", ps.unit], ["exclude_from_sim", "no"], ["in_bom", "yes" if ps.in_bom else "no"],
              ["on_board", "yes" if ps.on_board else "no"], ["dnp", "yes" if ps.dnp else "no"],
              ["uuid", S(ps.uuid)]]
        # property placement
        (rx, ry, ra), (vx, vy, va) = self._prop_place(ps)
        is_pwr = getattr(ps, "is_power", False)
        t.append(_prop("Reference", ps.ref, rx, ry, ra, hide=is_pwr))
        t.append(_prop("Value", ps.value, vx, vy, va, hide=ps.hide_value))
        t.append(_prop("Footprint", ps.footprint, ps.x, ps.y, 0, hide=True))
        t.append(_prop("Datasheet", ps.datasheet, ps.x, ps.y, 0, hide=True))
        t.append(_prop("Description", ps.description, ps.x, ps.y, 0, hide=True))
        if ps.lcsc:
            t.append(_prop("LCSC", ps.lcsc, ps.x, ps.y, 0, hide=True))
        for k, v in ps.props.items():
            t.append(_prop(k, v, ps.x, ps.y, 0, hide=True))
        for p in ps._pins:
            t.append(["pin", S(p["number"]), ["uuid", S(uid())]])
        path = "/" + self.root_uuid + ("/" + self.path_uuid if self.path_uuid else "")
        t.append(["instances", ["project", S(self.project), ["path", S(path), ["reference", S(ps.ref)], ["unit", ps.unit]]]])
        return t

    @staticmethod
    def _tw(txt, size=1.27):
        return len(txt) * size * 0.9

    def _prop_place(self, ps):
        """Reference and value positions, ((x, y, angle), (x, y, angle)), centre-justified.
        Centre justification is used on purpose: KiCad flips left/right justification of fields
        on mirrored symbols, and rotates field text on 90/270 symbols (angle 90 cancels that)."""
        bx0, by0, bx1, by1 = ps.bbox()
        small = (bx1 - bx0) < 6.0 or (by1 - by0) < 6.0
        is_pwr = getattr(ps, "is_power", False)
        ang = 90 if ps.rot % 180 == 90 else 0
        tall = (by1 - by0) >= (bx1 - bx0)
        wr, wv = self._tw(ps.ref), self._tw(ps.value)

        def from_pos(pos, w):
            x, y, j = pos
            return (x + w / 2 if j == "left" else x - w / 2 if j == "right" else x, y)

        if ps.ref_pos:
            rx, ry = from_pos(ps.ref_pos, wr)
        elif is_pwr:
            rx, ry = ps.x, ps.y
        elif small:
            rx, ry = (bx1 + 0.6 + wr / 2, (by0 + by1) / 2 - 1.0) if tall else ((bx0 + bx1) / 2, by0 - 1.0)
        else:
            rx, ry = bx0 + wr / 2, by0 - 1.2
        if ps.val_pos:
            vx, vy = from_pos(ps.val_pos, wv)
        elif is_pwr:
            # put the name beyond the body, on the side away from the wire end (works for any rotation)
            cx, cy = (bx0 + bx1) / 2 - ps.x, (by0 + by1) / 2 - ps.y
            if ps.name == "PWR_FLAG" and ps.rot == 0 and getattr(ps, "flag_text", "below") == "below":
                cy = 1.0        # flag text goes under the wire, so it cannot collide with the rail name next to it
                by1 = ps.y + 0.4
            if abs(cy) >= abs(cx):
                vx, vy = ps.x, (by0 - 1.0 if cy < 0 else by1 + 1.2)
            else:
                vx, vy = (bx0 - 0.6 - wv / 2 if cx < 0 else bx1 + 0.6 + wv / 2), ps.y
        elif small:
            vx, vy = (bx1 + 0.6 + wv / 2, (by0 + by1) / 2 + 1.0) if tall else ((bx0 + bx1) / 2, by1 + 1.2)
        else:
            vx, vy = bx0 + wv / 2, by1 + 1.2
        return (rx, ry, ang), (vx, vy, ang)

    def _prop_extents(self, ps):
        """Visible reference/value text boxes of a placed symbol: [(label, extent), ...]."""
        (rx, ry, ra), (vx, vy, va) = self._prop_place(ps)
        out = []
        for label, txt, x, y, ang, hidden in ((f"{ps.ref}.ref", ps.ref, rx, ry, ra, getattr(ps, "is_power", False)),
                                             (f"{ps.ref}.value", ps.value, vx, vy, va, ps.hide_value)):
            if hidden:
                continue
            w, h = self._tw(txt), 1.27 * 1.4
            # field text of a 90/270 symbol is written with angle 90 so it renders horizontally
            out.append((label, (x - w / 2, y - h / 2, x + w / 2, y + h / 2)))
        return out

    def tree(self):
        self._normalize_wires()
        root = ["kicad_sch", ["version", FMT_VERSION], ["generator", S("lazergamebox_gen")],
                ["generator_version", S("10.0")], ["uuid", S(self.uuid)], ["paper", S(self.paper)]]
        root.append(["title_block", ["title", S(self.title)], ["rev", S(self.rev)], ["company", S(self.company)]])
        ls = ["lib_symbols"]
        for lib_id in sorted(self.lib_symbols):
            ls.append(self.lib_symbols[lib_id])
        root.append(ls)
        for (x0, y0, x1, y1) in self.rects:
            root.append(["rectangle", ["start", x0, y0], ["end", x1, y1],
                         ["stroke", ["width", 0.2], ["type", "dash"]], ["fill", ["type", "none"]], ["uuid", S(uid())]])
        for (txt, x, y, size, rot, bold, justify) in self.texts:
            eff = ["effects", ["font", ["size", size, size]] + ([["bold", "yes"]] if bold else []), ["justify"] + justify.split()]
            root.append(["text", S(txt), ["exclude_from_sim", "no"], ["at", x, y, rot], eff, ["uuid", S(uid())]])
        for j in self._junctions():
            root.append(["junction", ["at", j[0], j[1]], ["diameter", 0], ["color", 0, 0, 0, 0], ["uuid", S(uid())]])
        for (x, y) in self.noconns:
            root.append(["no_connect", ["at", x, y], ["uuid", S(uid())]])
        for a, b in self.wires:
            root.append(["wire", ["pts", ["xy", a[0], a[1]], ["xy", b[0], b[1]]],
                         ["stroke", ["width", WIRE_WIDTH], ["type", "default"]], ["uuid", S(uid())]])
        for (txt, x, y, rot, justify) in self.labels:
            j = justify or _label_justify(rot)
            root.append(["label", S(txt), ["at", x, y, rot],
                         ["effects", ["font", ["size", 1.27, 1.27]], ["justify"] + j.split()], ["uuid", S(uid())]])
        for (txt, x, y, rot, shape) in self.glabels:
            j = _label_justify(rot)
            root.append(["global_label", S(txt), ["shape", shape], ["at", x, y, rot],
                         ["effects", ["font", ["size", 1.27, 1.27]], ["justify"] + j.split()], ["uuid", S(uid())],
                         _prop("Intersheetrefs", "${INTERSHEET_REFS}", x, y, rot, hide=True)])
        for (txt, x, y, rot, shape) in self.hlabels:
            j = _label_justify(rot)
            root.append(["hierarchical_label", S(txt), ["shape", shape], ["at", x, y, rot],
                         ["effects", ["font", ["size", 1.27, 1.27]], ["justify"] + j.split()], ["uuid", S(uid())]])
        for ps in self.symbols:
            root.append(self._sym_tree(ps))
        for sh in self.sheets:
            x, y = sh["at"]; w, h = sh["size"]
            t = ["sheet", ["at", x, y], ["size", w, h], ["exclude_from_sim", "no"], ["in_bom", "yes"],
                 ["on_board", "yes"], ["dnp", "no"], ["fields_autoplaced", "yes"],
                 ["stroke", ["width", 0.15], ["type", "solid"]], ["fill", ["color", 0, 0, 0, 0.0]],
                 ["uuid", S(sh["uuid"])],
                 _prop("Sheetname", sh["name"], x, y - 0.8, 0, justify="left bottom", size=1.5),
                 _prop("Sheetfile", sh["filename"], x, y + h + 0.8, 0, justify="left top", size=1.27)]
            for (pname, shape, px, py, rot) in sh["pins"]:
                t.append(["pin", S(pname), shape, ["at", px, py, rot],
                          ["effects", ["font", ["size", 1.27, 1.27]], ["justify"] + _label_justify(rot).split()],
                          ["uuid", S(uid())]])
            t.append(["instances", ["project", S(self.project), ["path", S("/" + self.root_uuid), ["page", S(str(sh["page"]))]]]])
            root.append(t)
        if self.path_uuid is None:
            si = ["sheet_instances", ["path", S("/"), ["page", S("1")]]]
            root.append(si)
        return root

    def write(self, directory):
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, self.filename)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(to_sexpr(self.tree()) + "\n")
        return path


# ---------- helpers ----------
def _deepcopy(t):
    if isinstance(t, list):
        return [_deepcopy(c) for c in t]
    return t


def _on_segment(p, a, b, eps=1e-3):
    if abs(a[0] - b[0]) < eps:   # vertical
        return abs(p[0] - a[0]) < eps and min(a[1], b[1]) - eps < p[1] < max(a[1], b[1]) + eps
    if abs(a[1] - b[1]) < eps:   # horizontal
        return abs(p[1] - a[1]) < eps and min(a[0], b[0]) - eps < p[0] < max(a[0], b[0]) + eps
    return False


def _dir_to_rot(d):
    """Label rotation so the text runs away from the wire end (d = outward direction)."""
    dx, dy = round(d[0]), round(d[1])
    return {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[(dx, dy)]


def _label_justify(rot):
    return {0: "left bottom", 180: "right bottom", 90: "left bottom", 270: "right bottom"}[rot % 360]

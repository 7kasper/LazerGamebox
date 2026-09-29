"""Simulate what the KiCad 10.0.3 GUI does to a schematic on load (FixupJunctionsAfterImport,
SCHEMATIC::CleanUp junction pruning + collinear wire merging) and then the connection graph,
so generator output can be checked against GUI ERC "pin not connected" results offline.

Rules transcribed from eeschema/junction_helpers.cpp, sch_screen.cpp, schematic.cpp and
connection_graph.cpp at tag 10.0.3.
"""
import math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _on_seg(p, a, b, tol=1e-6):
    if p == a or p == b:
        return False
    (px, py), (ax, ay), (bx, by) = p, a, b
    cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
    if abs(cross) > tol:
        return False
    return min(ax, bx) - tol <= px <= max(ax, bx) + tol and min(ay, by) - tol <= py <= max(ay, by) + tol


def _angle(frm, to):
    return round(math.degrees(math.atan2(-(to[1] - frm[1]), to[0] - frm[0]))) % 360


def _collinear_touch_or_overlap(w1, w2):
    """Return merged segment if the two segments are collinear and touch or overlap, else None."""
    (a1, b1), (a2, b2) = w1, w2
    dx1, dy1 = b1[0] - a1[0], b1[1] - a1[1]
    dx2, dy2 = b2[0] - a2[0], b2[1] - a2[1]
    if abs(dx1 * dy2 - dy1 * dx2) > 1e-6:
        return None                       # not parallel
    if abs((a2[0] - a1[0]) * dy1 - (a2[1] - a1[1]) * dx1) > 1e-6:
        return None                       # parallel but not on the same line
    pts = sorted([a1, b1, a2, b2])
    lo1, hi1 = sorted([a1, b1]); lo2, hi2 = sorted([a2, b2])
    if hi1 < lo2 or hi2 < lo1:
        return None                       # disjoint
    return (pts[0], pts[-1]), (hi1 == lo2 and lo2 not in (lo1,)) or (hi2 == lo1 and lo1 not in (lo2,)) and True


class Model:
    def __init__(self, wires, junctions, pins, labels):
        self.wires = [tuple(w) for w in wires]            # [(a, b)]
        self.junctions = set(junctions)
        self.pins = dict(pins)                             # point -> [names]
        self.labels = set(labels)

    # ---- AnalyzePoint (10.0.3) ----
    def analyze(self, p, break_crossings):
        has_dot = p in self.junctions
        lines = [w for w in self.wires if p in w or _on_seg(p, *w)]
        if not break_crossings and not has_dot:
            # temporarily merge collinear touching/overlapping lines
            changed = True
            while changed:
                changed = False
                for i in range(len(lines)):
                    for j in range(i + 1, len(lines)):
                        m = _collinear_touch_or_overlap(lines[i], lines[j])
                        if m:
                            lines[i] = m[0]; del lines[j]; changed = True; break
                    if changed:
                        break
        angles = set(); mids = []; breaklines = False
        for w in lines:
            if p in w:
                other = w[1] if w[0] == p else w[0]
                angles.add(_angle(p, other)); breaklines = True
            elif _on_seg(p, *w):
                if break_crossings:
                    breaklines = True
                mids.append(w)
        uniq = 10000
        for _ in self.pins.get(p, []):
            angles.add(uniq); uniq += 1; breaklines = True
        if p in self.labels:
            breaklines = True
        if breaklines:
            for w in mids:
                angles.add(_angle(p, w[0])); angles.add(_angle(p, w[1]))
        return dict(is_junction=len(angles) >= 3, has_dot=has_dot)

    def connection_points(self):
        pts = set(self.junctions) | set(self.pins) | set(self.labels)
        for a, b in self.wires:
            pts.add(a); pts.add(b)
        return pts

    def break_wires_at(self, p):
        new = []
        for w in self.wires:
            if _on_seg(p, *w):
                new += [(w[0], p), (p, w[1])]
            else:
                new.append(w)
        self.wires = new

    # ---- SCHEMATIC::FixupJunctionsAfterImport ----
    def fixup(self):
        n = 0
        for p in sorted(self.connection_points()):
            info = self.analyze(p, False)
            if info["is_junction"] and not info["has_dot"]:
                self.junctions.add(p); self.break_wires_at(p); n += 1
        return n

    # ---- SCHEMATIC::CleanUp ----
    def cleanup(self):
        removed = [j for j in self.junctions if not self.analyze(j, False)["is_junction"]]
        for j in removed:
            self.junctions.discard(j)
        merged = 0
        changed = True
        while changed:
            changed = False
            for i in range(len(self.wires)):
                for j in range(i + 1, len(self.wires)):
                    w1, w2 = self.wires[i], self.wires[j]
                    if w1 == w2 or set(w1) == set(w2):
                        del self.wires[j]; changed = True; break
                    m = _collinear_touch_or_overlap(w1, w2)
                    if not m:
                        continue
                    lo1, hi1 = sorted(w1); lo2, hi2 = sorted(w2)
                    touching = hi1 == lo2 or hi2 == lo1
                    touch = hi1 if hi1 == lo2 else lo1
                    if touching and self.analyze(touch, False)["is_junction"]:
                        continue
                    self.wires[i] = m[0]; del self.wires[j]; changed = True; merged += 1; break
                if changed:
                    break
        return removed, merged

    # ---- CONNECTION_GRAPH::updateItemConnectivity (endpoints + junction pass-through) ----
    def nets(self):
        parent = {}
        def find(x):
            while parent.setdefault(x, x) != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x
        def union(a, b):
            parent[find(a)] = find(b)
        for idx, (a, b) in enumerate(self.wires):
            union(("w", idx), ("p", a)); union(("w", idx), ("p", b))
        for j in self.junctions:
            for idx, w in enumerate(self.wires):
                if _on_seg(j, *w):
                    union(("w", idx), ("p", j))
        for p, names in self.pins.items():
            for n in names:
                union(("pin", n), ("p", p))
        groups = {}
        for p, names in self.pins.items():
            for n in names:
                groups.setdefault(find(("pin", n)), []).append(n)
        return groups


def model_from_sheet(sh):
    pins = {}
    for ps in sh.symbols:
        for num, nm, pt, typ in ps.pins():
            pins.setdefault(pt, []).append(f"{ps.ref}.{num}")
    labels = {(x, y) for (_, x, y, *_r) in sh.labels} | {(x, y) for (_, x, y, *_r) in sh.glabels}
    sh._normalize_wires()
    return Model(sh.wires, sh._junctions(), pins, labels)


def unconnected_pins(sh):
    m = model_from_sheet(sh)
    before = m.nets()
    m.fixup(); m.cleanup()
    after = m.nets()
    lonely = sorted(n for g in after.values() if len(g) == 1 for n in g)
    # only report pins that were in a multi-pin net before the GUI transformations
    was_ok = {n for g in before.values() if len(g) > 1 for n in g}
    return [n for n in lonely if n in was_ok]


if __name__ == "__main__":
    import gen_schematic as g
    from kisch import Sheet
    root = Sheet("LazerGamebox", "LazerGamebox.kicad_sch", title="LazerGamebox", extra_dirs=g.EXTRA, paper="A3")
    names = ["power", "mcu", "radio", "lora_gps", "audio", "io"]
    sheets = {n: Sheet("LazerGamebox", f"{n}.kicad_sch", root_uuid=root.uuid, sheet_path_uuid="x", title=n, extra_dirs=g.EXTRA, paper="A3") for n in names}
    g.gen_root(root, sheets)
    for n in names:
        getattr(g, f"gen_{n}")(sheets[n])
    total = 0
    for n in names:
        bad = unconnected_pins(sheets[n])
        total += len(bad)
        print(n, len(bad), bad)
    print("total pins the GUI would report as unconnected:", total)

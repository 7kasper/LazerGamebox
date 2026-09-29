"""Audit every footprint used in the schematic: library exists, .kicad_mod exists, 3D model file exists,
pad count vs symbol pin count. Uses the global and project fp-lib-tables like KiCad does."""
import os, re, subprocess, sys, tempfile, glob
HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, "..", "hardware"))
K = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
ENV = {"KICAD10_FOOTPRINT_DIR": r"C:\Program Files\KiCad\10.0\share\kicad\footprints",
       "KICAD10_3DMODEL_DIR": r"C:\Program Files\KiCad\10.0\share\kicad\3dmodels",
       "KIPRJMOD": HW}


def lib_table(path):
    """Parse an fp-lib-table; entries of type Table point at another table (KiCad 10 global table)."""
    if not os.path.exists(path):
        return {}
    s = open(path, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r'\(name "([^"]+)"\)\s*\(type "([^"]+)"\)\s*\(uri "([^"]+)"\)', s):
        name, typ, uri = m.groups()
        if typ == "Table":
            out.update(lib_table(expand(uri)))
        else:
            out[name] = uri
    return out


def expand(p):
    for k, v in ENV.items():
        p = p.replace("${" + k + "}", v)
    return p


libs = lib_table(os.path.join(os.environ["APPDATA"], "kicad", "10.0", "fp-lib-table"))
libs.update(lib_table(os.path.join(HW, "fp-lib-table")))

xmlp = os.path.join(tempfile.gettempdir(), "lgb_fp.xml")
subprocess.run([K, "sch", "export", "netlist", "--format", "kicadxml", "-o", xmlp, os.path.join(HW, "LazerGamebox.kicad_sch")],
               check=True, capture_output=True)
xml = open(xmlp, encoding="utf-8").read()
comps = []
for m in re.finditer(r'<comp ref="([^"]+)">(.*?)</comp>', xml, re.S):
    ref, body = m.group(1), m.group(2)
    fp = re.search(r"<footprint>([^<]*)</footprint>", body)
    val = re.search(r"<value>([^<]*)</value>", body)
    lib = re.search(r'<libsource lib="([^"]*)" part="([^"]*)"', body)
    dnp = 'dnp="' in body or "<property name=\"dnp\"" in body
    comps.append((ref, val.group(1) if val else "", fp.group(1) if fp else "", lib.group(1) + ":" + lib.group(2) if lib else "", dnp))
pins = {}
for m in re.finditer(r'<libpart lib="([^"]+)" part="([^"]+)">(.*?)</libpart>', xml, re.S):
    nums = re.findall(r'<pin num="([^"]+)"', m.group(3))
    pins[m.group(1) + ":" + m.group(2)] = nums

rows, problems = [], []
for ref, val, fp, libpart, dnp in comps:
    if not fp:
        problems.append(f"{ref}: no footprint"); continue
    lib, name = fp.split(":", 1)
    if lib not in libs:
        problems.append(f"{ref}: footprint library {lib!r} not in fp-lib-table"); continue
    modp = os.path.join(expand(libs[lib]), name + ".kicad_mod")
    if not os.path.exists(modp):
        problems.append(f"{ref}: {fp} -> file missing {modp}"); continue
    mod = open(modp, encoding="utf-8").read()
    pads = set(re.findall(r'\(pad\s+"?([^"\s)]*)"?\s', mod))
    pads.discard("")
    models = re.findall(r'\(model "([^"]+)"', mod)
    model_ok = []
    for mp in models:
        mp2 = expand(mp)
        model_ok.append(os.path.exists(mp2))
    pin_nums = set(pins.get(libpart, []))
    # symbol pins that carry a number but have no pad (ignore stacked/hidden duplicates)
    missing_pads = sorted(p for p in pin_nums if p not in pads and p.isdigit() or (p not in pads and not p.isdigit()))
    extra_pads = sorted(p for p in pads if p not in pin_nums)
    status = "ok"
    if not models:
        status = "NO 3D MODEL"
    elif not all(model_ok):
        status = "3D MODEL FILE MISSING"
    rows.append((ref, val, fp, len(pads), len(pin_nums), status, missing_pads, extra_pads, dnp))
    if status != "ok":
        problems.append(f"{ref} {fp}: {status} {models}")
    if missing_pads:
        problems.append(f"{ref} {fp}: symbol pins without pad: {missing_pads}")
    if extra_pads and not all(p.isalpha() or p in ("MP", "SH", "S1", "S2") for p in extra_pads):
        problems.append(f"{ref} {fp}: pads without symbol pin: {extra_pads}")

seen = set()
print(f"{'ref':8} {'value':22} {'footprint':58} pads pins status")
for r in sorted(rows):
    key = r[2]
    mark = "" if key not in seen else "  (same fp)"
    seen.add(key)
    print(f"{r[0]:8} {r[1][:22]:22} {r[2][:58]:58} {r[3]:4} {r[4]:4} {r[5]}{mark}")
print("\n---- problems:")
for p in problems:
    print(" ", p)
print(f"\n{len(rows)} components, {len(set(r[2] for r in rows))} distinct footprints, {len(problems)} problems")

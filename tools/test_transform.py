"""Empirical check of the symbol placement transform: place SS8050 in all orientations,
put a label exactly on each computed pin end-point, export a netlist with kicad-cli and
verify every label ended up on the intended pin."""
import os, subprocess, sys, re, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from kisch import Sheet

KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
out = os.path.join(tempfile.gettempdir(), "kisch_test")
sh = Sheet("kisch_test", "kisch_test.kicad_sch", title="transform test")
n = 0
expect = {}
for rot in (0, 90, 180, 270):
    for mirror in (None, "x", "y"):
        n += 1
        x, y = 30 + 40 * ((n - 1) % 4), 30 + 40 * ((n - 1) // 4)
        q = sh.symbol("Transistor_BJT:SS8050", f"Q{n}", "SS8050", (x, y), rot=rot, mirror=mirror)
        for pin in ("B", "C", "E"):
            name = f"Q{n}_{pin}"
            e = sh.pin_label(q, pin, name, length=2.54)
            expect[name] = (f"Q{n}", pin)
        # also a resistor with a power symbol and a stub
        r = sh.symbol("Device:R", f"R{n}", "10k", (x + 15, y), rot=rot, mirror=mirror)
        sh.pin_label(r, "1", f"R{n}_1", kind="global", shape="passive")
        sh.pin_power(r, "2", "GND")
        expect[f"R{n}_1"] = (f"R{n}", "1")
p = sh.write(out)
net = os.path.join(out, "test.xml")
r = subprocess.run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", net, p], capture_output=True, text=True)
print(r.stdout[-800:], r.stderr[-800:])
xml = open(net, encoding="utf-8").read()
# parse nets
ok = bad = 0
for m in re.finditer(r'<net code="\d+" name="([^"]+)"[^>]*>(.*?)</net>', xml, re.S):
    name, body = m.group(1), m.group(2)
    nodes = re.findall(r'<node ref="([^"]+)" pin="([^"]+)"', body)
    name = name.lstrip("/")
    if name in expect:
        ref, pin = expect[name]
        # pin number lookup: SS8050 B=1 E=2 C=3
        want = {"B": "1", "E": "2", "C": "3", "1": "1"}[pin]
        if (ref, want) in nodes:
            ok += 1
        else:
            bad += 1; print("BAD", name, nodes)
print("ok", ok, "bad", bad, "expected", len(expect))
gnd = re.search(r'<net code="\d+" name="GND"[^>]*>(.*?)</net>', xml, re.S)
print("GND nodes:", len(re.findall(r'<node', gnd.group(1))) if gnd else None)

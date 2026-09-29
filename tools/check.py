"""Regenerate the schematic, run ERC, summarise it, export PDF and rasterise pages to PNG.
Usage: python tools/check.py [--no-pdf]"""
import os, sys, subprocess, json, collections
HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.join(HERE, "..", "hardware")
K = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
TMP = os.environ.get("TMPDIR", os.environ.get("TEMP"))

subprocess.run([sys.executable, os.path.join(HERE, "gen_schematic.py")], check=True)
sch = os.path.join(HW, "LazerGamebox.kicad_sch")
erc = os.path.join(HW, "erc.json")
if os.path.exists(erc):
    os.remove(erc)
r = subprocess.run([K, "sch", "erc", "--severity-all", "--format", "json", "-o", erc, sch], capture_output=True, text=True)
print(r.stdout.strip()[-300:], r.stderr.strip()[-300:])
if os.path.exists(erc):
    d = json.load(open(erc, encoding="utf-8"))
    cnt = collections.Counter(); items = []
    for sh in d.get("sheets", []):
        for v in sh.get("violations", []):
            cnt[(v["severity"], v["type"])] += 1
            items.append((sh["path"], v["severity"], v["type"], v["description"][:120],
                          [(i.get("description", "")[:80]) for i in v.get("items", [])][:2]))
    for k, n in sorted(cnt.items()):
        print(n, k)
    print("---- errors:")
    for it in items:
        if it[1] == "error":
            print(it)
    print("---- warnings:")
    for it in [i for i in items if i[1] == "warning"][:60]:
        print(it)
if "--no-pdf" not in sys.argv:
    pdf = os.path.join(TMP, "sch.pdf")
    r = subprocess.run([K, "sch", "export", "pdf", "-o", pdf, sch], capture_output=True, text=True)
    print(r.stdout.strip()[-200:], r.stderr.strip()[-200:])
    if os.path.exists(pdf):
        import pymupdf
        doc = pymupdf.open(pdf)
        for i in range(len(doc)):
            doc[i].get_pixmap(dpi=int(sys.argv[sys.argv.index("--dpi") + 1]) if "--dpi" in sys.argv else 75).save(os.path.join(TMP, f"sch_p{i + 1}.png"))
        print("pages", len(doc), "->", TMP)

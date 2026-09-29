"""Regenerate docs/pinmap.md from the schematic netlist (kicad-cli), so the doc can never drift."""
import os, re, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.join(HERE, "..", "hardware")
K = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
xmlp = os.path.join(tempfile.gettempdir(), "lgb_pinmap.xml")
subprocess.run([K, "sch", "export", "netlist", "--format", "kicadxml", "-o", xmlp, os.path.join(HW, "LazerGamebox.kicad_sch")],
               check=True, capture_output=True)
xml = open(xmlp, encoding="utf-8").read()
pins = {}
for m in re.finditer(r'<net code="\d+" name="([^"]+)"[^>]*>(.*?)</net>', xml, re.S):
    for node in re.finditer(r'<node ref="([^"]+)" pin="([^"]+)"([^/]*)/>', m.group(2)):
        pf = re.search(r'pinfunction="([^"]*)"', node.group(3))
        name = pf.group(1) if pf else ""
        name = re.sub(r'_\d+$', '', name)
        pins[(node.group(1), node.group(2))] = (m.group(1), name)

def table(ref, title, cols):
    rows = [(int(p), f, n) for (r, p), (n, f) in pins.items() if r == ref and p.isdigit() and not n.startswith("unconnected")]
    out = [f"## {title}", "", f"| {cols[0]} | {cols[1]} | Net |", "|---|---|---|"]
    out += [f"| {p} | {f} | {n} |" for p, f, n in sorted(rows)]
    return out + [""]

out = ["# Pin map", "",
       "Generated from the schematic netlist by `python tools/check_pinmap.py`; do not edit by hand.",
       "Net names are the global labels in the schematic, `/mcu/EN` style names are sheet-local nets.",
       "Unconnected (NC) pins are omitted.", ""]
out += table("U201", "U201 ESP32-WROOM-32E-N16", ("Module pin", "GPIO"))
out += table("U205", "U205 TCA9555 I2C GPIO expander (address 0x20, INT on GPIO32)", ("Pin", "Port"))
out += table("U301", "U301 SA818S-U radio module", ("Pin", "Name"))
out += table("U401", "U401 Ra-01SH LoRa module", ("Pin", "Name"))
out += table("U402", "U402 ATGM336H-5N31 GNSS module", ("Pin", "Name"))
out += table("J601", "J601 display ZIF (HS20HS072RX pinout)", ("Pin", "Name"))
out += ["## Strapping and analog notes", "",
        "- GPIO0 boot button, GPIO2 pulled down 10k (LCD_BL), GPIO12 has no pull-up, GPIO5 and GPIO15 keep internal pull-ups.",
        "- All ADC inputs on ADC1: GPIO34 pot, GPIO36 radio audio, GPIO39 VBAT/2. GPIO35 is the IR receiver (digital).",
        "- UART0 (GPIO1/3) is the CH340C programming port only. UART1 = GPS (shared with the DNP cellular module), UART2 = radio.",
        "- Wake sources from deep sleep: GPIO32 (expander INT: buttons, motion, squelch, PPS) and GPIO33 (LoRa DIO1).", ""]
p = os.path.join(HERE, "..", "docs", "pinmap.md")
open(p, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("wrote", os.path.normpath(p), len(pins), "pins")

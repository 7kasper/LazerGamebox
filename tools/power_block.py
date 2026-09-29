"""Power sheet, left half: USB-C input, BQ25601 charger with power path, cells + protection,
USB PD sink and fuel gauge. Split out of gen_schematic.py because it is the largest block."""
from gen_common import *

G = "GND"


def usb_charger_cells(sh, tp_fn, gauge=True):
    # ---------------- USB-C input ----------------
    sh.box(12, 20, 122, 110, "USB-C INPUT")
    j = sh.symbol("Connector:USB_C_Receptacle_USB2.0_16P", "J101", "USB-C 16P", (40, 62), footprint=FP_USBC,
                  lcsc="C165948", description="Korean Hroparts TYPE-C-31-M-12, 16 pin USB 2.0 receptacle")
    vb = j.pin("A4")
    sh.wire(vb, (70, vb[1]))
    sh.power("VBUS", (70, vb[1]))
    sh.wire((70, vb[1]), (76, vb[1]))
    sh.flag((76, vb[1]))
    sh.pin_label(j, "A5", "CC1", length=7.62, kind="local")      # Rd is inside the HUSB238
    sh.pin_label(j, "B5", "CC2", length=7.62, kind="local")
    esd = sh.symbol("Power_Protection:USBLC6-2SC6", "D101", "USBLC6-2SC6", (95, 62),
                    footprint="Package_TO_SOT_SMD:SOT-23-6", lcsc="C7519")
    io1, io2 = esd.pin("1"), esd.pin("3")           # I/O1 (y 62), I/O2 (y 64.54)
    dm1, dm2 = j.pin("A7"), j.pin("B7")               # D- pair, upper
    dp1, dp2 = j.pin("A6"), j.pin("B6")               # D+ pair, lower
    xn = dm1[0] + 4
    sh.wire(dm1, (xn, dm1[1]), (xn, io1[1]), io1)
    sh.wire(dm2, (xn, dm2[1]))
    xm = dp1[0] + 8
    sh.wire(dp1, (xm, dp1[1]), (xm, dp2[1]), dp2)
    sh.wire((xm, io2[1]), io2)
    sh.pin_label(esd, "6", "USB_D-", length=5.08, kind="global", shape="passive")
    sh.pin_label(esd, "4", "USB_D+", length=5.08, kind="global", shape="passive")
    sh.pin_power(esd, "5", "VBUS", length=2.54)
    sh.pin_power(esd, "2", G, length=2.54)
    sh.pin_nc(j, "A8"); sh.pin_nc(j, "B8")
    sh.pin_power(j, "A1", G, length=2.54)
    sh.pin_power(j, "SH", G, length=2.54)
    sh.text("CC1/CC2 go to the HUSB238 PD sink (Rd inside it). D+/D- both rows joined (reversible plug).\nVBUS: 5 V only, up to 3 A negotiated; USBLC6 clamps VBUS and the data lines.", (14, 100), size=1.27)

    # ---------------- Charger + power path ----------------
    sh.box(130, 20, 232, 184, "CHARGER + POWER PATH (BQ25601, 2 A, I2C 0x6B)")
    u = sh.symbol("LazerGamebox:BQ25601", "U101", "BQ25601", (180, 58), lcsc="C468236")
    vbus = u.pin("24")
    sh.pin_power(u, "24", "VBUS", length=12.7)
    vac = u.pin("1")
    sh.wire(vac, (vac[0] - 5, vac[1]), (vac[0] - 5, vbus[1]))        # VAC must be tied to VBUS
    c = C(sh, "C101", "1uF", (vbus[0] - 9, vbus[1] - 8))               # 1 uF 50 V at the VBUS pin
    sh.wire(c.pin("2"), (vbus[0] - 9, vbus[1]))
    sh.pin_power(c, "1", G, length=2.54)
    sh.pin_label(u, "23", "PMID", length=10.16, kind="local")
    sh.pin_label(u, "22", "REGN", length=7.62, kind="local")
    sh.pin_label(u, "2", "PSEL", length=7.62, kind="local")
    sh.pin_power(u, "9", G, length=5.08)                                # /CE low: charging enabled, software CHG_CONFIG decides
    sh.pin_label(u, "12", "QON", length=7.62, kind="local")
    sh.pin_label(u, "11", "TS", length=7.62, kind="local")
    sh.pin_label(u, "19", "SW", length=5.08, kind="local")
    sh.pin_label(u, "20", "SW", length=5.08, kind="local")
    sh.pin_label(u, "21", "BTST", length=5.08, kind="local")
    s15, s16 = u.pin("15"), u.pin("16")
    sh.wire(s16, (s16[0] + 3, s16[1]), (s15[0] + 3, s15[1]))
    sh.wire(s15, (s15[0] + 14, s15[1]))
    sh.power("VSYS", (s15[0] + 14, s15[1]), lib="LazerGamebox")
    b13, b14 = u.pin("13"), u.pin("14")
    sh.wire(b14, (b14[0] + 3, b14[1]), (b13[0] + 3, b13[1]))
    sh.wire(b13, (b13[0] + 14, b13[1]))
    sh.power("VBAT", (b13[0] + 14, b13[1]), lib="LazerGamebox")
    sh.pin_label(u, "4", "STAT", length=5.08, kind="local")
    sh.pin_nc(u, "3")                                                   # /PG: status is in the registers
    sh.pin_label(u, "7", "PWR_INT", length=7.62, kind="global", shape="passive")
    sh.pin_label(u, "6", "SDA", length=5.08, kind="global", shape="passive")
    sh.pin_label(u, "5", "SCL", length=5.08, kind="global", shape="passive")
    sh.pin_power(u, "17", G, length=2.54)

    # cells under the IC, all connected through the local labels above
    y0 = 100
    # TS: no NTC in the holders, 50 % of REGN sits in the normal window
    sh.label("REGN", (136, y0), 180)
    sh.wire((136, y0), (154, y0))
    c = C(sh, "C116", "4.7uF", (140, y0 + 8))
    sh.wire(c.pin("1"), (140, y0))
    sh.pin_power(c, "2", G, length=2.54)
    r = R(sh, "R101", "10k", (154, y0 + 6))
    sh.wire(r.pin("1"), (154, y0))
    ts = (154, y0 + 12)
    sh.wire(r.pin("2"), ts, (162, ts[1]))
    sh.label("TS", (162, ts[1]), 0)
    r = R(sh, "R102", "10k", (154, ts[1] + 6))
    sh.wire(r.pin("1"), ts)
    sh.pin_power(r, "2", G, length=2.54)
    # PSEL: high = 500 mA input limit until the ESP32 programs IINDPM
    sh.label("PSEL", (136, y0 + 32), 180)
    r = R(sh, "R103", "10k", (142, y0 + 32), rot=90)
    sh.wire((136, y0 + 32), r.pin("1"))
    sh.pin_power(r, "2", "VBUS", length=3.81)
    # QON: power / wake button, also exits ship mode (hold > 1 s)
    sh.label("QON", (136, y0 + 44), 180)
    sw = sh.symbol("Switch:SW_Push", "SW101", "PWR", (144, y0 + 44), footprint=FP_TACT, lcsc="C318884",
                   description="XKB TS-1187A-B-A-B 5.1 mm tact switch")
    sh.wire((136, y0 + 44), sw.pin("1"))
    sh.pin_power(sw, "2", G, length=2.54)
    # switching cell: SW -> L -> VSYS, BTST bootstrap
    sh.label("SW", (176, y0), 180)
    l = L(sh, "L103", "1uH", (186, y0), rot=90)
    sh.wire((176, y0), l.pin("1"))
    sh.wire(l.pin("2"), (198, y0))
    sh.power("VSYS", (198, y0), lib="LazerGamebox")
    c = C(sh, "C117", "47nF", (176, y0 + 8))
    sh.wire((176, y0), c.pin("1"))
    sh.wire(c.pin("2"), (176, y0 + 14), (182, y0 + 14))
    sh.label("BTST", (182, y0 + 14), 0)
    # PMID hot-loop capacitors
    sh.label("PMID", (204, y0 + 19), 180)
    sh.wire((204, y0 + 19), (220, y0 + 19))
    for ref, x in (("C102", 210), ("C115", 220)):
        c = C(sh, ref, "10uF", (x, y0 + 25))
        sh.wire(c.pin("1"), (x, y0 + 19))
        sh.pin_power(c, "2", G, length=2.54)
    # SYS and BAT capacitors
    cap_between(sh, "C118", "10uF", 176, y0 + 34, "VSYS")
    cap_between(sh, "C119", "10uF", 188, y0 + 34, "VSYS")
    cap_between(sh, "C120", "10uF", 200, y0 + 34, "VBAT")
    # STAT LED: low = charging, high = done, blink = fault
    sh.label("STAT", (222, y0 + 52), 0)
    d = sh.symbol("Device:LED", "D102", "RED CHRG", (214, y0 + 52), rot=180, footprint="LED_SMD:LED_0603_1608Metric",
                  lcsc="C2286", description="KENTO KT-0603R red LED")
    sh.wire(d.pin("K"), (222, y0 + 52))
    r = R(sh, "R104", "1k", (204, y0 + 52), rot=90)
    sh.wire(r.pin("2"), d.pin("A"))
    sh.pin_power(r, "1", "VSYS", length=3.81, lib="LazerGamebox")
    # interrupt pull-up (BQ25601 /INT and the gauge ALRT are open drain, wire-ORed on PWR_INT)
    r = R(sh, "R105", "10k", (160, y0 + 34))       # PWR_INT: BQ25601 /INT and MAX17048 ALRT wire-ORed to GPIO39 (RTC wake)
    r.ref_pos = (158.4, y0 + 34.5, "right"); r.val_pos = (158.4, y0 + 36.5, "right")
    sh.pin_power(r, "1", "+3V3", length=2.54)
    sh.pin_label(r, "2", "PWR_INT", length=3.81, kind="global", shape="passive")
    sh.text("NVDC power path: VSYS runs from USB or the cells; BATFET ship mode = true off.\n"
            "Plug-in defaults: 500 mA input (PSEL high), 2 A charge, 4.208 V. Firmware raises\n"
            "IINDPM after reading the HUSB238, clears EN_HIZ after a QON wake, feeds or\n"
            "disables the 40 s watchdog.", (132, y0 + 66), size=1.1)

    # ---------------- Cells + protection ----------------
    sh.box(12, 118, 122, 258, "2x 18650 IN PARALLEL + PROTECTION (DW01A + FS8205A)")
    bt = sh.symbol("Device:Battery_Cell", "BT101", "18650", (28, 150), footprint=f"{LIB}:BATTERY-SMD_18650-1S-L77.1-W20.7-1",
                   lcsc="C2988620", description="MYOUNG BH-18650-B1BA002 SMT 18650 holder, gold contacts")
    bt2 = sh.symbol("Device:Battery_Cell", "BT102", "18650", (44, 150), footprint=f"{LIB}:BATTERY-SMD_18650-1S-L77.1-W20.7-1",
                    lcsc="C2988620", description="MYOUNG BH-18650-B1BA002 SMT 18650 holder, gold contacts")
    bp, bp2 = bt.pin("+"), bt2.pin("+")
    sh.wire(bp, (bp[0], 136), (bp2[0], 136), bp2)
    sh.power("VBAT", (bp[0], 136), lib="LazerGamebox")
    bm, bm2 = bt.pin("-"), bt2.pin("-")
    sh.wire(bm, (bm[0], 180))
    sh.label("BAT-", (bm[0], 180), 270)
    sh.wire(bm2, (bm2[0], 174), (bm[0], 174))
    sh.wire((bm2[0], 174), (52, 174))
    sh.flag((52, 174))
    dw = sh.symbol("Battery_Management:DW01A", "U102", "DW01A", (78, 200), footprint="Package_TO_SOT_SMD:SOT-23-6",
                   lcsc="C351410", description="PUOLOP DW01A single cell protection IC")
    vcc = dw.pin("5")
    _b = dw.bbox(); dw.val_pos = (_b[2], _b[3] + 1.2, "right")
    sh.wire(vcc, (42, vcc[1]))
    sh.flag((50, vcc[1]), text="above")
    r = R(sh, "R106", "100R", (58, vcc[1] - 8))
    sh.wire(r.pin("2"), (58, vcc[1]))
    sh.pin_power(r, "1", "VBAT", length=2.54, lib="LazerGamebox")
    c = C(sh, "C103", "100nF", (42, vcc[1] + 8))       # left of the GND-pin wire so nothing crosses
    sh.wire(c.pin("1"), (42, vcc[1]))
    sh.wire(c.pin("2"), (42, vcc[1] + 18))
    sh.label("BAT-", (42, vcc[1] + 18), 270)
    gnd = dw.pin("6")
    sh.wire(gnd, (52, gnd[1]))
    sh.label("BAT-", (52, gnd[1]), 180)
    sh.pin_label(dw, "1", "OD", length=3.81, kind="local")
    sh.pin_label(dw, "3", "OC", length=3.81, kind="local")
    sh.pin_nc(dw, "4")
    cs = dw.pin("2")
    sh.wire(cs, (98, cs[1]), (98, cs[1] + 3))
    r = R(sh, "R107", "1k", (98, cs[1] + 6.81))
    sh.pin_power(r, "2", G, length=2.54)
    q = sh.symbol("LazerGamebox:FS8205A", "Q101", "FS8205A", (78, 235), lcsc="C908265")
    sh.pin_label(q, "G1", "OD", length=3.81, kind="local")
    sh.pin_label(q, "G2", "OC", length=3.81, kind="local")
    sh.pin_label(q, "S1", "BAT-", length=3.81, kind="local")
    sh.pin_power(q, "S2", G, length=3.81)
    d1, d2 = q.pin("2"), q.pin("5")
    sh.wire(d1, (d1[0], d1[1] - 2), (d2[0], d2[1] - 2), d2)
    sh.text("Two cells of the same type and age, fitted together (parallel pair, no balancing needed).\nCell negative reaches system GND through the dual MOSFET (BAT- net).\nDW01A: 2.5 V under-voltage, 4.3 V over-voltage,\n150 mV over-current sense (2 to 4 A with the FS8205A).",
            (14, 244), size=1.27)

    # ---------------- USB PD sink + fuel gauge ----------------
    sh.box(130, 188, 232, 274, "PD SINK (HUSB238 0x08)" + (" + GAUGE (MAX17048 0x36)" if gauge else ""))
    h = sh.symbol("LazerGamebox:HUSB238", "U105", "HUSB238", (158, 218), lcsc="C7471904")
    sh.pin_power(h, "1", "VBUS", length=5.08)
    vin = h.pin("1")
    c = C(sh, "C121", "1uF", (vin[0] - 2, vin[1] - 8))
    sh.wire(c.pin("2"), (vin[0] - 2, vin[1]))
    sh.pin_power(c, "1", G, length=2.54)
    sh.pin_nc(h, "2"); sh.pin_nc(h, "3")                              # D+/D- belong to the CH340C
    sh.pin_label(h, "4", "CC1", length=5.08, kind="local")
    sh.pin_label(h, "5", "CC2", length=5.08, kind="local")
    r25, _, _ = pin_series_label(sh, h, "6", "R125", "330R", "SDA", length=22.86, gap=10.16)   # chip is dead without USB
    r25.ref_pos = (r25.x, r25.y - 2.9, None); r25.val_pos = (r25.x, r25.y - 1.2, None)
    r26, _, _ = pin_series_label(sh, h, "7", "R126", "330R", "SCL", length=22.86, gap=2.54)
    r26.ref_pos = (r26.x, r26.y + 1.4, None); r26.val_pos = (r26.x, r26.y + 3.1, None)
    p8, p9 = h.pin("8"), h.pin("9")
    sh.wire(p8, (p8[0] + 4, p8[1]), (p8[0] + 4, p9[1]))
    sh.wire(p9, (p8[0] + 4, p9[1]))
    r = R(sh, "R123", "0R", (p8[0] + 4, p9[1] + 6.35))               # VSET and ISET both 0 R: request 5 V, 1.25 A (matches every 5 V PDO)
    sh.wire((p8[0] + 4, p9[1]), r.pin("1"))
    r.ref_pos = (p8[0] + 5.6, p9[1] + 5.4, "left"); r.val_pos = (p8[0] + 5.6, p9[1] + 7.4, "left")
    sh.pin_power(r, "2", G, length=2.54)
    sh.pin_nc(h, "10")
    sh.pin_power(h, "11", G, length=2.54)
    if gauge:
        g = sh.symbol("LazerGamebox:MAX17048", "U106", "MAX17048", (180, 250), lcsc="C2682616")
        vdd, cell = g.pin("3"), g.pin("2")
        sh.wire(cell, (cell[0] - 3, cell[1]), (vdd[0] - 3, vdd[1]))
        sh.wire(vdd, (vdd[0] - 10, vdd[1]))
        sh.power("VBAT", (vdd[0] - 10, vdd[1]), lib="LazerGamebox")
        c = C(sh, "C122", "100nF", (vdd[0] - 10, vdd[1] + 8))
        c.ref_pos = (vdd[0] - 11.6, vdd[1] + 6.8, "right"); c.val_pos = (vdd[0] - 11.6, vdd[1] + 8.8, "right")
        sh.wire(c.pin("1"), (vdd[0] - 10, vdd[1]))
        sh.pin_power(c, "2", G, length=2.54)
        sh.pin_power(g, "6", G, length=5.08)
        sh.pin_power(g, "1", G, length=5.08)
        sh.pin_label(g, "8", "SDA", length=7.62, kind="global", shape="passive")
        sh.pin_label(g, "7", "SCL", length=7.62, kind="global", shape="passive")
        sh.pin_label(g, "5", "PWR_INT", length=7.62, kind="global", shape="passive")
        sh.pin_power(g, "4", G, length=2.54)
    sh.text("HUSB238 runs from VBUS only; firmware reads its 5 V current capability and sets IINDPM.\nGauge on the cell pair; ALRT and /INT share PWR_INT (P17), firmware clears both.", (132, 268), size=1.1)
    return dict(husb=h)

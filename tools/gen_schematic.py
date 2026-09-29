#!/usr/bin/env python3
"""Generate the LazerGamebox KiCad 10 schematic: root + six hierarchical sheets.

Run:  python tools/gen_schematic.py      (writes hardware/*.kicad_sch and project files)
Cross-sheet nets use global labels; power rails use power symbols. Reference designators
are grouped per sheet: 1xx power, 2xx mcu, 3xx radio, 4xx lora_gps, 5xx audio, 6xx io.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from kisch import Sheet, snap
from gen_common import *

PROJECT = "LazerGamebox"
from power_block import usb_charger_cells

G = "GND"


def title(sh, text, sub=""):
    # inner frame line is at y = 12; boxes start at y = 20
    sh.text(text, (14, 13.2), size=2.5, bold=True)
    if sub:
        sh.text(sub, (14, 16.9), size=1.27)


# ======================================================================================
# POWER
# ======================================================================================
def gen_power(sh):
    title(sh, "POWER: USB-C PD sink, BQ25601 charger with power path, 2x 18650, fuel gauge, 3V3 buck, radio boost, load switches",
          "All switched rails default OFF at power-up (gate pull-downs); firmware enables them through the TCA9555 expander.")

    usb_charger_cells(sh, tp)

    # ---------------- 3V3 buck ----------------
    sh.box(240, 20, 405, 100, "3V3 BUCK, ALWAYS ON (TPS62A02, 2 A, Iq 23 uA)")
    u = sh.symbol("Regulator_Switching:TPS62A02DRL", "U103", "TPS62A02", (300, 48), footprint="Package_TO_SOT_SMD:SOT-563",
                  lcsc="C5350187", description="TI TPS62A02DRLR 2 A synchronous buck, SOT-563")
    vin = u.pin("VIN"); en = u.pin("EN")
    sh.wire(vin, (280, vin[1]))
    sh.power("VSYS", (280, vin[1]), lib="LazerGamebox")
    sh.wire(en, (286, en[1]), (286, vin[1]))
    sw = u.pin("SW")
    l = L(sh, "L101", "1uH", (322, sw[1]), rot=90)
    sh.wire(sw, l.pin("1"))
    sh.wire(l.pin("2"), (352, sw[1]))
    sh.power("+3V3", (352, sw[1]))
    sh.wire((352, sw[1]), (358, sw[1]))
    sh.flag((358, sw[1]))
    rh = R(sh, "R111", "150k", (338, sw[1] + 9))
    sh.wire(rh.pin("1"), (338, sw[1]))
    rl = R(sh, "R112", "33k", (338, sw[1] + 24))
    sh.wire(rh.pin("2"), rl.pin("1"))
    sh.pin_power(rl, "2", G, length=2.54)
    fb = u.pin("FB")
    sh.wire(fb, (314, fb[1]), (314, sw[1] + 16.5), (338, sw[1] + 16.5))
    sh.pin_nc(u, "PG")
    sh.pin_power(u, "GND", G, length=2.54)
    cap_between(sh, "C105", "10uF", 255, 80, "VSYS")
    cap_between(sh, "C106", "100nF", 268, 80, "VSYS")
    cap_between(sh, "C107", "22uF", 372, 80, "+3V3")
    cap_between(sh, "C108", "10uF", 386, 80, "+3V3")
    sh.text("VOUT = 0.6 V x (1 + 100k/22k) = 3.33 V. L = 1 uH (SWPA4030S1R0, 5.7 A sat). fsw 2.4 MHz.\nEN tied to VIN: rail is always on; deep-sleep current is set by the ESP32 and the buck Iq.",
            (242, 91), size=1.27)

    # ---------------- Radio boost ----------------
    sh.box(240, 106, 405, 184, "RADIO SUPPLY: 4.6 V BOOST WITH TRUE DISCONNECT (TPS61023)")
    yb = 140
    u = sh.symbol("LazerGamebox:TPS61023DRL", "U104", "TPS61023", (300, yb), lcsc="C919459")
    vin = u.pin("VIN")
    sh.wire(vin, (270, vin[1]))
    sh.power("VSYS", (270, vin[1]), lib="LazerGamebox")        # behind the load-share FET: on USB the radio does not drain the cell
    sw = u.pin("SW")
    l = L(sh, "L102", "1uH", (290, yb - 18), rot=90)
    sh.wire((270, vin[1]), (270, yb - 18), l.pin("1"))
    sh.wire(l.pin("2"), (322, yb - 18), (322, sw[1]), sw)
    en = u.pin("EN")
    sh.pin_label(u, "EN", "RADIO_EN", length=12.7, kind="global", shape="passive")
    r21 = R(sh, "R121", "4.7k", (en[0] - 12, en[1] - 7))      # expander ports boot as inputs with 100k pull-ups: keep the boost off
    sh.wire(r21.pin("2"), (en[0] - 12, en[1]))
    sh.pin_power(r21, "1", G, length=2.54)
    vo = u.pin("VOUT")
    sh.wire(vo, (345, vo[1]))
    sh.power("RADIO_4V5", (345, vo[1]), lib="LazerGamebox")
    rh = R(sh, "R113", "220k", (335, vo[1] + 9))
    sh.wire(rh.pin("1"), (335, vo[1]))
    rl = R(sh, "R114", "33k", (335, vo[1] + 24))
    sh.wire(rh.pin("2"), rl.pin("1"))
    sh.pin_power(rl, "2", G, length=2.54)
    cff = C(sh, "C113", "1nF", (349, vo[1] + 9))                  # feed-forward across R113: TI asks for it above 40 uF of output capacitance
    sh.wire(cff.pin("1"), (349, vo[1]), (345, vo[1]))
    sh.wire(cff.pin("2"), (349, vo[1] + 16.5), (335, vo[1] + 16.5))
    fb = u.pin("FB")
    sh.wire(fb, (282, fb[1]), (282, vo[1] + 16.5), (335, vo[1] + 16.5))
    sh.pin_power(u, "GND", G, length=2.54)
    cap_between(sh, "C109", "22uF", 255, yb + 25, "VSYS")
    cap_between(sh, "C110", "10uF", 268, yb + 25, "VSYS")
    cap_between(sh, "C111", "22uF", 372, yb + 25, "RADIO_4V5")
    cap_between(sh, "C112", "22uF", 386, yb + 25, "RADIO_4V5")
    sh.text("VOUT = 0.6 V x (1 + 220k/33k) = 4.6 V. Pass-through when the cell is above 4.6 V.\nEN low = output disconnected (< 1 uA): no separate load switch for the radio. 470 uF bulk sits at the module (radio sheet).",
            (242, 178.8), size=1.27)

    # ---------------- Load switches ----------------
    sh.box(240, 188, 405, 252, "LOAD SWITCHES (P-FET high side, N-FET level shift, default OFF)")
    def load_switch(x0, y0, rail_in, rail_out, en_name, qp, qn, rp, rn, soft=None):
        """soft=(r_ref, c_ref): RC soft start on the P-FET gate (large bulk capacitance on the output)."""
        p = PMOS(sh, qp, (x0 + 20, y0 + 10))                 # S left, D right, G bottom
        s, d, g = p.pin("S"), p.pin("D"), p.pin("G")
        sh.wire(s, (x0 + 2, s[1]))
        sh.power(rail_in, (x0 + 2, s[1]), lib=lib_for(rail_in))
        sh.wire(d, (x0 + 36, d[1]))
        sh.power(rail_out, (x0 + 36, d[1]), lib="LazerGamebox")
        sh.wire((x0 + 36, d[1]), (x0 + 42, d[1]))
        sh.flag((x0 + 42, d[1]))
        r = R(sh, rp, "100k", (x0 + 6, y0 + 14))
        sh.wire(r.pin("1"), (x0 + 6, s[1]))
        sh.wire(r.pin("2"), (x0 + 6, y0 + 22), (x0 + 20, y0 + 22))
        sh.wire(g, (x0 + 20, y0 + 22))
        if soft:
            # gate RC: the N-FET pulls the gate down through 10k while 100 nF gate-source slows the edge (about 1 ms)
            rs = R(sh, soft[0], "10k", (x0 + 20, y0 + 28))
            sh.wire((x0 + 20, y0 + 22), rs.pin("1"))
            cs = C(sh, soft[1], "100nF", (x0 + 8, y0 + 28))
            sh.wire(cs.pin("1"), (x0 + 8, y0 + 22))
            sh.wire(cs.pin("2"), (x0 + 8, y0 + 33), (x0 + 2, y0 + 33), (x0 + 2, s[1]))
            n = NMOS(sh, qn, (x0 + 17.46, y0 + 38))
            _b = n.bbox(); n.val_pos = (_b[2] + 0.6, (_b[1] + _b[3]) / 2, "left")
            sh.wire(n.pin("D"), rs.pin("2"))
        else:
            n = NMOS(sh, qn, (x0 + 17.46, y0 + 30))
            _b = n.bbox(); n.val_pos = (_b[2] + 0.6, (_b[1] + _b[3]) / 2, "left")
            sh.wire(n.pin("D"), (x0 + 20, y0 + 22))
        sh.pin_power(n, "S", G, length=2.54)
        gg = n.pin("G")
        sh.wire(gg, (x0 + 2, gg[1]))
        sh.glabel(en_name, (x0 + 2, gg[1]), 180, "passive")
        r2 = R(sh, rn, "10k", (x0 + 6, gg[1] + 7))
        sh.wire(r2.pin("1"), (x0 + 6, gg[1]))
        sh.pin_power(r2, "2", G, length=2.54)
    load_switch(250, 194, "+3V3", "GPS_3V3", "GPS_EN", "Q103", "Q104", "R115", "R116")
    load_switch(302, 194, "+3V3", "LCD_3V3", "LCD_EN", "Q105", "Q106", "R117", "R118")
    load_switch(354, 194, "VSYS", "VBAT_SW", "AUX_EN", "Q107", "Q108", "R119", "R120", soft=("R122", "C114"))
    sh.text("GPS_3V3: GNSS module.  LCD_3V3: display, pot, IR receiver.\nVBAT_SW: audio amp (470 uF bulk, hence the soft start), RGB LEDs, IR LED, backlight.",
            (242, 244), size=1.27)

    f = sh.flag((250, 262))
    sh.wire((250, 262), (250, 266))
    sh.power(G, (250, 266))
    sh.text("PWR_FLAG on GND (ERC only).", (256, 264.5), size=1.0)


# ======================================================================================
# MCU
# ======================================================================================
def gen_mcu(sh):
    title(sh, "MCU: ESP32-WROOM-32E, USB serial (CH340C on its own 3.3 V LDO), accelerometer, I2C GPIO expander",
          "All 26 usable GPIO are used; slow enables, resets and buttons live on the TCA9555 (I2C 0x20). See docs/pinmap.md.")
    sh.box(12, 20, 175, 205, "ESP32-WROOM-32E-N16 (16 MB flash)")
    u = sh.symbol("RF_Module:ESP32-WROOM-32E", "U201", "ESP32-WROOM-32E-N16", (95, 105), footprint=FP_ESP32,
                  lcsc="C701343", description="Espressif ESP32-WROOM-32E-N16 module")
    right = [("IO0", "IO0", "local"), ("TXD0/IO1", "U0TXD", "local"), ("RXD0/IO3", "U0RXD", "local"),
             ("IO2", "LCD_BL", "global"), ("IO4", "LORA_BUSY", "global"), ("IO5", "LORA_CS", "global"),
             ("IO12", "LCD_DC", "global"), ("IO13", "GPS_RX", "global"), ("IO14", "GPS_TX", "global"),
             ("IO15", "LED_DATA", "global"), ("IO16", "RADIO_RX", "global"), ("IO17", "RADIO_TX", "global"),
             ("IO18", "SCK", "global"), ("IO19", "MISO", "global"), ("IO21", "SDA", "global"), ("IO22", "SCL", "global"),
             ("IO23", "MOSI", "global"), ("IO25", "DAC1", "global"), ("IO26", "IR_TX", "global"),
             ("IO27", "RADIO_PTT", "global"), ("IO32", "EXP_INT", "global"), ("IO33", "LORA_DIO1", "global"),
             ("IO34", "ADC_POT", "global"), ("IO35", "IR_RX", "global")]
    for pin, net, kind in right:
        sh.pin_label(u, pin, net, length=10.16, kind=kind, shape="passive")
    sh.pin_label(u, "SENSOR_VP", "ADC_AUDIO", length=7.62, kind="global", shape="passive")
    sh.pin_label(u, "SENSOR_VN", "PWR_INT", length=7.62, kind="global", shape="passive")   # GPIO39: RTC wake on charger / gauge interrupt
    for n in ("17", "18", "19", "20", "21", "22", "32"):
        sh.pin_nc(u, n)
    sh.pin_power(u, "VDD", "+3V3", length=3.81)
    sh.pin_power(u, "GND", G, length=2.54)
    cap_between(sh, "C201", "10uF", 40, 45, "+3V3")
    cap_between(sh, "C202", "100nF", 52, 45, "+3V3")
    # EN: 10k pull-up, 1 uF, reset button, local label EN (auto-reset transistor)
    en = u.pin("EN")
    sh.wire(en, (38, en[1]))
    sh.label("EN", (38, en[1]), 180)
    r = R(sh, "R201", "10k", (58, en[1] - 8))
    sh.wire(r.pin("2"), (58, en[1]))
    sh.pin_power(r, "1", "+3V3", length=2.54)
    c = C(sh, "C203", "1uF", (50, en[1] + 8))
    sh.wire(c.pin("1"), (50, en[1]))
    sh.pin_power(c, "2", G, length=2.54)
    sw = sh.symbol("Switch:SW_Push", "SW201", "RESET", (40.92, en[1] + 14), footprint=FP_TACT, lcsc="C318884",
                   description="XKB TS-1187A-B-A-B 5.1 mm tact switch")
    sh.wire(sw.pin("2"), (sw.pin("2")[0], en[1]))
    sh.pin_power(sw, "1", G, length=2.54)
    # boot button block
    sh.box(12, 212, 175, 262, "BOOT / RESET BUTTONS")
    y = 235
    sh.label("IO0", (30, y), 180)
    r = R(sh, "R202", "10k", (40, y - 8))
    sh.wire((30, y), (52, y))
    sh.wire(r.pin("2"), (40, y))
    sh.pin_power(r, "1", "+3V3", length=2.54)
    sw = sh.symbol("Switch:SW_Push", "SW202", "BOOT", (57.08, y), rot=0, footprint=FP_TACT, lcsc="C318884",
                   description="XKB TS-1187A-B-A-B 5.1 mm tact switch")
    sh.pin_power(sw, "2", G, length=2.54)
    sh.text("IO0 low at reset = download mode. RESET pulls EN low.\nStrapping: IO2 has a 10k pull-down (R203, net LCD_BL),\nIO12 has no pull-up (flash stays 3.3 V),\nIO5 and IO15 keep their internal pull-ups.",
            (75, 226), size=1.27)
    r = R(sh, "R203", "10k", (125, 250))
    sh.glabel("LCD_BL", (125, 244), 90, "passive")
    sh.wire((125, 244), r.pin("1"))
    sh.pin_power(r, "2", G, length=2.54)

    # ---------------- USB serial ----------------
    sh.box(183, 20, 310, 125, "USB SERIAL: CH340C + auto-reset")
    ldo = sh.symbol("Regulator_Linear:XC6206PxxxMR", "U202", "XC6206P332MR", (207, 32),
                    footprint="Package_TO_SOT_SMD:SOT-23-3", lcsc="C5446", description="Torex XC6206P332MR 3.3 V 250 mA LDO")
    sh.pin_power(ldo, "VI", "VBUS", length=5.08)
    sh.pin_power(ldo, "GND", G, length=2.54)
    vo = ldo.pin("VO")
    sh.wire(vo, (233, vo[1]))
    sh.label("CH_3V3", (233, vo[1]), 0)
    c = C(sh, "C204", "1uF", (225, vo[1] + 8))
    sh.wire(c.pin("1"), (225, vo[1]))
    sh.pin_power(c, "2", G, length=2.54)
    c = C(sh, "C205", "1uF", (193, 48))
    sh.pin_power(c, "1", "VBUS", length=2.54)
    sh.pin_power(c, "2", G, length=2.54)
    ch = sh.symbol("LazerGamebox:CH340C", "U203", "CH340C", (250, 80), lcsc="C84681")
    vcc, v3 = ch.pin("VCC"), ch.pin("V3")
    sh.wire(vcc, (vcc[0], vcc[1] - 4), (v3[0], vcc[1] - 4))
    sh.wire(v3, (v3[0], vcc[1] - 4), (v3[0], vcc[1] - 8))
    sh.label("CH_3V3", (v3[0], vcc[1] - 8), 90)
    sh.pin_power(ch, "GND", G, length=2.54)
    sh.pin_label(ch, "UD+", "USB_D+", length=7.62, kind="global", shape="passive")
    sh.pin_label(ch, "UD-", "USB_D-", length=7.62, kind="global", shape="passive")
    r10, _, _ = pin_series_label(sh, ch, "TXD", "R210", "1k", "U0RXD", length=15.24, kind="local")   # CH340C is unpowered on battery
    r10.ref_pos = (r10.x, r10.y - 2.9, None); r10.val_pos = (r10.x, r10.y - 1.2, None)
    r11, _, _ = pin_series_label(sh, ch, "RXD", "R211", "1k", "U0TXD", length=17.78, kind="local", gap=10.16)
    r11.ref_pos = (r11.x, r11.y + 1.4, None); r11.val_pos = (r11.x, r11.y + 3.1, None)
    c9 = C(sh, "C209", "100nF", (v3[0] + 10, vcc[1] - 14))
    sh.wire(c9.pin("2"), (v3[0] + 10, vcc[1] - 8), (v3[0], vcc[1] - 8))
    sh.pin_power(c9, "1", G, length=2.54)
    sh.pin_label(ch, "13", "DTR", length=7.62, kind="local")
    sh.pin_label(ch, "14", "RTS", length=7.62, kind="local")
    for n in ("9", "10", "11", "12", "15"):
        sh.pin_nc(ch, n)
    # esptool auto-reset (DevKitC): DTR=1,RTS=0 -> EN low; DTR=0,RTS=1 -> IO0 low; both equal -> released
    for (qref, rref, yq, b_net, e_net, c_net) in (("Q201", "R204", 66, "DTR", "RTS", "EN"), ("Q202", "R205", 98, "RTS", "DTR", "IO0")):
        q = NPN(sh, qref, (295, yq))
        r = R(sh, rref, "10k", (283, yq), rot=90)
        sh.wire(r.pin("2"), q.pin("B"))
        sh.wire(r.pin("1"), (274, yq))
        sh.label(b_net, (274, yq), 180)
        e = q.pin("E")
        sh.wire(e, (e[0], e[1] + 3))
        sh.label(e_net, (e[0], e[1] + 3), 270)
        cc = q.pin("C")
        sh.wire(cc, (cc[0], cc[1] - 3))
        sh.label(c_net, (cc[0], cc[1] - 3), 90)
    sh.text("CH340C runs from its own 3.3 V LDO on VBUS (V3 tied to VCC): 3.3 V logic into the ESP32,\nunpowered on battery. DTR/RTS transistor pair = esptool auto-reset.", (185, 116), size=1.27)

    # ---------------- Accelerometer ----------------
    sh.box(183, 132, 310, 205, "ACCELEROMETER (LIS3DHTR, I2C 0x18)")
    a = sh.symbol("Sensor_Motion:LIS3DH", "U204", "LIS3DHTR", (225, 170),
                  footprint="Package_LGA:LGA-16_3x3mm_P0.5mm_LayoutBorder3x5y", lcsc="C15134",
                  description="ST LIS3DHTR 3-axis accelerometer, LGA-16")
    sh.pin_power(a, "VDD_IO", "+3V3", length=3.81)
    sh.pin_power(a, "VDD", "+3V3", length=3.81)
    sh.pin_power(a, "5", G, length=2.54)
    sh.pin_label(a, "SPC", "SCL", length=7.62, kind="global", shape="passive")
    sh.pin_label(a, "SDI", "SDA", length=7.62, kind="global", shape="passive")
    sdo = a.pin("SDO")
    r = R(sh, "R209", "0R", (sdo[0] - 6, sdo[1]), rot=90)   # SA0 hard to GND (address 0x18): the pin has a 20k internal pull-up, 10k would sit at 1 V
    r.ref_pos = (r.x, sdo[1] - 3.0, None); r.val_pos = (r.x, sdo[1] - 1.3, None)
    sh.wire(r.pin("2"), sdo)
    sh.pin_power(r, "1", G, length=2.54)
    sh.pin_power(a, "CS", "+3V3", length=5.08)
    sh.pin_label(a, "INT1", "ACC_INT1", length=7.62, kind="global", shape="passive")
    for n in ("2", "3", "9", "13", "15", "16"):
        sh.pin_nc(a, n)
    cap_between(sh, "C206", "100nF", 267, 165, "+3V3")
    cap_between(sh, "C207", "10uF", 280, 165, "+3V3")
    r1 = R(sh, "R206", "4.7k", (290, 160))
    r2 = R(sh, "R207", "4.7k", (300, 160))
    sh.pin_power(r1, "1", "+3V3", length=2.54)
    sh.pin_power(r2, "1", "+3V3", length=2.54)
    sh.pin_label(r1, "2", "SDA", length=3.81, kind="global", shape="passive")
    sh.pin_label(r2, "2", "SCL", length=3.81, kind="global", shape="passive")
    sh.text("SA0 (SDO) pulled low by R209 = address 0x18, CS high = I2C mode. INT1 wakes the ESP32 via the expander INT.", (185, 196), size=1.27)

    # ---------------- Expander ----------------
    sh.box(318, 20, 405, 250, "I2C GPIO EXPANDER (TCA9555, 0x20)")
    x = sh.symbol("Interface_Expansion:TCA9555PWR", "U205", "TCA9555PWR", (362, 150),
                  footprint="Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm", lcsc="C465732",
                  description="TI TCA9555PWR 16-bit I2C GPIO expander with interrupt")
    outs = [("P00", "RADIO_EN"), ("P01", "GPS_EN"), ("P02", "LCD_EN"), ("P03", "AUX_EN"), ("P04", "AMP_SD"),
            ("P05", "MUX_SEL"), ("P06", "LCD_CS"), ("P07", "LCD_RST"), ("P10", "LORA_RST"), ("P11", "CELL_PWRKEY"),
            ("P12", "BTN1"), ("P13", "BTN2"), ("P14", "BTN3"), ("P15", "RADIO_SQ"), ("P16", "ACC_INT1"), ("P17", "GPS_PPS")]
    for pin, net in outs:
        sh.pin_label(x, pin, net, length=7.62, kind="global", shape="passive")
    sh.pin_label(x, "SCL", "SCL", length=2.54, kind="global", shape="passive")
    sh.pin_label(x, "SDA", "SDA", length=2.54, kind="global", shape="passive")
    it = x.pin("1")
    sh.wire(it, (it[0] - 12.7, it[1]))
    sh.glabel("EXP_INT", (it[0] - 12.7, it[1]), 180, "passive")
    r = R(sh, "R208", "10k", (it[0] - 10, it[1] - 9))       # left of the short SCL/SDA stubs
    sh.wire(r.pin("2"), (it[0] - 10, it[1]))
    sh.pin_power(r, "1", "+3V3", length=2.54)
    for n in ("A0", "A1", "A2"):
        sh.pin_power(x, n, G, length=5.08)
    sh.pin_power(x, "VCC", "+3V3", length=3.81)
    sh.pin_power(x, "GND", G, length=2.54)
    cap_between(sh, "C208", "100nF", 330, 40, "+3V3")
    sh.text("P00-P11 outputs, P12-P17 inputs\n(100k internal pull-ups).\nINT open drain -> GPIO32,\next0 wake source.", (320, 236), size=1.27)


# ======================================================================================
# RADIO
# ======================================================================================
def gen_radio(sh):
    title(sh, "RADIO: SA818S-U 1 W UHF transceiver, 400-480 MHz", "UART2 9600 8N1 AT commands. Supply 4.6 V from the boost, RADIO_EN low = module fully off.")
    sh.box(12, 20, 260, 118, "SA818S-U MODULE")
    u = sh.symbol("LazerGamebox:SA818S-U", "U301", "SA818S-U", (110, 80), lcsc="C3001549")
    sh.pin_power(u, "VBAT", "RADIO_4V5", length=10.16, lib="LazerGamebox")
    sh.pin_label(u, "PD", "PD", length=7.62, kind="local")
    sh.pin_label(u, "PTT", "PTT_N", length=10.16, kind="local")
    sh.pin_label(u, "H/L", "HL", length=7.62, kind="local")
    pin_series_label(sh, u, "RXD", "R306", "1k", "RADIO_TX", length=27.94, gap=12.7)   # limits back-drive into the unpowered module
    sh.pin_label(u, "TXD", "RADIO_RX", length=27.94, kind="global", shape="passive")
    sh.pin_label(u, "AF_OUT", "RADIO_AF", length=12.7, kind="global", shape="passive")
    sh.pin_label(u, "MIC_IN", "RADIO_MIC", length=12.7, kind="global", shape="passive")
    sh.pin_label(u, "AUDIO_ON", "RADIO_SQ", length=12.7, kind="global", shape="passive")
    sh.pin_power(u, "9", G, length=2.54)
    sh.pin_power(u, "10", G, length=2.54)
    ant = u.pin("ANT")
    sh.wire(ant, (ant[0] + 4, ant[1]), (ant[0] + 4, 48), (170, 48))
    c1 = C(sh, "C301", "DNP", (170, 56), dnp=True)
    sh.wire(c1.pin("1"), (170, 48))
    sh.pin_power(c1, "2", G, length=2.54)
    r = R(sh, "R301", "0R", (180, 48), rot=90)
    sh.wire((170, 48), r.pin("1"))
    sh.wire(r.pin("2"), (195, 48))
    c2 = C(sh, "C302", "DNP", (195, 56), dnp=True)
    sh.wire(c2.pin("1"), (195, 48))
    sh.pin_power(c2, "2", G, length=2.54)
    j = sh.symbol("Connector:Conn_Coaxial", "J301", "SMA", (215, 48), footprint="LazerGamebox:SMA_BAT_Wireless_BWSMA-KWE-Z001",
                  lcsc="C496551", description="BAT WIRELESS BWSMA-KWE-Z001 right-angle SMA, THT")
    sh.wire((195, 48), j.pin("In"))
    sh.pin_power(j, "Ext", G, length=2.54)
    sh.text("50 ohm coplanar trace, ground stitching both sides.\nPi pads C301/R301/C302 for matching (fit 0R only).\nWhip antenna screwed on by hand after assembly.", (150, 66), size=1.27)
    cp_between(sh, "C303", "470uF", 30, 48, "RADIO_4V5")
    cap_between(sh, "C304", "10uF", 42, 48, "RADIO_4V5")
    cap_between(sh, "C305", "100nF", 54, 48, "RADIO_4V5")
    sh.text("Module current: RX 60 mA, TX high 750 mA, TX low 450 mA, 1 uA in power-down. 470 uF right at the VBAT pad.\nH/L open = 1 W; bridge JP301 for 0.5 W (the pin must never be driven high).", (14, 106), size=1.27)

    sh.box(12, 126, 260, 205, "MODULE CONTROL")
    r1 = R(sh, "R302", "10k", (40, 150))
    sh.pin_power(r1, "1", "RADIO_4V5", length=2.54, lib="LazerGamebox")
    r2 = R(sh, "R303", "22k", (40, 165))
    sh.wire(r1.pin("2"), r2.pin("1"))
    sh.pin_power(r2, "2", G, length=2.54)
    sh.wire((40, 157.5), (52, 157.5))
    sh.label("PD", (52, 157.5), 0)
    sh.text("PD held high (3.2 V) whenever the boost is on.", (20, 182), size=1.1)
    q = NMOS(sh, "Q301", (110, 165))
    d = q.pin("D")
    node = (d[0], d[1] - 4)
    sh.wire(d, node, (d[0] + 20, node[1]))
    sh.label("PTT_N", (d[0] + 20, node[1]), 0)
    r5 = R(sh, "R305", "100k", (d[0] + 10, node[1] - 7))          # PTT pull-up to the 3.2 V PD node: no internal pull-up in the module
    sh.wire(r5.pin("2"), (d[0] + 10, node[1]))
    sh.pin_label(r5, "1", "PD", length=3.81, kind="local")
    sh.pin_power(q, "S", G, length=2.54)
    g = q.pin("G")
    sh.wire(g, (g[0] - 12, g[1]))
    sh.glabel("RADIO_PTT", (g[0] - 12, g[1]), 180, "passive")
    r = R(sh, "R304", "100k", (g[0] - 6, g[1] + 7))
    sh.wire(r.pin("1"), (g[0] - 6, g[1]))
    sh.pin_power(r, "2", G, length=2.54)
    sh.text("RADIO_PTT (GPIO27) high = transmit. Open drain: no current into the module when it is off.\nR305 pulls PTT to the PD node (3.2 V, follows the boost rail): RX by default, nothing back-drives a dead module.", (75, 184), size=1.1)
    jp = sh.symbol("Jumper:SolderJumper_2_Open", "JP301", "0.5W", (205, 160), rot=0,
                   footprint="Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", in_bom=False)
    sh.pin_label(jp, "A", "HL", length=5.08, kind="local")
    sh.pin_power(jp, "B", G, length=2.54)
    sh.text("JP301 open: 1 W (default).", (190, 172), size=1.1)


# ======================================================================================
# LORA + GPS + CELLULAR (DNP)
# ======================================================================================
def gen_lora_gps(sh):
    title(sh, "LoRa 868 MHz (Ra-01SH), GNSS (ATGM336H-5N31), optional cellular (SIM7080G, all DNP)",
          "LoRa on VSPI with its own CS. GPS on UART1 behind GPS_3V3. Cellular shares UART1 through 0R links and needs 1.8 V level shifting.")
    sh.box(12, 20, 205, 130, "LoRa Ra-01SH (SX1262)")
    u = sh.symbol("LazerGamebox:Ra-01SH", "U401", "Ra-01SH", (85, 75), lcsc="C2764087")
    sh.pin_power(u, "3V3", "+3V3", length=7.62)
    sh.pin_label(u, "RESET", "LORA_RST", length=10.16, kind="global", shape="passive")
    sh.pin_label(u, "NSS", "LORA_CS", length=10.16, kind="global", shape="passive")
    sh.pin_label(u, "SCK", "SCK", length=10.16, kind="global", shape="passive")
    sh.pin_label(u, "MOSI", "MOSI", length=10.16, kind="global", shape="passive")
    sh.pin_label(u, "MISO", "MISO", length=10.16, kind="global", shape="passive")
    sh.pin_label(u, "DIO1", "LORA_DIO1", length=10.16, kind="global", shape="passive")
    sh.pin_label(u, "BUSY", "LORA_BUSY", length=10.16, kind="global", shape="passive")
    for n in ("DIO2", "DIO3", "TXEN", "RXEN"):
        sh.pin_nc(u, n)
    for n in ("2", "9", "16"):
        sh.pin_power(u, n, G, length=2.54)
    ant = u.pin("ANT")
    sh.wire(ant, (ant[0] + 4, ant[1]), (ant[0] + 4, 40), (140, 40))
    c1 = C(sh, "C401", "DNP", (140, 48), dnp=True)
    sh.wire(c1.pin("1"), (140, 40))
    sh.pin_power(c1, "2", G, length=2.54)
    r = R(sh, "R401", "0R", (150, 40), rot=90)
    sh.wire((140, 40), r.pin("1"))
    sh.wire(r.pin("2"), (165, 40))
    c2 = C(sh, "C402", "DNP", (165, 48), dnp=True)
    sh.wire(c2.pin("1"), (165, 40))
    sh.pin_power(c2, "2", G, length=2.54)
    a = sh.symbol("Device:Antenna", "ANT401", "868 spring", (180, 30), footprint=f"{LIB}:ANT-TH_BW868SNX20-5Z6",
                  lcsc="C496555", description="BAT WIRELESS BW868SNX20-5Z6 spring antenna 868 MHz, THT pin")
    sh.wire(a.pin("A"), (180, 40), (165, 40))
    cap_between(sh, "C403", "10uF", 30, 45, "+3V3")
    cap_between(sh, "C404", "100nF", 42, 45, "+3V3")
    sh.text("RF switch is driven by DIO2 inside the module: setDio2AsRfSwitch(true). TXEN/RXEN pads unused.\nSX1262 sleep 1 uA, always powered from +3V3. 50 ohm trace to the spring antenna, keep 15 mm from the UHF PA.",
            (14, 116), size=1.27)

    sh.box(12, 138, 205, 250, "GNSS ATGM336H-5N31 (UART1, 1PPS)")
    g = sh.symbol("LazerGamebox:ATGM336H-5N31", "U402", "ATGM336H-5N31", (85, 195), lcsc="C90770")
    sh.pin_power(g, "VCC", "GPS_3V3", length=10.16, lib="LazerGamebox")
    sh.pin_power(g, "VBAT", "+3V3", length=17.78)
    sh.pin_label(g, "ON/OFF", "GPS_ON", length=7.62, kind="local")
    sh.pin_nc(g, "9")
    pin_series_label(sh, g, "RXD", "R411", "1k", "GPS_TX", length=17.78)     # VCC domain is switched off most of the time
    sh.pin_label(g, "TXD", "GPS_RX", length=17.78, kind="global", shape="passive")
    sh.pin_label(g, "1PPS", "GPS_PPS", length=10.16, kind="global", shape="passive")
    sh.pin_nc(g, "16"); sh.pin_nc(g, "17"); sh.pin_nc(g, "14")
    for n in ("1", "10", "12"):
        sh.pin_power(g, n, G, length=2.54)
    rf = g.pin("RF_IN")
    sh.wire(rf, (rf[0] + 4, rf[1]))
    c = C(sh, "C405", "100pF", (rf[0] + 8, rf[1]), rot=90)
    # pi matching pads for the patch (fit R412 0R only; C412/C413 DNP until the antenna is tuned on the real board)
    sh.wire(c.pin("2"), (rf[0] + 18, rf[1]))
    c12 = C(sh, "C412", "100pF", (rf[0] + 18, rf[1] + 8), dnp=True)
    sh.wire(c12.pin("1"), (rf[0] + 18, rf[1]))
    sh.pin_power(c12, "2", G, length=2.54)
    r12 = R(sh, "R412", "0R", (rf[0] + 24, rf[1]), rot=90)
    sh.wire((rf[0] + 18, rf[1]), r12.pin("1"))
    sh.wire(r12.pin("2"), (rf[0] + 30, rf[1]), (140, rf[1]))
    c13 = C(sh, "C413", "100pF", (rf[0] + 30, rf[1] + 8), dnp=True)
    sh.wire(c13.pin("1"), (rf[0] + 30, rf[1]))
    sh.pin_power(c13, "2", G, length=2.54)
    a = sh.symbol("Device:Antenna", "ANT402", "GPS patch 18x18", (140, 178), footprint=f"{LIB}:ANT-TH_L18.0-W18.0_C9900026472",
                  lcsc="C784395", description="BAT WIRELESS BWGNSCNX18-18W4 ceramic patch antenna 1575 MHz, THT pin")
    sh.wire(a.pin("A"), (140, rf[1]))
    cap_between(sh, "C406", "10uF", 30, 160, "GPS_3V3")
    cap_between(sh, "C407", "100nF", 42, 160, "GPS_3V3")
    r = R(sh, "R410", "10k", (60, 160))
    sh.pin_power(r, "1", "GPS_3V3", length=2.54, lib="LazerGamebox")
    sh.pin_label(r, "2", "GPS_ON", length=3.81, kind="local")
    sh.text("Passive patch antenna on a solid ground pour (40 x 40 mm), 15 mm or more from the UHF PA and the LoRa antenna.\nVBAT backup pin on +3V3 (10 uA) keeps ephemeris for hot starts while GPS_3V3 is switched off. ON/OFF pulled up by R410.",
            (14, 236), size=1.27)

    sh.box(213, 20, 405, 250, "CELLULAR OPTION: SIM7080G Cat-M / NB-IoT + nano-SIM + antenna (ALL DNP)")
    m = sh.symbol("LazerGamebox:SIM7080G", "U403", "SIM7080G", (300, 92), lcsc="C2943992", dnp=True)
    vb1, vb2 = m.pin("34"), m.pin("35")
    sh.wire(vb1, (vb1[0] - 6, vb1[1]), (vb1[0] - 6, vb2[1]), vb2)
    sh.wire((vb1[0] - 6, vb1[1]), (vb1[0] - 14, vb1[1]))
    sh.power("VBAT", (vb1[0] - 14, vb1[1]), lib="LazerGamebox")
    sh.pin_label(m, "VDD_EXT", "VDD_EXT", length=5.08, kind="local")
    sh.pin_label(m, "UART1_TXD", "CELL_TXD", length=7.62, kind="local")
    sh.pin_label(m, "UART1_RXD", "CELL_RXD", length=7.62, kind="local")
    for n in ("NETLIGHT", "STATUS", "ADC", "UART1_RTS", "UART1_CTS", "UART1_DCD", "UART1_DTR", "UART1_RI",
              "GNSS_ANT", "ANT_CONTROL1", "ANT_CONTROL0", "USB_VBUS", "USB_DP", "USB_DM"):
        sh.pin_nc(m, n)
    sh.pin_power(m, "8", G, length=2.54)
    for n, lbl in (("SIM_VDD", "SIM_VDD"), ("SIM_DATA", "SIM_DATA"), ("SIM_CLK", "SIM_CLK"), ("SIM_RST", "SIM_RST")):
        sh.pin_label(m, n, lbl, length=7.62, kind="local")
    rfa = m.pin("RF_ANT")
    sh.wire(rfa, (rfa[0] + 5, rfa[1]))
    r = R(sh, "R402", "0R", (rfa[0] + 9, rfa[1]), rot=90, dnp=True)
    sh.wire(r.pin("2"), (rfa[0] + 24, rfa[1]))
    a = sh.symbol("Device:Antenna", "ANT403", "GSM spring", (rfa[0] + 24, rfa[1] - 10), footprint=f"{LIB}:ANT-TH_1P",
                  lcsc="C381192", dnp=True, description="DreamLNK T10 GSM 900/1800 spring antenna, THT pin")
    sh.wire(a.pin("A"), (rfa[0] + 24, rfa[1]))
    pk = m.pin("PWRKEY")
    q = NPN(sh, "Q401", (252, 110), dnp=True)
    cc = q.pin("C")
    sh.wire(cc, (cc[0], pk[1]), pk)
    r = R(sh, "R403", "1k", (244, 110), rot=90, dnp=True)
    sh.wire(r.pin("2"), q.pin("B"))
    sh.wire(r.pin("1"), (234, 110))
    sh.glabel("CELL_PWRKEY", (234, 110), 180, "passive")
    sh.pin_power(q, "E", G, length=2.54)
    cap_between(sh, "C408", "100uF", 230, 55, "VBAT", dnp=True)
    cap_between(sh, "C409", "100uF", 243, 55, "VBAT", dnp=True)
    cap_between(sh, "C410", "100nF", 256, 55, "VBAT", dnp=True)
    def shifter(cy, qref, r_hi, r_lo, r_link, esp_net, cell_net):
        n = NMOS(sh, qref, (300, cy), rot=90, dnp=True)      # D left (3V3 side), S right (1V8 side), G bottom
        d, s, gg = n.pin("D"), n.pin("S"), n.pin("G")
        sh.wire(d, (283, d[1]))
        rh = R(sh, r_hi, "10k", (283, d[1] - 8), dnp=True)
        sh.wire(rh.pin("2"), (283, d[1]))
        sh.pin_power(rh, "1", "+3V3", length=2.54)
        rl = R(sh, r_link, "0R", (272, d[1]), rot=90, dnp=True)
        sh.wire(rl.pin("2"), (283, d[1]))
        sh.wire(rl.pin("1"), (260, d[1]))
        sh.glabel(esp_net, (260, d[1]), 180, "passive")
        sh.wire(s, (322, s[1]))
        rr = R(sh, r_lo, "10k", (317, s[1] - 8), dnp=True)
        sh.wire(rr.pin("2"), (317, s[1]))
        sh.wire(rr.pin("1"), (317, s[1] - 14))
        sh.label("VDD_EXT", (317, s[1] - 14), 90)
        sh.label(cell_net, (322, s[1]), 0)
        sh.wire(gg, (gg[0], gg[1] + 4))
        sh.label("VDD_EXT", (gg[0], gg[1] + 4), 270)
    shifter(160, "Q402", "R404", "R405", "R406", "GPS_RX", "CELL_TXD")
    shifter(190, "Q403", "R407", "R408", "R409", "GPS_TX", "CELL_RXD")
    j = sh.symbol("LazerGamebox:SIM_Card", "J401", "nano-SIM", (375, 190), footprint=f"{LIB}:SIM-SMD_NANO-SIM-XG6P-H1.35",
                  lcsc="C7529386", dnp=True, description="SHOU HAN NANO SIM XG6P H1.35 push-pull socket")
    sh.pin_label(j, "VCC", "SIM_VDD", length=5.08, kind="local")
    sh.pin_label(j, "RST", "SIM_RST", length=5.08, kind="local")
    sh.pin_label(j, "CLK", "SIM_CLK", length=5.08, kind="local")
    sh.pin_label(j, "I/O", "SIM_DATA", length=5.08, kind="local")
    sh.pin_power(j, "GND", G, length=5.08)
    sh.pin_nc(j, "VPP")
    c = C(sh, "C411", "100nF", (352, 218), dnp=True)
    sh.wire(c.pin("1"), (352, 212))
    sh.label("SIM_VDD", (352, 212), 90)
    sh.pin_power(c, "2", G, length=2.54)
    sh.text("Fit EITHER the GNSS module OR the cellular module (SIM7080G has its own GNSS): both share UART1 via R406/R409.\nSIM7080G IO is 1.8 V (VDD_EXT): Q402/Q403 are BSS138-style bidirectional level shifters.\nPWRKEY pulsed low 1 s by CELL_PWRKEY through Q401. No ESD array on the SIM lines: socket sits inside the enclosure.",
            (215, 232), size=1.27)


# ======================================================================================
# AUDIO
# ======================================================================================
def gen_audio(sh):
    title(sh, "AUDIO: DAC or radio audio -> class-D amp -> speaker; DAC -> radio mic; radio audio -> ADC for DTMF",
          "NS4150B gain = 2 x 240k / 220k = 2.2. MUX_SEL low = ESP32 DAC to the speaker, high = radio receive audio to the speaker.")
    sh.box(12, 20, 150, 105, "SOURCE SELECT (TS5A3159)")
    u = sh.symbol("LazerGamebox:TS5A3159", "U501", "TS5A3159", (75, 62), lcsc="C46388")
    r12, _, _ = pin_series_label(sh, u, "NO", "R512", "1k", "RADIO_AF", length=20.32)    # protects the switch clamp diodes, like R501
    r12.ref_pos = (r12.x, r12.y - 2.9, None); r12.val_pos = (r12.x, r12.y - 1.2, None)
    nc = u.pin("NC")
    r = R(sh, "R501", "1k", (nc[0] - 14, nc[1]), rot=90)
    r.ref_pos = (r.x, r.y - 2.9, None); r.val_pos = (r.x, r.y - 1.2, None)
    sh.wire(r.pin("2"), nc)
    sh.wire(r.pin("1"), (nc[0] - 20.32, nc[1]))
    sh.glabel("DAC1", (nc[0] - 20.32, nc[1]), 180, "passive")
    sh.pin_label(u, "IN", "MUX_SEL", length=20.32, kind="global", shape="passive")
    sh.pin_power(u, "V+", "+3V3", length=3.81)
    sh.pin_power(u, "GND", G, length=2.54)
    com = u.pin("COM")
    c = C(sh, "C501", "100nF", (com[0] + 8, com[1]), rot=90)
    sh.wire(com, c.pin("1"))
    sh.wire(c.pin("2"), (120, com[1]))
    sh.label("AMP_IN", (120, com[1]), 0)
    cap_between(sh, "C502", "100nF", 132, 40, "+3V3")
    sh.text("DAC1 is 0-3.3 V unipolar; R501 limits current into the switch.\nAC coupling after the switch (C501).", (14, 92), size=1.27)

    sh.box(158, 20, 405, 105, "CLASS-D AMPLIFIER (NS4150B) + 30 mm SPEAKER")
    a = sh.symbol("LazerGamebox:NS4150B", "U502", "NS4150B", (240, 62), lcsc="C189961")
    inp = a.pin("INP")
    r = R(sh, "R502", "220k", (206, inp[1]), rot=90)
    sh.wire(r.pin("2"), inp)
    sh.wire(r.pin("1"), (192, inp[1]))
    sh.label("AMP_IN", (192, inp[1]), 180)
    inn = a.pin("INN")
    sh.wire(inn, (222, inn[1]), (222, inn[1] + 8), (218, inn[1] + 8))
    r = R(sh, "R503", "220k", (214, inn[1] + 8), rot=90)
    c = C(sh, "C503", "100nF", (202, inn[1] + 8), rot=90)
    sh.wire(r.pin("1"), c.pin("2"))
    sh.pin_power(c, "1", G, length=2.54)
    sh.pin_label(a, "BYPASS", "AMP_BYP", length=22.86, kind="local")
    c = C(sh, "C504", "1uF", (178, 84))
    sh.wire(c.pin("1"), (178, 78))
    sh.label("AMP_BYP", (178, 78), 90)
    sh.pin_power(c, "2", G, length=2.54)
    ctrl = a.pin("CTRL")
    node = (ctrl[0] - 5, ctrl[1])
    sh.wire(ctrl, node)
    r11 = R(sh, "R511", "10k", (node[0], node[1] - 7))              # CTRL abs max is VDD + 0.3 V and VBAT_SW is switched
    r11.ref_pos = (node[0] - 1.6, node[1] - 7.8, "right"); r11.val_pos = (node[0] - 1.6, node[1] - 5.8, "right")
    sh.wire(r11.pin("2"), node)
    sh.wire(r11.pin("1"), (node[0], node[1] - 16))
    sh.glabel("AMP_SD", (node[0], node[1] - 16), 90, "passive")
    r4 = R(sh, "R504", "100k", (node[0] - 8, node[1]), rot=90)       # amp stays off until firmware drives AMP_SD high
    r4.ref_pos = (node[0] - 8, node[1] - 2.9, None); r4.val_pos = (node[0] - 8, node[1] - 1.2, None)
    sh.wire(r4.pin("2"), node)
    sh.pin_power(r4, "1", G, length=2.54)
    sh.pin_power(a, "VCC", "VBAT_SW", length=3.81, lib="LazerGamebox")
    sh.pin_power(a, "GND", G, length=2.54)
    vop, von = a.pin("VoP"), a.pin("VoN")
    spk = sh.symbol("Device:Speaker", "LS501", "FS-3013 30mm 8R", (290, vop[1]), footprint=f"{LIB}:BEEP-TH_BD30.0-P15.00-D1.0",
                    lcsc="C482323", description="FUET FS-3013 30 mm 8 ohm 1 W speaker, THT")
    sh.wire(vop, spk.pin("1"))
    sh.wire(von, spk.pin("2"))
    cp_between(sh, "C505", "470uF", 322, 45, "VBAT_SW")
    cap_between(sh, "C506", "10uF", 335, 45, "VBAT_SW")
    cap_between(sh, "C507", "100nF", 348, 45, "VBAT_SW")
    sh.text("R504 keeps the amp off until firmware drives AMP_SD high; R511 limits the current into CTRL while VBAT_SW is off.\nFirmware: AUX_EN high a few ms before AMP_SD high, AMP_SD low before AUX_EN low.", (250, 76), size=1.1)
    sh.text("Filter-free BTL output: keep speaker traces short and away from the radio. VCC on VBAT_SW with 470 uF bulk.\nMax output about 1 W into 8 ohm at 3.7 V.",
            (160, 97), size=1.27)

    sh.box(12, 113, 150, 190, "DAC -> RADIO MIC_IN (100:1)")
    r1 = R(sh, "R505", "100k", (45, 145), rot=90)
    sh.glabel("DAC1", (30, 145), 180, "passive")
    sh.wire((30, 145), r1.pin("1"))
    sh.wire(r1.pin("2"), (62, 145))
    r2 = R(sh, "R506", "1k", (62, 153))
    sh.wire((62, 145), r2.pin("1"))
    sh.pin_power(r2, "2", G, length=2.54)
    c = C(sh, "C508", "1uF", (78, 145), rot=90)
    sh.wire((62, 145), c.pin("1"))
    sh.wire(c.pin("2"), (100, 145))
    sh.glabel("RADIO_MIC", (100, 145), 0, "passive")
    sh.text("3.3 Vpp DAC -> 33 mVpp at MIC_IN, AC coupled.\nUsed for DTMF / tone signalling over the radio.", (14, 177), size=1.27)

    sh.box(158, 113, 405, 190, "RADIO AF_OUT -> ADC1 (software Goertzel DTMF decoder)")
    y = 145
    sh.glabel("RADIO_AF", (175, y), 180, "passive")
    r1 = R(sh, "R507", "47k", (188, y), rot=90)
    sh.wire((175, y), r1.pin("1"))
    c1 = C(sh, "C509", "1uF", (204, y), rot=90)
    sh.wire(r1.pin("2"), c1.pin("1"))
    sh.wire(c1.pin("2"), (225, y))
    ru = R(sh, "R508", "100k", (225, y - 9))
    sh.wire(ru.pin("2"), (225, y))
    sh.pin_power(ru, "1", "+3V3", length=2.54)
    rd = R(sh, "R509", "100k", (225, y + 9))
    sh.wire(rd.pin("1"), (225, y))
    sh.pin_power(rd, "2", G, length=2.54)
    r2 = R(sh, "R510", "10k", (245, y), rot=90)
    sh.wire((225, y), r2.pin("1"))
    sh.wire(r2.pin("2"), (265, y))
    c2 = C(sh, "C510", "1nF", (265, y + 9))
    sh.wire(c2.pin("1"), (265, y))
    sh.pin_power(c2, "2", G, length=2.54)
    sh.wire((265, y), (285, y))
    sh.glabel("ADC_AUDIO", (285, y), 0, "passive")
    sh.text("AF_OUT is 700 mV / 200 ohm: R507 with the 50k bias gives about 0.35 Vrms swing around 1.65 V at GPIO36.\nR510/C510 = 16 kHz anti-alias for a 40 kHz ADC sample rate.", (160, 177), size=1.27)


# ======================================================================================
# IO
# ======================================================================================
def gen_io(sh):
    title(sh, "IO: 2.0in display on ZIF, pot, buttons, RGB LEDs, IR transmit / receive",
          "Front side of the board: display, buttons, pot, LEDs, IR. Display, pot and IR receiver ride on LCD_3V3.")
    sh.box(12, 20, 192, 125, "DISPLAY: HS20HS072RX 2.0in IPS 320x240, ST7789V2, 12-pin 0.5 mm ZIF")
    j = sh.symbol("LazerGamebox:LCD_HS20HS072RX_FPC12", "J601", "ZIF 12P 0.5mm", (95, 70), lcsc="C5362174",
                  description="HanElectricity 05A20H12P dual-contact ZIF for HS20HS072RX (C5329582) panel")
    sh.pin_power(j, "1", G, length=3.81)
    sh.pin_power(j, "12", G, length=3.81)
    sh.pin_label(j, "CS", "LCD_CS", length=10.16, kind="global", shape="passive")
    sh.pin_label(j, "RS", "LCD_DC", length=10.16, kind="global", shape="passive")
    sh.pin_label(j, "SCL", "SCK", length=10.16, kind="global", shape="passive")
    sh.pin_label(j, "SDA", "MOSI", length=10.16, kind="global", shape="passive")
    sh.pin_label(j, "RST", "LCD_RST", length=10.16, kind="global", shape="passive")
    sh.pin_nc(j, "7")
    iov, vcc9 = j.pin("IOVCC"), j.pin("VCC")
    sh.wire(iov, (iov[0] - 5, iov[1]), (vcc9[0] - 5, vcc9[1]), vcc9)      # one rail symbol for both supply pins
    sh.power("LCD_3V3", (iov[0] - 5, iov[1]), lib="LazerGamebox")
    la = j.pin("LEDA")
    r = R(sh, "R601", "20R", (la[0] - 11, la[1]), rot=90, pkg="0805")
    sh.wire(la, r.pin("2"))
    sh.wire(r.pin("1"), (la[0] - 20, la[1]))
    sh.power("VBAT_SW", (la[0] - 20, la[1]), lib="LazerGamebox")
    lk = j.pin("LEDK")
    q = NPN(sh, "Q601", (lk[0] - 12.54, lk[1] + 14))
    cc = q.pin("C")
    sh.wire(lk, (cc[0], lk[1]), cc)
    sh.pin_power(q, "E", G, length=2.54)
    r = R(sh, "R602", "1k", (cc[0] - 12, q.pin("B")[1]), rot=90)
    sh.wire(r.pin("2"), q.pin("B"))
    sh.wire(r.pin("1"), (cc[0] - 22, q.pin("B")[1]))
    sh.glabel("LCD_BL", (cc[0] - 22, q.pin("B")[1]), 180, "passive")
    cap_between(sh, "C601", "10uF", 140, 40, "LCD_3V3")
    cap_between(sh, "C602", "100nF", 153, 40, "LCD_3V3")
    pot = sh.symbol("Device:R_Potentiometer", "RV601", "10k lin", (140, 82), footprint=f"{LIB}:Potentiometer_Alps_RK09K1130A6S_LCSC",
                    lcsc="C209770", description="Alps RK09K1130A6S 10k linear, 15 mm flat shaft, THT")
    sh.pin_power(pot, "1", "LCD_3V3", length=2.54, lib="LazerGamebox")
    sh.pin_power(pot, "3", G, length=2.54)
    w = pot.pin("2")
    r = R(sh, "R603", "10k", (w[0] + 16, w[1]), rot=90)
    sh.wire(w, r.pin("1"))
    sh.wire(r.pin("2"), (w[0] + 26, w[1]))
    c = C(sh, "C603", "100nF", (w[0] + 26, w[1] + 8))
    sh.wire(c.pin("1"), (w[0] + 26, w[1]))
    sh.pin_power(c, "2", G, length=2.54)
    sh.wire((w[0] + 26, w[1]), (w[0] + 34, w[1]))
    sh.glabel("ADC_POT", (w[0] + 34, w[1]), 0, "passive")
    sh.text("Backlight: 3 white LEDs in parallel from VBAT_SW via 20 R (25-60 mA over the cell range), PWM on LCD_BL.\nPanel logic 3.3 V. Pot wiper -> GPIO34 (ADC1_CH6).", (14, 112), size=1.27)

    sh.box(200, 20, 268, 125, "USER BUTTONS (to expander)")
    for i, y in enumerate((45, 70, 95), start=1):
        sw = sh.symbol("Switch:SW_Push", f"SW60{i}", f"BTN{i}", (220, y), footprint=FP_TACT,
                       lcsc="C318884", description="XKB TS-1187A-B-A-B 5.1 mm tact switch")
        sh.pin_power(sw, "1", G, length=2.54)
        p2 = sw.pin("2")
        sh.wire(p2, (247, y))
        sh.glabel(f"BTN{i}", (247, y), 0, "passive")
        c = C(sh, f"C60{i + 3}", "100nF", (239, y + 8))
        sh.wire(c.pin("1"), (239, y))
        sh.pin_power(c, "2", G, length=2.54)
    sh.text("Expander pull-ups (100k),\n100 nF debounce.", (203, 112), size=1.27)

    sh.box(276, 20, 405, 125, "RGB LEDs (WS2812B-2020 x3)")
    r = R(sh, "R604", "330R", (300, 60), rot=90)
    sh.glabel("LED_DATA", (290, 60), 180, "passive")
    sh.wire((290, 60), r.pin("1"))
    prev = r.pin("2")
    for i, x in enumerate((311, 346, 381), start=1):
        d = sh.symbol("LED:WS2812B-2020", f"D60{i}", "WS2812B-2020", (x, 60), footprint="LazerGamebox:LED_WS2812B-2020_PLCC4_2.0x2.0mm",
                      lcsc="C52917434", description="Worldsemi WS2812B-2020-V6 addressable RGB LED")
        sh.wire(prev, d.pin("DIN"))
        prev = d.pin("DOUT")
        sh.pin_power(d, "VDD", "VBAT_SW", length=3.81, lib="LazerGamebox")
        sh.pin_power(d, "VSS", G, length=2.54)
        cap_between(sh, f"C60{i + 6}", "100nF", x, 95, "VBAT_SW")
    sh.noconn(prev)
    sh.text("LEDs run from VBAT_SW (3.0-4.2 V); data is 3.3 V, fine for WS2812B-V6.", (278, 112), size=1.27)

    sh.box(12, 133, 268, 215, "IR: 38 kHz RECEIVER and 940 nm HIGH-POWER EMITTER (laser-tag style)")
    ir = sh.symbol("LazerGamebox:IRM-H638T", "U601", "IRM-H638T", (70, 180), footprint="LazerGamebox:Everlight_IRM-H6xxT",
                   lcsc="C91447")
    vcc = ir.pin("VCC")
    sh.wire(vcc, (vcc[0], vcc[1] - 4))
    r = R(sh, "R605", "100R", (vcc[0], vcc[1] - 7.81))
    sh.pin_power(r, "1", "LCD_3V3", length=2.54, lib="LazerGamebox")
    c = C(sh, "C610", "4.7uF", (vcc[0] + 12, vcc[1] + 2))
    sh.wire((vcc[0], vcc[1] - 4), (vcc[0] + 12, vcc[1] - 4), c.pin("1"))
    sh.pin_power(c, "2", G, length=2.54)
    sh.wire((vcc[0] + 12, vcc[1] - 4), (vcc[0] + 20, vcc[1] - 4))
    sh.flag((vcc[0] + 20, vcc[1] - 4))
    out = ir.pin("OUT")
    sh.wire(out, (out[0] - 12, out[1]))
    sh.glabel("IR_RX", (out[0] - 12, out[1]), 180, "passive")
    r = R(sh, "R606", "10k", (out[0] - 7, out[1] - 7))
    sh.wire(r.pin("2"), (out[0] - 7, out[1]))
    sh.pin_power(r, "1", "LCD_3V3", length=2.54, lib="LazerGamebox")
    sh.pin_power(ir, "1", G, length=2.54)
    sh.pin_power(ir, "2", G, length=2.54)
    x = 190
    r = R(sh, "R607", "12R", (x, 150), pkg="1206")      # 190 mA peak at 4.2 V: VSMY2940G IFM is 200 mA at 50 % duty
    sh.pin_power(r, "1", "VBAT_SW", length=2.54, lib="LazerGamebox")
    d = sh.symbol("Device:LED", "D604", "VSMY2940G", (x, 162), rot=90, footprint=f"{LIB}:LED-SMD_L2.3-W2.3-RD_VSMY2940G",
                  lcsc="C499547", description="Vishay VSMY2940G 940 nm IR emitter, 75 mW/sr at 100 mA")
    sh.wire(r.pin("2"), d.pin("A"))
    q = NPN(sh, "Q602", (x - 2.54, 176))
    sh.wire(d.pin("K"), q.pin("C"))
    sh.pin_power(q, "E", G, length=2.54)
    rb = R(sh, "R608", "330R", (x - 15, q.pin("B")[1]), rot=90)   # 7 mA base drive so the SS8050 saturates at 190 mA
    sh.wire(rb.pin("2"), q.pin("B"))
    sh.wire(rb.pin("1"), (x - 26, q.pin("B")[1]))
    sh.glabel("IR_TX", (x - 26, q.pin("B")[1]), 180, "passive")
    sh.text("Receiver on LCD_3V3 (1.2 mA), output pulled up to 3.3 V -> GPIO35 (RMT). Never power it from VBAT_SW: its output would exceed 3.3 V.\nEmitter: about 150-230 mA peak at 38 kHz / 50 % duty from VBAT_SW through 12 R (1206). Keep bursts under 100 ms.",
            (14, 203), size=1.27)


# ======================================================================================
# ROOT
# ======================================================================================
def gen_root(root, sheets):
    root.text("LazerGamebox: outdoor game box, ESP32 + UHF radio + LoRa + GNSS", (14, 13.5), size=3.0, bold=True)
    root.text("2-layer 70 x 100 mm, JLCPCB assembled. Hierarchical sheets below; nets cross sheets as global labels, rails as power symbols.",
              (14, 18.5), size=1.5)
    descr = {
        "power": "USB-C, TP4056 charger, DW01A/FS8205A protection,\nload sharing, TPS62A02 3V3 buck, TPS61023 radio\nboost, P-FET load switches, VBAT sense",
        "mcu": "ESP32-WROOM-32E-N16, CH340C USB serial with\nauto-reset, LIS3DHTR accelerometer,\nTCA9555 I2C GPIO expander",
        "radio": "SA818S-U 1 W UHF module, PTT driver,\nPD divider, H/L jumper, pi pads, SMA",
        "lora_gps": "Ra-01SH LoRa 868 MHz, ATGM336H GNSS + patch,\nSIM7080G cellular option (DNP) with SIM and\n1.8 V level shifters",
        "audio": "TS5A3159 source mux, NS4150B class-D + speaker,\nDAC to radio mic divider, radio AF to ADC bias",
        "io": "2.0in ST7789 display on 12p ZIF + backlight,\n10k pot, 3 buttons, 3x WS2812B-2020,\nIR receiver + high-power IR emitter",
    }
    pos = {"power": (15, 30), "mcu": (150, 30), "radio": (285, 30), "lora_gps": (15, 110), "audio": (150, 110), "io": (285, 110)}
    for i, (name, sh) in enumerate(sheets.items(), start=2):
        x, y = pos[name]
        s = root.subsheet(name, sh.filename, (x, y), (120, 60))
        s["page"] = i
        sh.path_uuid = s["uuid"]
        root.text(descr[name], (x + 2, y + 4), size=1.5)
    root.box(15, 185, 405, 250, "MECHANICAL: 4x M2.5 mounting holes, 3 fiducials")
    for i in range(4):
        root.symbol("Mechanical:MountingHole", f"H{i + 1}", "M2.5", (40 + i * 25, 215), footprint="MountingHole:MountingHole_2.7mm_M2.5", in_bom=False)
    for i in range(3):
        root.symbol("Mechanical:Fiducial", f"FID{i + 1}", "Fiducial", (170 + i * 25, 215), footprint="Fiducial:Fiducial_1mm_Mask2mm", in_bom=False)
    root.text("Cross-sheet signal list: see docs/pinmap.md. Power rails: VBUS, VBAT, VSYS, +3V3, RADIO_4V5, VBAT_SW, GPS_3V3, LCD_3V3, GND.",
              (18, 240), size=1.4)


def write_project(out_dir):
    """Project file. An existing .kicad_pro (KiCad adds many settings on save) is kept and only the
    parts the generator owns are enforced. The default net class must carry wire_width, bus_width and
    line_style: the GUI derives wire pen width and junction size from it, and without them every
    generated wire and junction dot resolves to zero size and the load-time cleanup merges wires
    across junctions (found 2026-09-29, KiCad 10.0.3)."""
    path = os.path.join(out_dir, f"{PROJECT}.kicad_pro")
    pro = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                pro = json.load(f)
        except Exception:
            pro = {}
    default_class = {"bus_width": 12, "clearance": 0.15, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
                     "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
                     "name": "Default", "pcb_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647,
                     "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": 0.25, "tuning_profile": "",
                     "via_diameter": 0.6, "via_drill": 0.3, "wire_width": 6}
    ns = pro.setdefault("net_settings", {"meta": {"version": 4}})
    classes = ns.setdefault("classes", [])
    for c in classes:
        if c.get("name") == "Default":
            for k, v in default_class.items():
                c.setdefault(k, v)
            break
    else:
        classes.insert(0, default_class)
    drawing = pro.setdefault("schematic", {}).setdefault("drawing", {})
    for k, v in {"default_line_thickness": 6.0, "default_text_size": 50.0, "junction_size_choice": 3,
                 "label_size_ratio": 0.375, "pin_symbol_size": 25.0}.items():
        drawing.setdefault(k, v)
    pro.setdefault("board", {"design_settings": {"defaults": {}, "rules": {}}, "layer_presets": [], "viewports": []})
    pro.setdefault("boards", []); pro.setdefault("cvpcb", {"equivalence_files": []})
    pro.setdefault("erc", {"erc_exclusions": [], "meta": {"version": 0}, "pin_map": [], "rule_severities": {}})
    pro.setdefault("libraries", {"pinned_footprint_libs": [], "pinned_symbol_libs": []})
    pro.setdefault("meta", {"filename": f"{PROJECT}.kicad_pro", "version": 3})
    pro.setdefault("pcbnew", {"last_paths": {}, "page_layout_descr_file": ""})
    pro["schematic"].setdefault("legacy_lib_dir", ""); pro["schematic"].setdefault("legacy_lib_list", [])
    pro["schematic"].setdefault("meta", {"version": 1})
    pro.setdefault("sheets", []); pro.setdefault("text_variables", {})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(pro, f, indent=2)
    with open(os.path.join(out_dir, "sym-lib-table"), "w", encoding="utf-8", newline="\n") as f:
        f.write('(sym_lib_table\n  (version 7)\n'
                f'  (lib (name "LazerGamebox")(type "KiCad")(uri "${{KIPRJMOD}}/LazerGamebox.kicad_sym")(options "")(descr "Project symbols"))\n'
                f'  (lib (name "LazerGamebox_lcsc")(type "KiCad")(uri "${{KIPRJMOD}}/lib/LazerGamebox_lcsc.kicad_sym")(options "")(descr "EasyEDA imports"))\n)\n')
    with open(os.path.join(out_dir, "fp-lib-table"), "w", encoding="utf-8", newline="\n") as f:
        f.write("(fp_lib_table\n  (version 7)\n"
                '  (lib (name "LazerGamebox_lcsc")(type "KiCad")(uri "${KIPRJMOD}/lib/LazerGamebox_lcsc.pretty")(options "")(descr "EasyEDA/JLC footprints"))\n'
                '  (lib (name "LazerGamebox")(type "KiCad")(uri "${KIPRJMOD}/lib/LazerGamebox.pretty")(options "")(descr "KiCad footprints with LCSC STEP models"))\n'
                ")\n")


def main():
    out = PRJ_DIR
    root = Sheet(PROJECT, f"{PROJECT}.kicad_sch", title="LazerGamebox", extra_dirs=EXTRA, paper="A3")
    names = ["power", "mcu", "radio", "lora_gps", "audio", "io"]
    sheets = {n: Sheet(PROJECT, f"{n}.kicad_sch", root_uuid=root.uuid, sheet_path_uuid="x", title=n, extra_dirs=EXTRA, paper="A3")
              for n in names}
    gen_root(root, sheets)
    gen_power(sheets["power"]); gen_mcu(sheets["mcu"]); gen_radio(sheets["radio"])
    gen_lora_gps(sheets["lora_gps"]); gen_audio(sheets["audio"]); gen_io(sheets["io"])
    problems = []
    refs = {}
    for sh in [root] + list(sheets.values()):
        problems += sh.lint_layout()
        for ps in sh.symbols:
            if ps.ref.startswith("#"):
                continue
            if ps.ref in refs and refs[ps.ref] != (ps.lib, ps.name, ps.unit):
                raise SystemExit(f"duplicate reference {ps.ref} in {sh.filename} and {refs[ps.ref][3]}")
            refs.setdefault(ps.ref, (ps.lib, ps.name, ps.unit, sh.filename))
    for p in problems:
        print("LAYOUT:", p)
    root.write(out)
    for sh in sheets.values():
        sh.write(out)
    write_project(out)
    print("written to", out, f"({len(problems)} layout problems)")
    return len(problems)


if __name__ == "__main__":
    main()

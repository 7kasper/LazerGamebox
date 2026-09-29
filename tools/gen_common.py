"""Helpers shared by the sheet generators: part tables (value -> LCSC, footprint) and
placement idioms (decoupling caps, pull-ups, series parts) that keep the sheets tidy."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from kisch import Sheet, snap

PRJ_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "hardware"))
EXTRA = (PRJ_DIR,)
LIB = "LazerGamebox_lcsc"          # EasyEDA/JLC imported footprints
FP_ESP32 = "RF_Module:ESP32-WROOM-32E"
FP_USBC = "LazerGamebox:USB_C_Receptacle_HRO_TYPE-C-31-M-12"          # KiCad footprint + LCSC STEP
FP_TACT = "LazerGamebox:SW_Push_1P1T_XKB_TS-1187A"

FP_R = {"0603": "Resistor_SMD:R_0603_1608Metric", "0805": "Resistor_SMD:R_0805_2012Metric",
        "1206": "Resistor_SMD:R_1206_3216Metric"}
FP_C = {"0603": "Capacitor_SMD:C_0603_1608Metric", "0805": "Capacitor_SMD:C_0805_2012Metric",
        "1206": "Capacitor_SMD:C_1206_3216Metric"}

# JLC Basic resistors, verified 2026-09-28 (value -> (LCSC, package))
R_LCSC = {
    "0R": ("C21189", "0603"), "10R": ("C22859", "0603"), "22R": ("C23345", "0603"), "33R": ("C23140", "0603"),
    "100R": ("C22775", "0603"), "330R": ("C23138", "0603"), "470R": ("C23179", "0603"),
    "1k": ("C21190", "0603"), "1.2k": ("C22765", "0603"), "1.5k": ("C22843", "0603"), "2k": ("C22975", "0603"),
    "2.2k": ("C4190", "0603"), "3.3k": ("C22978", "0603"), "4.7k": ("C23162", "0603"), "5.1k": ("C23186", "0603"),
    "10k": ("C25804", "0603"), "22k": ("C31850", "0603"), "33k": ("C4216", "0603"), "39k": ("C23153", "0603"),
    "47k": ("C25819", "0603"), "68k": ("C23231", "0603"), "100k": ("C25803", "0603"), "150k": ("C22807", "0603"),
    "200k": ("C25811", "0603"), "220k": ("C22961", "0603"), "330k": ("C23137", "0603"), "470k": ("C23164", "0603"),
    "1M": ("C22935", "0603"),
    "20R/0805": ("C17544", "0805"), "100R/0805": ("C17408", "0805"), "10R/1206": ("C17903", "1206"), "12R/1206": ("C17913", "1206"), "1.1k": ("C22764", "0603"), "2.2k": ("C4190", "0603"),
}
C_LCSC = {
    "100pF": ("C14858", "0603"), "1nF": ("C1588", "0603"), "47nF": ("C1622", "0603"), "22pF": ("C1653", "0603"), "100nF": ("C14663", "0603"),
    "1uF": ("C15849", "0603"), "4.7uF": ("C19666", "0603"), "10uF": ("C15850", "0805"), "22uF": ("C45783", "0805"),
    "100uF": ("C15008", "1206"), "4.7uF/0805": ("C1779", "0805"),
}


def R(sh, ref, value, at, rot=0, dnp=False, pkg=None, lcsc=None):
    key = value if pkg is None else f"{value}/{pkg}"
    code, p = R_LCSC.get(key, (lcsc or "", pkg or "0603"))
    return sh.symbol("Device:R", ref, value, at, rot=rot, footprint=FP_R[p], lcsc=code, dnp=dnp)


def C(sh, ref, value, at, rot=0, dnp=False, pkg=None, lcsc=None):
    key = value if pkg is None else f"{value}/{pkg}"
    code, p = C_LCSC.get(key, (lcsc or "", pkg or "0603"))
    return sh.symbol("Device:C", ref, value, at, rot=rot, footprint=FP_C[p], lcsc=code, dnp=dnp)


def CP(sh, ref, value, at, rot=0, dnp=False):
    return sh.symbol("Device:C_Polarized", ref, value, at, rot=rot, footprint="Capacitor_SMD:CP_Elec_6.3x7.7",
                     lcsc="C2858856", dnp=dnp, description="470 uF 10 V SMD electrolytic")


def L(sh, ref, value, at, rot=0):
    return sh.symbol("Device:L", ref, value, at, rot=rot, footprint="Inductor_SMD:L_Sunlord_SWPA4030S",
                     lcsc="C42193", description="Sunlord SWPA4030S1R0NT 1 uH, Isat 5.7 A")


def PMOS(sh, ref, at, rot=270, mirror="x"):
    """AO3401A. Default orientation: S left, D right, G at the bottom (high-side switch)."""
    return sh.symbol("Transistor_FET:AO3401A", ref, "AO3401A", at, rot=rot, mirror=mirror,
                     footprint="Package_TO_SOT_SMD:SOT-23", lcsc="C15127")


def NMOS(sh, ref, at, rot=0, mirror=None, dnp=False):
    """2N7002, rot 0: G left, D top, S bottom."""
    return sh.symbol("Transistor_FET:2N7002", ref, "2N7002", at, rot=rot, mirror=mirror,
                     footprint="Package_TO_SOT_SMD:SOT-23", lcsc="C8545", dnp=dnp)


def NPN(sh, ref, at, rot=0, mirror=None, dnp=False):
    """SS8050, rot 0: B left, C top, E bottom."""
    return sh.symbol("Transistor_BJT:SS8050", ref, "SS8050", at, rot=rot, mirror=mirror,
                     footprint="Package_TO_SOT_SMD:SOT-23", lcsc="C2150", dnp=dnp)


def two_pin_ends(sym):
    """(pin1_point, pin2_point) of a 2-pin part."""
    return sym.pin("1"), sym.pin("2")


def cap_between(sh, ref, value, x, y, rail, gnd="GND", pkg=None, dnp=False, rail_lib=None):
    """Vertical cap centred at (x, y): top to `rail` power symbol, bottom to GND symbol."""
    c = C(sh, ref, value, (x, y), pkg=pkg, dnp=dnp)
    top, bot = two_pin_ends(c)
    sh.pin_power(c, "1", rail, length=2.54, lib=rail_lib or lib_for(rail))
    sh.pin_power(c, "2", gnd, length=2.54)
    return c


def cp_between(sh, ref, value, x, y, rail, gnd="GND", dnp=False):
    c = CP(sh, ref, value, (x, y), dnp=dnp)
    sh.pin_power(c, "1", rail, length=2.54, lib=lib_for(rail))
    sh.pin_power(c, "2", gnd, length=2.54)
    return c


def lib_for(rail):
    return "power" if rail in ("GND", "+3V3", "VBUS", "+BATT", "+5V") else "LazerGamebox"


def pullup(sh, ref, value, x, y, rail, sig_pt=None, length=2.54):
    """Vertical resistor centred at (x, y); top to `rail`, bottom wire to sig_pt (if given)."""
    r = R(sh, ref, value, (x, y))
    sh.pin_power(r, "1", rail, length=length, lib=lib_for(rail))
    if sig_pt is not None:
        sh.wire(r.pin("2"), sig_pt)
    return r


def pulldown(sh, ref, value, x, y, sig_pt=None, length=2.54):
    r = R(sh, ref, value, (x, y))
    sh.pin_power(r, "2", "GND", length=length)
    if sig_pt is not None:
        sh.wire(r.pin("1"), sig_pt)
    return r


def series_h(sh, kind, ref, value, x, y, **kw):
    """Horizontal 2-pin part centred at (x, y); returns (left_pt, right_pt)."""
    f = {"R": R, "C": C, "L": L}[kind]
    s = f(sh, ref, value, (x, y), rot=90, **kw)
    return s, s.pin("1"), s.pin("2")


def lab(sh, text, at, rot=0, kind="global", shape="bidirectional"):
    if kind == "global":
        sh.glabel(text, at, rot, shape)
    else:
        sh.label(text, at, rot)


def tp(sh, ref, at, net=None, rot=0):
    t = sh.symbol("Connector:TestPoint", ref, net or "TP", at, rot=rot, footprint="TestPoint:TestPoint_Pad_D1.5mm",
                  in_bom=False)
    return t


def pin_series_label(sh, sym, pin, ref, value, text, length=20.32, kind="global", shape="passive", gap=2.54):
    """Stub from a left/right pin, a series resistor on it, then a label at `length` from the pin.
    Returns (resistor, node on the pin side, label point)."""
    p = sym.pin(pin)
    d = sym.pin_dir(pin)
    node = (p[0] + d[0] * gap, p[1])
    r = R(sh, ref, value, (p[0] + d[0] * (gap + 3.81), p[1]), rot=90)
    near, far = (r.pin("2"), r.pin("1")) if d[0] < 0 else (r.pin("1"), r.pin("2"))
    sh.wire(p, node, near)
    end = (p[0] + d[0] * length, p[1])
    sh.wire(far, end)
    lab(sh, text, end, 180 if d[0] < 0 else 0, kind, shape)
    return r, node, end

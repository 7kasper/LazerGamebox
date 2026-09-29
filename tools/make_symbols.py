#!/usr/bin/env python3
"""Generate the project symbol library LazerGamebox.kicad_sym (KiCad 10 format).

Box symbols are described by pin lists per side; pins are ordered top-to-bottom (left and
right sides) or left-to-right (top and bottom sides). Each pin: (number, name, etype)
where etype is a KiCad electrical type. Pins with etype 'nc_hidden' are hidden no-connect
pins stacked at the symbol origin (module pads that are not used).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from kisym import S, to_sexpr

PITCH = 2.54
PIN_LEN = 5.08


def _font(size=1.27):
    return ["effects", ["font", ["size", size, size]]]


def _prop(name, value, x=0, y=0, rot=0, hide=False):
    p = ["property", S(name), S(value), ["at", x, y, rot], ["show_name", "no"], ["do_not_autoplace", "no"]]
    if hide:
        p.append(["hide", "yes"])
    p.append(_font())
    return p


def _pin(etype, x, y, rot, length, name, number, hide=False):
    p = ["pin", etype, "line", ["at", x, y, rot], ["length", length]]
    if hide:
        p.append(["hide", "yes"])
    p.append(["name", S(name), _font()])
    p.append(["number", S(number), _font()])
    return p


def box_symbol(name, left=(), right=(), top=(), bottom=(), hidden=(), ref="U", value=None,
               footprint="", datasheet="", description="", width=None, pin_len=PIN_LEN,
               keywords="", stacked_gnd=None, in_bom=True):
    """Return the S-expression tree of a rectangular symbol."""
    value = value or name
    nl, nr = len(left), len(right)
    nt, nb = len(top), len(bottom)
    rows = max(nl, nr, 1)
    cols = max(nt, nb, 1)
    # box size: leave room for names; height from rows, width from name lengths
    longest = 0
    for side in (left, right):
        for p in side:
            longest = max(longest, len(p[1]))
    if width is None:
        width = max(cols * PITCH + PITCH, 2 * (longest * 1.1 + 3.0), 15.24)
    width = round(round(width / PITCH) * PITCH, 3)
    height = (rows + 1) * PITCH
    if nt or nb:
        height = max(height, (rows + 2) * PITCH)
    height = round(round(height / PITCH) * PITCH, 3)
    hw, hh = width / 2, height / 2
    sym = ["symbol", S(name), ["pin_names", ["offset", 1.016]], ["exclude_from_sim", "no"],
           ["in_bom", "yes" if in_bom else "no"], ["on_board", "yes"], ["in_pos_files", "yes"],
           ["duplicate_pin_numbers_are_jumpers", "no"],
           _prop("Reference", ref, -hw, hh + 1.27),
           _prop("Value", value, -hw, -hh - 1.27),
           _prop("Footprint", footprint, 0, 0, hide=True),
           _prop("Datasheet", datasheet, 0, 0, hide=True),
           _prop("Description", description, 0, 0, hide=True)]
    if keywords:
        sym.append(_prop("ki_keywords", keywords, hide=True))
    g = ["symbol", S(f"{name}_0_1"),
         ["rectangle", ["start", -hw, hh], ["end", hw, -hh],
          ["stroke", ["width", 0.254], ["type", "default"]], ["fill", ["type", "background"]]]]
    sym.append(g)
    u = ["symbol", S(f"{name}_1_1")]
    # left/right pins top-to-bottom, centred vertically
    def ys(n):
        top_y = ((n - 1) / 2) * PITCH
        return [round(top_y - i * PITCH, 3) for i in range(n)]
    for (num, pname, et), y in zip(left, ys(nl)):
        u.append(_pin(et, -hw - pin_len, y, 0, pin_len, pname, str(num)))
    for (num, pname, et), y in zip(right, ys(nr)):
        u.append(_pin(et, hw + pin_len, y, 180, pin_len, pname, str(num)))
    def xs(n):
        left_x = -((n - 1) / 2) * PITCH
        return [round(left_x + i * PITCH, 3) for i in range(n)]
    for (num, pname, et), x in zip(top, xs(nt)):
        u.append(_pin(et, x, hh + pin_len, 270, pin_len, pname, str(num)))
    for (num, pname, et), x in zip(bottom, xs(nb)):
        u.append(_pin(et, x, -hh - pin_len, 90, pin_len, pname, str(num)))
    if stacked_gnd:
        # extra GND pins stacked (hidden) on top of the first bottom GND pin
        x0 = xs(nb)[stacked_gnd[0]]
        for num in stacked_gnd[1]:
            u.append(_pin("power_in", x0, -hh - pin_len, 90, pin_len, "GND", str(num), hide=True))
    # hidden no-connect pins: each on its own grid point inside the body (stacked pins would connect)
    cols_in = max(1, int(width / PITCH) - 1)
    for i, (num, pname, et) in enumerate(hidden):
        gx = -hw + PITCH * (1 + i % cols_in)
        gy = hh - PITCH * (1 + i // cols_in)
        u.append(_pin("no_connect", round(gx, 3), round(gy, 3), 0, 0, pname, str(num), hide=True))
    sym.append(u)
    sym.append(["embedded_fonts", "no"])
    return sym


def power_symbol(name, description=""):
    sym = ["symbol", S(name), ["power", "global"], ["pin_numbers", ["hide", "yes"]],
           ["pin_names", ["offset", 0], ["hide", "yes"]], ["exclude_from_sim", "no"], ["in_bom", "yes"],
           ["on_board", "yes"], ["in_pos_files", "yes"], ["duplicate_pin_numbers_are_jumpers", "no"],
           _prop("Reference", "#PWR", 0, -3.81, hide=True),
           _prop("Value", name, 0, 3.556),
           _prop("Footprint", "", hide=True), _prop("Datasheet", "", hide=True),
           _prop("Description", description or f'Power symbol creates a global label with name "{name}"', hide=True),
           _prop("ki_keywords", "global power", hide=True)]
    def pl(a, b):
        return ["polyline", ["pts", ["xy", a[0], a[1]], ["xy", b[0], b[1]]],
                ["stroke", ["width", 0], ["type", "default"]], ["fill", ["type", "none"]]]
    g = ["symbol", S(f"{name}_0_1"), pl((-0.762, 1.27), (0, 2.54)), pl((0, 2.54), (0.762, 1.27)), pl((0, 0), (0, 2.54))]
    u = ["symbol", S(f"{name}_1_1"), _pin("power_in", 0, 0, 90, 0, "", "1")]
    sym += [g, u, ["embedded_fonts", "no"]]
    return sym


def build():
    syms = []
    # ---- SA818S-U walkie-talkie module ----
    syms.append(box_symbol(
        "SA818S-U",
        left=[(8, "VBAT", "power_in"), (6, "PD", "input"), (5, "PTT", "input"), (7, "H/L", "input"),
              (16, "RXD", "input"), (17, "TXD", "output")],
        right=[(12, "ANT", "passive"), (3, "AF_OUT", "output"), (18, "MIC_IN", "input"), (1, "AUDIO_ON", "output")],
        bottom=[(9, "GND", "power_in"), (10, "GND", "power_in")],
        stacked_gnd=(0, [19, 20]),
        hidden=[(2, "NC", "no_connect"), (4, "NC", "no_connect"), (11, "NC", "no_connect"),
                (13, "NC", "no_connect"), (14, "NC", "no_connect"), (15, "NC", "no_connect")],
        footprint="LazerGamebox_lcsc:WIRELM-SMD_G-NICERF_SA818S-X", datasheet="https://www.nicerf.com/products/detail/walkie-talkie-module-sa818s.html",
        description="G-NiceRF SA818S-U 1 W UHF walkie-talkie module, 400-480 MHz, UART control", width=30.48))
    # ---- Ra-01SH LoRa module ----
    syms.append(box_symbol(
        "Ra-01SH",
        left=[(3, "3V3", "power_in"), (4, "RESET", "input"), (15, "NSS", "input"), (12, "SCK", "input"),
              (14, "MOSI", "input"), (13, "MISO", "output")],
        right=[(1, "ANT", "passive"), (6, "DIO1", "bidirectional"), (7, "DIO2", "bidirectional"),
               (8, "DIO3", "bidirectional"), (10, "BUSY", "output"), (5, "TXEN", "input"), (11, "RXEN", "input")],
        bottom=[(2, "GND", "power_in"), (9, "GND", "power_in"), (16, "GND", "power_in")],
        footprint="LazerGamebox_lcsc:WIRELM-SMD_RA-01SH", datasheet="https://docs.ai-thinker.com/en/lora",
        description="Ai-Thinker Ra-01SH SX1262 LoRa module 803-930 MHz, SPI", width=25.4))
    # ---- ATGM336H-5N31 GNSS ----
    syms.append(box_symbol(
        "ATGM336H-5N31",
        left=[(8, "VCC", "power_in"), (6, "VBAT", "power_in"), (5, "ON/OFF", "input"), (9, "~{RESET}", "input"),
              (3, "RXD", "input"), (2, "TXD", "output"), (4, "1PPS", "output"), (16, "SDA", "bidirectional"),
              (17, "SCL", "bidirectional")],
        right=[(11, "RF_IN", "input"), (14, "VCC_RF", "power_out")],
        bottom=[(1, "GND", "power_in"), (10, "GND", "power_in"), (12, "GND", "power_in")],
        hidden=[(7, "NC", "no_connect"), (13, "NC", "no_connect"), (15, "RSV", "no_connect"), (18, "RSV", "no_connect")],
        footprint="LazerGamebox_lcsc:GPSM-SMD_ATGM336H-TR", datasheet="https://www.lcsc.com/product-detail/C90770.html",
        description="ZHONGKEWEI ATGM336H-5N31 GNSS module (GPS/BDS/GLONASS), UART, 1PPS", width=25.4))
    # ---- SIM7080G cellular (DNP) ----
    gnd_pins = [8, 13, 19, 21, 27, 30, 31, 33, 36, 37, 45, 63, 66, 67, 69, 70, 71, 72, 73, 74, 75, 76, 77]
    used = {1, 2, 3, 4, 5, 6, 7, 15, 16, 17, 18, 24, 25, 26, 32, 34, 35, 38, 39, 40, 41, 42, 43, 44, 68} | set(gnd_pins)
    names = {9: "PCM_DIN", 10: "PCM_DOUT", 11: "PCM_CLK", 12: "PCM_SYNC", 14: "GPIO5", 20: "USB_BOOT", 22: "UART2_TXD",
             23: "UART2_RXD", 28: "NC", 29: "NC", 46: "NC", 47: "NC", 48: "SPI_CS", 49: "SPI_MOSI", 50: "SPI_CLK",
             51: "SPI_MISO", 52: "NC", 53: "NC", 54: "NC", 55: "NC", 56: "NC", 57: "GPIO1", 58: "GPIO2", 59: "GPIO3",
             60: "GPIO4", 61: "UART3_TXD", 62: "UART3_RXD", 64: "I2C_SDA", 65: "I2C_SCL"}
    hidden = [(n, names[n], "no_connect") for n in range(1, 78) if n not in used]
    syms.append(box_symbol(
        "SIM7080G",
        left=[(34, "VBAT", "power_in"), (35, "VBAT", "power_in"), (39, "PWRKEY", "input"), (40, "VDD_EXT", "power_out"),
              (41, "NETLIGHT", "output"), (42, "STATUS", "output"), (38, "ADC", "input"),
              (1, "UART1_TXD", "output"), (2, "UART1_RXD", "input"), (3, "UART1_RTS", "output"), (4, "UART1_CTS", "input"),
              (5, "UART1_DCD", "output"), (6, "UART1_DTR", "input"), (7, "UART1_RI", "output")],
        right=[(32, "RF_ANT", "passive"), (68, "GNSS_ANT", "passive"), (43, "ANT_CONTROL1", "output"),
               (44, "ANT_CONTROL0", "output"), (18, "SIM_VDD", "power_out"), (15, "SIM_DATA", "bidirectional"),
               (16, "SIM_CLK", "output"), (17, "SIM_RST", "output"), (24, "USB_VBUS", "power_in"),
               (25, "USB_DP", "bidirectional"), (26, "USB_DM", "bidirectional")],
        bottom=[(gnd_pins[0], "GND", "power_in")],
        stacked_gnd=(0, gnd_pins[1:]), hidden=hidden,
        footprint="LazerGamebox_lcsc:LCC-SMD_SIM7080G", datasheet="https://www.simcom.com/product/SIM7080G.html",
        description="SIMCom SIM7080G Cat-M/NB-IoT + GNSS module, LGA 77, 1.8 V logic (DNP option)", width=35.56))
    # ---- NS4150B class-D amplifier ----
    syms.append(box_symbol(
        "NS4150B",
        left=[(1, "CTRL", "input"), (2, "BYPASS", "passive"), (3, "INP", "input"), (4, "INN", "input")],
        right=[(8, "VoP", "output"), (5, "VoN", "output")],
        top=[(6, "VCC", "power_in")], bottom=[(7, "GND", "power_in")],
        footprint="Package_SO:MSOP-8_3x3mm_P0.65mm", datasheet="https://www.lcsc.com/product-detail/C189961.html",
        description="Nsiway NS4150B 3 W mono class-D audio amplifier, MSOP-8", width=17.78))
    # ---- FS8205A dual N-MOSFET ----
    syms.append(box_symbol(
        "FS8205A",
        left=[(6, "G1", "input"), (1, "S1", "passive")], right=[(4, "G2", "input"), (3, "S2", "passive")],
        top=[(2, "D1/D2", "passive"), (5, "D1/D2", "passive")], ref="Q",
        footprint="Package_TO_SOT_SMD:SOT-23-6", datasheet="https://www.lcsc.com/product-detail/C908265.html",
        description="FUXINSEMI FS8205A dual N-channel MOSFET 20 V 6 A, common drain, SOT-23-6", width=15.24))
    # ---- TPS61023 boost ----
    syms.append(box_symbol(
        "TPS61023DRL",
        left=[(3, "VIN", "power_in"), (2, "EN", "input"), (1, "FB", "input")],
        right=[(5, "SW", "passive"), (6, "VOUT", "power_out")], bottom=[(4, "GND", "power_in")],
        footprint="Package_TO_SOT_SMD:SOT-563", datasheet="https://www.ti.com/lit/ds/symlink/tps61023.pdf",
        description="TI TPS61023 synchronous boost converter, 3.7 A switch, true disconnect, SOT-563", width=15.24))
    # ---- TS5A3159 analog SPDT ----
    syms.append(box_symbol(
        "TS5A3159",
        left=[(1, "NO", "passive"), (3, "NC", "passive"), (6, "IN", "input")], right=[(4, "COM", "passive")],
        top=[(5, "V+", "power_in")], bottom=[(2, "GND", "power_in")],
        footprint="Package_TO_SOT_SMD:SOT-363_SC-70-6", datasheet="https://www.ti.com/lit/ds/symlink/ts5a3159.pdf",
        description="TI TS5A3159 1 ohm SPDT analog switch, SC-70-6", width=15.24))
    # ---- IRM-H638T IR receiver ----
    syms.append(box_symbol(
        "IRM-H638T",
        left=[(3, "OUT", "output")], top=[(4, "VCC", "power_in")],
        bottom=[(1, "GND", "power_in"), (2, "GND", "power_in")],
        footprint="LazerGamebox:Everlight_IRM-H6xxT", datasheet="https://www.everlight.com",
        description="Everlight IRM-H638T/TR2 38 kHz IR receiver module, SMD", width=15.24))
    # ---- CH340C (V3 as passive so it can be tied to VCC at 3.3 V without an ERC clash) ----
    syms.append(box_symbol(
        "CH340C",
        left=[(5, "UD+", "bidirectional"), (6, "UD-", "bidirectional"), (15, "R232", "input")],
        right=[(2, "TXD", "output"), (3, "RXD", "input"), (9, "~{CTS}", "input"), (10, "~{DSR}", "input"),
               (11, "~{RI}", "input"), (12, "~{DCD}", "input"), (13, "~{DTR}", "output"), (14, "~{RTS}", "output")],
        top=[(16, "VCC", "power_in"), (4, "V3", "passive")], bottom=[(1, "GND", "power_in")],
        hidden=[(7, "NC", "no_connect"), (8, "NC", "no_connect")],
        footprint="Package_SO:SOIC-16_3.9x9.9mm_P1.27mm", datasheet="https://www.wch-ic.com/products/CH340.html",
        description="WCH CH340C USB to UART bridge with internal oscillator, SOIC-16", width=20.32))
    # ---- Display FPC connector, named pins ----
    syms.append(box_symbol(
        "LCD_HS20HS072RX_FPC12",
        left=[(1, "GND", "passive"), (2, "CS", "passive"), (3, "RS", "passive"), (4, "SCL", "passive"),
              (5, "SDA", "passive"), (6, "RST", "passive"), (7, "NC", "no_connect"), (8, "IOVCC", "passive"),
              (9, "VCC", "passive"), (10, "LEDA", "passive"), (11, "LEDK", "passive"), (12, "GND", "passive")],
        ref="J", footprint="LazerGamebox_lcsc:FPC-SMD_12P-P0.50_05A20H12P", datasheet="https://www.lcsc.com/product-detail/C5329582.html",
        description="12-pin 0.5 mm ZIF for HS20HS072RX 2.0in ST7789 320x240 panel", width=20.32))
    # ---- nano-SIM socket: KiCad's Connector:SIM_Card with a footprint filter that accepts the LCSC name ----
    from kisym import get_symbol, atom, find_all
    import copy
    sim, parent = get_symbol("Connector", "SIM_Card", ())
    sim = copy.deepcopy(parent if parent is not None else sim)
    sim[1] = S("SIM_Card")
    for c in find_all(sim, "property"):
        if atom(c[1]) == "ki_fp_filters":
            c[2] = S("*SIM*Card*Holder* *SIM*")
        if atom(c[1]) == "Footprint":
            c[2] = S("LazerGamebox_lcsc:SIM-SMD_NANO-SIM-XG6P-H1.35")
    for c in sim:
        if isinstance(c, list) and atom(c[0]) == "symbol":
            c[1] = S(atom(c[1]).replace("SIM_Card", "SIM_Card", 1))
    syms.append(sim)
    # ---- BQ25601 charger with power path ----
    syms.append(box_symbol(
        "BQ25601",
        left=[(24, "VBUS", "power_in"), (1, "VAC", "input"), (23, "PMID", "passive"), (22, "REGN", "power_out"),
              (2, "PSEL", "input"), (9, "~{CE}", "input"), (12, "~{QON}", "input"), (11, "TS", "input")],
        right=[(19, "SW", "passive"), (20, "SW", "passive"), (21, "BTST", "passive"), (15, "SYS", "power_out"),
               (16, "SYS", "passive"), (13, "BAT", "power_out"), (14, "BAT", "passive"), (4, "STAT", "open_collector"),
               (3, "~{PG}", "open_collector"), (7, "~{INT}", "open_collector"), (6, "SDA", "bidirectional"), (5, "SCL", "input")],
        bottom=[(17, "GND", "power_in")], stacked_gnd=(0, [18, 25]),
        hidden=[(8, "NC", "no_connect"), (10, "NC", "no_connect")],
        footprint="LazerGamebox_lcsc:VFQFPN-24_L4.0-W4.0-P0.50-BL-EP2.8", datasheet="https://www.ti.com/lit/ds/symlink/bq25601.pdf",
        description="TI BQ25601 3 A I2C 1S switching charger with NVDC power path and ship mode, WQFN-24", width=22.86))
    # ---- HUSB238 USB PD sink ----
    syms.append(box_symbol(
        "HUSB238",
        left=[(1, "VIN", "power_in"), (2, "D+", "passive"), (3, "D-", "passive"), (4, "CC1", "bidirectional"), (5, "CC2", "bidirectional")],
        right=[(6, "SDA", "bidirectional"), (7, "SCL", "input"), (8, "VSET", "input"), (9, "ISET", "input"), (10, "GATE", "open_collector")],
        bottom=[(11, "GND", "power_in")],
        footprint="LazerGamebox_lcsc:DFN-10_L3.0-W3.0-P0.50-BL-EP2.5", datasheet="https://www.hynetek.com/",
        description="Hynetek HUSB238 USB PD sink controller with I2C source-capability readback, DFN-10", width=17.78))
    # ---- MAX17048 fuel gauge ----
    syms.append(box_symbol(
        "MAX17048",
        left=[(3, "VDD", "power_in"), (2, "CELL", "input"), (6, "QSTRT", "input"), (1, "CTG", "passive")],
        right=[(8, "SDA", "bidirectional"), (7, "SCL", "input"), (5, "~{ALRT}", "open_collector")],
        bottom=[(4, "GND", "power_in")], stacked_gnd=(0, [9]),
        footprint="LazerGamebox_lcsc:TDFN-8_L2.0-W2.0-P0.50-BL-EP1.2", datasheet="https://www.analog.com/media/en/technical-documentation/data-sheets/MAX17048-MAX17049.pdf",
        description="Maxim MAX17048 ModelGauge 1S fuel gauge, I2C 0x36, TDFN-8 2x2", width=17.78))
    # ---- MSM421ACT006 analog MEMS microphone ----
    syms.append(box_symbol(
        "MIC_MEMS_ANALOG", ref="MK",
        right=[(1, "OUT", "output")], top=[(4, "VDD", "passive")],          # VDD fed through a filter resistor
        bottom=[(2, "GND", "power_in")], stacked_gnd=(0, [3]),
        footprint="LazerGamebox_lcsc:MIC-SMD_4P-L2.8-W1.9-P1.01-TL", datasheet="https://datasheet.lcsc.com/lcsc/C51928207.pdf",
        description="MEMSensing MSM421ACT006 analog top-port MEMS microphone, -42 dBV/Pa, 1.5 to 3.6 V, LGA-4", width=10.16))
    # ---- power symbols ----
    for n in ("VBAT", "VSYS", "RADIO_4V5", "VBAT_SW", "GPS_3V3", "LCD_3V3"):
        syms.append(power_symbol(n))
    lib = ["kicad_symbol_lib", ["version", 20251024], ["generator", S("lazergamebox_make_symbols")]] + syms
    return lib


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "hardware", "LazerGamebox.kicad_sym")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(to_sexpr(build()) + "\n")
    print("wrote", out)

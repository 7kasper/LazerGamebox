# Power block review 2 (USB-C, BQ25601, cells, HUSB238, MAX17048)

Date 2026-09-29. Second, independent review of the redrawn power block. Sources: docs/design.md
sections 0, 2, 5; tools/power_block.py; tools/make_symbols.py; hardware/reports/netlist.xml
(authoritative); datasheets in scratchpad/ds: bq25601.pdf (TI SLUSCK5A, Rev A March 2023),
husb238_en.pdf (Hynetek Rev 2.0) plus the LCSC Rev 2.5 copy and husb238_regs.pdf (Rev 1.1),
husb238_evb.pdf (RD-2010), max17048.pdf (Maxim 19-6171 Rev 7), dw01a.pdf (Puolop Rev B),
fs8205a.pdf (Fuxinsemi V2.1), usblc6.pdf (ST Rev 5), typec.pdf (HRO TYPE-C-31-M-12 drawing).
Page numbers refer to the printed page numbers of those documents. No project file was modified.

Netlist facts used throughout (hardware/reports/netlist.xml):

- VBUS: J101 A4/A9/B4/B9, U101.24 (VBUS), U101.1 (VAC), U105.1 (VIN), U202.3 (XC6206), D101.5, R103.2, C101, C121, C205.
- VSYS: U101.15/16, C118, C119, L101.2 (charger inductor, see 1), R104.1, U103.3/4 (buck), U104.3 (boost), Q107.2, R119.1, C105/C106/C109/C110/C114.
- VBAT: U101.13/14, C120, BT101.1, BT102.1, R106.1, U106.2/3, C122, U403.34/35 and C408-410 (DNP SIM7080G).
- GND includes U101.9 (CE), U101.17/18/25, U105.11, U106.1/4/6/9, R102.2, R107.2, R123.2, SW101.2, J101 A1/A12/B1/B12/SH.
- PWR_INT: R105.2, U101.7, U106.5, U205.20 (P17). SDA/SCL: U101.6/5, U106.8/7, R125.2/R126.2 (HUSB238 via 330 R), R206/R207 4.7 k.
- Unconnected: U101.3 (PG), U101.8, U101.10, U105.2, U105.3, U105.10, U102.4 (TD), J101 A8/B8.

---

## 1. BQ25601 (U101)

**Verdict: change needed** (one high: the charger inductor shares reference L101 with the buck inductor; everything on the IC itself is wired as the datasheet asks).

Symbol check (make_symbols.py vs datasheet p5 Figure 7-1 and Table 7-1): 1 VAC, 2 PSEL, 3 PG, 4 STAT, 5 SCL, 6 SDA, 7 INT, 8 NC, 9 CE, 10 NC, 11 TS, 12 QON, 13/14 BAT, 15/16 SYS, 17/18 GND, 19/20 SW, 21 BTST, 22 REGN, 23 PMID, 24 VBUS, 25 thermal pad. All 25 match; footprint VFQFPN-24_L4.0-W4.0-P0.50-BL-EP2.8 has pads 1-25 with pad 25 = 2.8 mm exposed pad (TI package 4 x 4 mm, 0.5 mm pitch).

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| Charger inductor reference | n/a (design tooling) | `tools/power_block.py` line 103 creates `L101` for the charger; `tools/gen_schematic.py` line 44 also creates `L101` for the TPS62A02 buck. The netlist has one `<comp ref="L101">` but four L101 nodes: pin 1 in both `/power/SW` and `Net-(U103-SW)`, pin 2 in both `VSYS` and `+3V3`. ERC does not flag it. On the PCB this becomes one footprint (or two with the same reference) carrying the charger SW node, the buck SW node, VSYS and +3V3 | **High** | Rename the charger inductor to **L103** in `tools/power_block.py` (line 103), regenerate, re-export ERC and netlist, update design.md section 4 ("L101, L102" becomes "L101-L103", 3x C42193). Add a duplicate-reference assertion in the generator's `symbol()` so this cannot recur |
| VAC | "This pin must be connected to VBUS pin" (p6) | U101.1 and U101.24 both on VBUS | OK | none |
| VBUS decoupling | 1 uF ceramic VBUS to GND close to the device (p6) | C101 1 uF 0603 = C15849 (50 V X7R) | OK | none |
| PMID | 10 uF ceramic PMID to GND (p6); 22 uF suggested for 3 A charging, 25 V rating preferred (p46) | C102 + C115, 10 uF 0805 = C15850 (25 V X5R) | OK | none. Layout: place them at PMID/GND first (layout guideline 1, p52) |
| REGN | 4.7 uF, 10 V rating, close to the IC (p6) | C116 4.7 uF 0603 = C19666 (10 V X5R) | OK | none |
| BTST | 0.047 uF from SW to BTST (p6) | C117 47 nF between /power/SW and /power/BTST | OK | none |
| SYS | 20 uF close to SYS; loop compensated for 20 uF ceramic (p6, p46) | C118 + C119 10 uF 25 V 0805 on VSYS, plus the buck and boost input caps (C105, C106, C109, C110) on the same net | OK | none |
| BAT | 10 uF close to BAT (p5) | C120 10 uF on VBAT | OK | none |
| Inductor | Isat >= ICHG + ripple/2, ripple = Vin D (1-D)/(fs L) (p45-46): 5 V in, 1 uH, 1.5 MHz gives 0.45 A at 4.2 V, 0.83 A worst case at D = 0.5. ISWOP max 3.25 A (p7) | 1 uH SWPA4030S1R0NT, Isat 5.7 A; worst-case peak 3.25 + 0.42 = 3.7 A | OK | none (after the L103 rename) |
| TS network without NTC | "When TS pin is not used, connect a 10 k from REGN to TS and a 10 k from TS to GND" (p6). Buck-mode JEITA thresholds as % of REGN (p11-12): T1 cold 73.3 % (suspend above), T2 cool 68 % rising / 66.8 % falling, T3 warm 44.7 % rising / 45.7 % falling, T5 hot 34.2 % (suspend below). Normal window (T2 to T3) = full ICHG and VREG; the warm window drops to 4.1 V (JEITA_VSET = 0, REG07[4], p40) and disables termination; the cool window halves ICHG (JEITA_ISET = 0, p38) | R101 10 k REGN-TS, R102 10 k TS-GND: TS = 50.0 % of REGN (49.5 to 50.5 % with 1 % parts). Margin to the warm threshold worst case (46.2 %) is 3.3 % of REGN, about 155 mV at REGN 4.7 V (p12: 4.6 to 4.7 V at 5 V input); margin to the cool threshold (66 % min) is 15.5 % | OK | none. The pack charges at 4.208 V and 2.04 A regardless of temperature. Optional (low): the same two footprints can carry the datasheet NTC network later (RT1 5.23 k, RT2 30.9 k, 103AT from TS to GND, p24) if a thermistor is glued to a holder |
| PSEL | Digital input, VIH 1.3 V min, VIL 0.4 V max, leakage 1 uA max (p12); abs max 7 V (p7). High = 500 mA, low = 2.4 A (Table 9-1 p19, REG00 p33) | R103 10 k to VBUS; drop at 1 uA is 10 mV, PSEL is above 1.3 V long before VBUS_GD (3.9 V, p9) | OK | none. A resistor is fine, and better than a hard tie: it limits current into the 7 V rated pin during VBUS transients while the VBUS pin itself is 22 V rated. Result after input detection: IINDPM = 500 mA, VBUS_STAT = 001 "USB host SDP" (p41) |
| CE | Charge enabled when CE low AND CHG_CONFIG = 1 (p34) | U101.9 on GND | OK | none |
| QON | Internal 200 k pull-up; high-to-low > tSHIPMODE (0.9 to 1.3 s, p13) exits ship mode; low > tQON_RST (8 to 12 s) without adapter opens BATFET for 250 to 400 ms = full system reset (p28) | SW101 to GND, no external pull-up, no cap | OK | none. Optional 100 nF across SW101 for ESD only |
| STAT LED | Open drain, sink max 6 mA (p7), VOL 0.4 V (p12); LOW while charging, HIGH when done or in sleep, 1 Hz blink on fault (Table 9-4 p29) | D102 KT-0603R cathode on STAT, anode via R104 2.2 k to VSYS. At VSYS 4.2 V: (4.2 - 2.0 - 0.3)/2.2 k = 0.9 mA; at VSYSMAX 4.48 V (p9): 1.0 mA | OK (low) | Within limits, but 0.9 mA is a dim charge indicator. Consider R104 = 1 k (about 1.9 mA, 2.2 mA max), still far below 6 mA |
| INT | Open drain, 256 us active-low pulse, "connect to a logic rail through 10 k" (p5) | R105 10 k to +3V3, net PWR_INT shared with U106 ALRT (open drain, 20 mA sink abs max, MAX17048 p2) and U205 P17 | OK (low) | Electrically fine (wire-OR of two open drains, both rated above 3.3 V). Firmware notes: the MAX17048 ALRT is a latched level (low until CONFIG.ALRT is cleared, MAX17048 p10) and hides BQ25601 pulses until serviced; the BQ25601 pulse is 256 us, so the TCA9555 INT on GPIO32 is also a short pulse and needs an edge interrupt; mask VINDPM/IINDPM interrupts (REG0A[1:0], p43) when charging from weak sources. Optional: GPIO39 is now free (design.md section 0) and RTC-capable; moving PWR_INT there gives a direct deep-sleep wake source and frees P17 |
| PG | Open drain, pull-up only if used (p5) | U101.3 no-connect | OK | none (PG_STAT in REG08 gives the same information) |
| SDA/SCL | 400 kHz fast mode, open drain, "10 k to the logic rail" (p5, p30); abs max 7 V (p7); I2C active from BAT alone above VBAT_UVLOZ 2.5 V (p9) | On the 3.3 V bus with R206/R207 4.7 k | OK | none; 4.7 k is standard for 400 kHz |
| GND, thermal pad | Pad is the ground reference and must be soldered to PCB ground with vias (p6, p52) | Pins 17, 18 and 25 on GND | OK | none; thermal vias under pad 25 in layout |
| NC pins 8, 10 | "Keep the pins float" (p5) | Both no-connect | OK | none |
| VBUS absolute maximum | VAC/VBUS -2 to 22 V (p7), operating 3.9 to 13.5 V; default ACOV 6.5 V (REG06 OVP = 01, p39; 6.1 to 6.7 V, p9) | USBLC6-2SC6 on VBUS: VBR 6 V min at 1 mA, leakage 150 nA max at 5.25 V (USBLC6 p2) | OK | none for 5 V. The weakest parts on VBUS are the USBLC6 (6 V) and the CH340C LDO XC6206 (6 V max input), not the charger; see section 2 on never requesting more than 5 V |

Register defaults quoted in the sheet note, confirmed (register maps p33-40, Table 9-2 p21):

| Parameter | Default | Where |
|---|---|---|
| EN_HIZ | 0 | REG00[7], reset by REG_RST and by watchdog |
| IINDPM after input detection with PSEL high | 500 mA (00100) | REG00[4:0] p33, Table 9-1 p19 |
| ICHG | 2040 mA (100010) | REG02[5:0] p35 (Table 9-2 says 2.048 A) |
| IPRECHG / ITERM | 180 mA / 180 mA | REG03 p36 |
| VREG | 4.208 V (01011), accuracy 4.187 to 4.229 V | REG04[7:3] p37; p10 |
| VRECHG | 100 mV below VREG | REG04[0] |
| Watchdog | 40 s (01) | REG05[5:4] p38; tWDT p13 |
| Safety timer | 10 h, half rate during DPM/JEITA/thermal regulation (TMR2X_EN = 1) | REG05, REG07[6] |
| TREG / JEITA_ISET / JEITA_VSET | 110 C / 50 % / 4.1 V | REG05, REG07 |
| VINDPM / OVP | 4.5 V (0110) / 6.5 V (01) | REG06 p39 |
| SYS_MIN | 3.5 V (101) | REG01[3:1] p34 |
| BATFET_DIS / BATFET_DLY / BATFET_RST_EN | 0 / 1 (10 s delay) / 1 | REG07 p40 |
| VDPM_BAT_TRACK | disabled | REG07[1:0] |

Behaviour confirmed:

- Default mode versus host mode (p20): the device powers up in default mode with the watchdog expired; the first I2C write of WD_RST starts the 40 s watchdog. If the host stops feeding it, registers reset to defaults except IINDPM, VINDPM, BATFET_RST_EN, BATFET_DLY and BATFET_DIS (p20). An IINDPM raised after reading the HUSB238 therefore survives ESP32 deep sleep, but ICHG/VREG changes do not. Any VBUS unplug and replug re-runs input detection and puts IINDPM back to 500 mA (PSEL, p19).
- Ship mode entry (p28): host sets BATFET_DIS (REG07[5]); BATFET opens after tSM_DLY 10 to 15 s unless BATFET_DLY = 0. With USB plugged the system keeps running from VBUS, so ship mode only powers the box down when unplugged.
- Ship mode exit (p28): adapter plug-in, QON low > tSHIPMODE, clearing BATFET_DIS, or REG_RST. A QON exit also sets EN_HIZ = 1 (9.4.4.4, p28): the input path stays high impedance until the host clears REG00[7] (or writes WD_RST and lets the watchdog expire, since EN_HIZ is reset by the watchdog). The sheet note already says firmware clears EN_HIZ after a QON wake; correct. An adapter plug-in exit does not set EN_HIZ.
- Battery over-discharge latch-off (9.3.8.4.2, p26): below VBAT_DPL_FALL (2.2 to 2.6 V, p9) the BATFET opens and only a VBUS plug-in recovers it (QON does not). Acceptable here.
- After the 10 h safety timer expires charging stops until CE or CHG_CONFIG is toggled (p24). With a 500 mA source the 2P pack needs about 9 h plus the CV tail, which fits only because the timer runs at half rate during IINDPM regulation. Firmware: handle CHRG_FAULT = 11 by toggling CHG_CONFIG, or clear EN_TIMER.

SYS rail capability (p7, p9, p26-27): in battery-only mode the BATFET is fully on (19.5 mOhm typ, 30 mOhm max over temperature), so 1.6 A costs 31 to 48 mV; continuous discharge rating 3.0 A, BATFET OCP 6 A with 100 us deglitch (p9, p12, p13), so the 1.6 A peak and the VBAT_SW inrush are fine. With USB present the converter output (max 3.25 A at SW) is shared: charge current = converter output minus system load, so during radio TX the charge current drops from 2 A to about 1.6 A with a 3 A source, and with a 500 mA source (about 0.55 A at SYS) supplement mode draws the remaining ~1.05 A from the cells through the regulated BATFET (Figure 9-9 p27: up to 4 A at 55 mV). SYS_MIN 3.5 V (typ 3.68 V in regulation, p9) only applies while an input is present: it guarantees instant-on and keeps the TPS62A02 in regulation with a dead or missing pack. On battery alone SYS = VBAT minus the BATFET drop, so the 3.3 V buck follows the cells down through its dropout below about 3.4 V; the practical end of discharge is set by firmware (MAX17048 SOC threshold), not by SYS_MIN. VINDPM default 4.5 V will throttle input current on resistive cables at 3 A (a 5 V source at 3 A over a 0.2 to 0.3 ohm cable sits right at 4.5 V); firmware can lower VINDPM to 4.2 or 4.3 V (REG06[3:0]) if full 2 A charge from 3 A bricks matters.

---

## 2. HUSB238 (U105)

**Verdict: OK** (one medium bench check and one firmware rule; no schematic change).

Symbol check (make_symbols.py vs datasheet p3 Table 1, DFN-10): 1 VIN, 2 D+, 3 D-, 4 CC1, 5 CC2, 6 SDA, 7 SCL, 8 VSET, 9 ISET, 10 GATE, 11 GND (exposed pad). All match; footprint DFN-10_L3.0-W3.0-P0.50-BL-EP2.5 has pads 1-11 with pad 11 = 2.5 x 1.5 mm exposed pad. LCSC C7471904 is HUSB238_002DD per design.md (no SOP', OTP 150/130 C, RDO mismatch = next PDO, GATE on during POR; Rev 2.5 ordering guide p15). None of the variant options matters for a 5 V only sink without a PMOS.

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| VIN | "Connect this pin to VBUS of the Type-C connector and bias via a 1 uF ceramic" (p3, p8); VIN 3 to 25 V, 30 V abs max (p6). EVB adds an optional 10 R in series (RD-2010 p13) | U105.1 on VBUS, C121 1 uF = C15849 (50 V X7R) to GND | OK | none |
| CC1/CC2 | Rd 4.6 to 5.6 k internal; dead-battery pull-down keeps Rd present unpowered and supports default/1.5 A/3 A Rp (p4, p10); pins rated 25 V (p6) | J101 A5 to U105.4, J101 B5 to U105.5, no external 5.1 k | OK | none. External Rd must indeed be absent (two Rd in parallel would be out of spec) |
| VSET / ISET | 100 uA sources; RVSET = 0 selects 5 V, RISET = 0 selects 1.25 A (Tables 5 and 6, p8-9). RDO = 5 V / 1.25 A; the chip requests the first source PDO with V <= 5 V and I >= 1.25 A (p9) | R123 0 R from both pins to GND | OK | none. Every compliant PD source offers a 5 V PDO of at least 1.5 A, so the request is always the 5 V PDO; its current is read from SRC_PDO_5V[3:0] (regs p4) or PD_STATUS0 |
| Source without PD (Type-C Rp only, 5 V / 3 A or 1.5 A) | After 1.5 s without source capabilities the chip falls back to Apple divider 3 then BC1.2 detection (p9). It detects the Rp level (VTH_DEF 0.2 V, VTH_1P5 0.66 V, VTH_3P0 1.23 V, p4). PD_STATUS1[1:0] "5V_CURRENT: 00 default, 01 1.5 A, 10 2.4 A, 11 3 A" and bit 6 ATTACH (regs p4) | No GATE FET, VBUS hard-wired, so the BQ25601 always sees vSafe5V as soon as the source detects Rd; the HUSB238 only provides information | OK | Handled at hardware level. Firmware: use PD_STATUS0/SRC_PDO_5V when PD_STATUS0[7:4] != 0, else PD_STATUS1[1:0]. Legacy USB-A bricks through A-to-C cables advertise default Rp and BC1.2 cannot run with D+/D- open, so those stay at 500 mA (conservative, acceptable) |
| GATE | "Leave this pin open if not used" (p3) | U105.10 no-connect | OK | none. No OVP/UVP cut-off of VBUS, fine because nothing above 5 V is ever requested |
| D+/D- | BC1.2 drives VDP_SRC 0.6 V and sinks 100 uA on D- during detection (p4); Apple divider uses 2.7 V thresholds; abs max 12 V (p6). The SOT33-6L variant has no D+/D- pins (p3), so unconnected is a supported state | U105.2/3 no-connect; D+/D- go only to the CH340C via the USBLC6 | OK | none. Paralleling them with the CH340C would inject 0.6 V onto D+ during enumeration and the CH340C 1.5 k D+ pull-up would look like an Apple divider, so keep them open |
| I2C while unpowered (no USB) | SDA/SCL abs max -0.3 to +6 V, not referenced to VIN (p6); I2C supply range 2.5 to 5.5 V (p4); Figures 1 and 4 show the SOC bus tied directly to a VBUS-powered HUSB238 | R125/R126 330 R in series to the 3.3 V bus | **Medium (bench check)** | The absolute-maximum wording implies no clamp diode from SDA/SCL to VIN, so an unpowered HUSB238 should not load the bus, but unpowered input leakage is not specified. Verify on the first board that SDA/SCL idle at 3.3 V with USB unplugged and that the BQ25601 (0x6B) and MAX17048 (0x36) ACK on battery. Keep the 330 R (they limit any clamp current to 10 mA) but they do not isolate the bus if a clamp exists; the fallback is to DNP R125/R126 |
| I2C levels through 330 R | VIL 0.4 V max, VIH 1.4 V min, VOL 0.4 V at 2 mA (p4) | With 4.7 k pull-ups: when the HUSB238 ACKs, I = (3.3 - 0.1)/5.03 k = 0.64 mA, chip VOL about 0.13 V, bus node about 0.34 V (ESP32 VIL 0.825 V, MAX17048 VIL 0.5 V). Master-driven lows reach the chip at about 0.1 V (no input current through 330 R). RC added by 330 R is a few ns | OK | none; 400 kHz is fine. Bus-level rise time (4.7 k x bus capacitance) is a whole-board matter |
| Exposed pad | GND, all signals referenced to it (p3) | U105.11 on GND | OK | none |
| I2C address | 0x08 (p9, regs p3) | Others: LIS3DH 0x18 (SA0 low), TCA9555 0x20, MAX17048 0x36, BQ25601 0x6B | OK | none. 0x08 lies in the I2C "Hs-mode master code" reserved range but is harmless in standard/fast mode |
| Requests above 5 V | I2C has highest priority over VSET/ISET (p9); SRC_PDO/GO_COMMAND can request 9 to 20 V (regs p7) | USBLC6 6 V, XC6206 6 V, BQ25601 ACOV 6.5 V | Medium (firmware rule) | Firmware must never write SRC_PDO/GO_COMMAND with anything but PDO_SELECT = 0001 (5 V). Document it in design.md next to "5 V only, never 9 V" |
| Supply current | 3.1 mA typ with CC attached (p4), from VBUS only | Not on the battery budget | OK | none |

---

## 3. MAX17048 (U106)

**Verdict: OK** (firmware notes only).

Symbol check (make_symbols.py vs datasheet p6, TDFN): 1 CTG, 2 CELL, 3 VDD, 4 GND, 5 ALRT, 6 QSTRT, 7 SCL, 8 SDA, EP. The symbol has 9 = EP stacked on GND; footprint TDFN-8_L2.0-W2.0-P0.50-BL-EP1.2 has pads 1-9 with pad 9 = 1.2 x 0.8 mm exposed pad. All match. The configuration equals Table 3 "1S host-side location, low-cell interrupt" (p15): VDD from the battery, ALRT to a system interrupt, QSTRT to GND.

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| VDD, CELL | VDD 2.5 to 4.5 V, bypass 0.1 uF; MAX17048 measures VCELL between VDD and GND, CELL not internally connected, connect to the positive terminal (p2, p6) | U106.2 and U106.3 on VBAT, C122 100 nF | OK | none |
| CTG / QSTRT | CTG to ground; QSTRT to GND if unused (p6) | Both on GND | OK | none |
| ALRT | Open drain, active low, needs a system pull-up (p14); latched until CONFIG.ALRT cleared (p10); alerts enabled by default: ATHD 4 % SOC, VALRT.MAX 5.1 V, VALRT.MIN 0 V, ALSC off (defaults p11-13) | PWR_INT with R105 10 k to +3V3, shared with BQ25601 INT | OK | none; see section 1 for the wire-OR behaviour |
| SDA/SCL | Up to 400 kHz; pins rated -0.3 to +5.5 V independent of VDD; VIH 1.4 V; internal 0.2 to 0.4 uA pull-downs (p2, p3, p6) | 3.3 V bus, 4.7 k pull-ups, VDD 2.5 to 4.2 V | OK | none. A bus held low > 2.5 s only sleeps the part if MODE.EnSleep = 1 (default 0), so the 3.3 V rail being off in ship mode does not disturb it |
| Exposed pad | Connect to GND (p6) | U106.9 on GND | OK | none |
| Quiescent | Hibernate 3 uA typ / 5 uA max with VRESET.Dis = 1, 4 uA typ with the reset comparator enabled (default); active 23 uA typ / 40 max; sleep < 1 uA (p2). Hibernate is entered automatically when CRATE < HibThr (default 26.6 %/h) for 6 min (p9, p12) | Default configuration | OK | none; in deep sleep the pack discharges at about 0.003 %/h, so the gauge sits in hibernate at about 4 uA |
| VRESET | Default 3.0 V (0x96, p13); "for captive batteries set to 2.5 V"; a dip below and recovery above VRESET resets the IC (POR includes quick-start, model reload needed, RI set) | n/a | Low (firmware) | Set VRESET to 2.5 V (VRESET[7:1] = 62 or 63) at boot; a 1.6 A pulse on a nearly empty pack (about 100 mOhm of cell + protector + contacts = 160 mV) could otherwise cross 3.0 V and reset the SOC estimate |
| Missing parts | "Only one external component" (p1); RCOMP temperature compensation is expected from the host at least once per minute (p8); the default ROM model "performs well for some batteries" (p7) | Nothing missing | OK (low) | none in hardware. Firmware: use a board temperature (LIS3DH or ESP32) for RCOMP; accept the default model or obtain a custom one for the chosen 18650 |

---

## 4. USB-C input (J101, D101)

**Verdict: OK.**

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| Connector rating | HRO TYPE-C-31-M-12 drawing: current rating 5 A, voltage rating 20 V, 16 pins, 10 000 cycles | J101 with VBUS on A4/A9/B4/B9 and GND on A1/A12/B1/B12 all connected, shell to GND | OK | none; 3 A is 60 % of rating and all four VBUS pins are used |
| CC routing | Sink must present Rd on both CC pins (HUSB238 p10) | A5 to CC1, B5 to CC2, no other loads, no external Rd | OK | none. The optional 330 pF/TVS on CC from the EVB are not required |
| D+/D- | Both rows joined for a reversible plug | A7/B7 to D101 I/O1, A6/B6 to D101 I/O2, then to the CH340C | OK | none |
| SBU | unused | A8/B8 no-connect | OK | none |
| USBLC6-2SC6 on VBUS | VBUS to GND breakdown 6 V min at 1 mA, leakage 150 nA at 5.25 V, IEC 61000-4-2 level 4 (p1-2); it is a shunt clamp with no series element | D101.5 on VBUS, D101.2 GND | OK | none for a 5 V / 3 A source (no load current flows through the clamp). It remains sensible only while VBUS stays at 5 V, which the VSET = 0 R strap and the firmware rule in section 2 guarantee |
| Layout | Clamp tracks from VBUS, I/O and GND as short as possible (USBLC6 p4-5) | n/a | Low | Place D101 at the receptacle |

---

## 5. Two cells in parallel through DW01A + FS8205A (BT101, BT102, U102, Q101)

**Verdict: OK.**

Wiring check against the DW01A typical circuit (p3): R106 100 R VBAT to VCC with C103 100 nF VCC to BAT- (cell negative); DW01A GND (pin 6) on BAT-; R107 1 k from VM/CS (pin 2) to PCB GND (load side); OD (pin 1) to Q101 G1 whose S1 is BAT- (discharge FET on the cell side); OC (pin 3) to Q101 G2 whose S2 is GND (charge FET on the load side); common drains tied (Q101 pins 2 and 5). All correct. TD (pin 4) is a test pin and is left open as in the typical circuit.

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| Over-current threshold | VEDI 130 to 170 mV across the two FETs, delay 7 ms typ / 20 ms max; short circuit 0.82 to 1.75 V, 400 to 600 us (DW01A p4). FS8205A RDS(on) per FET 18 mOhm typ / 25 max at VGS 4.5 V, 23 / 32 at 2.5 V (FS8205A p2); the gate drive equals the cell voltage | Discharge trip: 150 mV / 36 mOhm = 4.2 A typ at 4.2 V, 3.3 A typ at 2.5 V; worst case (130 mV, 2 x 32 mOhm) 2.0 A at a 2.5 V cell, 2.3 A at 3.4 V, 2.6 A at 4.2 V. Charging 2 A and the 1.6 A load never add at the protector: with USB present the load is fed from VBUS and the pack sees at most 2 A charge (VM negative, no discharge OCP) or, in supplement mode, ISYS minus the input share (about 1.1 A). Maximum discharge is the 1.6 A peak on battery | OK | none. The VBAT_SW soft start (10 k + 100 nF gate, 480 uF load) adds a 1 to 2 A inrush for 1 to 2 ms, inside the 7 ms OCP delay and the BQ25601 6 A / 100 us BATFET limit. Short-circuit trip at about 38 A |
| Charge-side over-current | DW01A has no charge OCP; 2 A x 36 mOhm = 72 mV on VM | n/a | OK | none |
| 2.5 V UVLO vs BQ25601 | DW01A VOD 2.4 to 2.6 V, delay 55 to 200 ms, release VODR 2.8 to 3.0 V (p4). Timing diagram p6: in over-discharge, OD returns high as soon as a charger is detected on VM (VM pulled below VSS through the discharge FET body diode), before the cell reaches VODR. BQ25601 depletion threshold 2.2 to 2.6 V (p9); SYS_MIN only applies with VBUS present | Both cut-offs sit in the same 2.4 to 2.6 V band; either can fire first | OK | none. If the DW01A fires first the pack terminals collapse to about 0 V and the BQ25601 loses BAT; on the next USB plug-in SYS starts at 3.5 V from VBUS (instant-on), the charger pushes ISHORT/IPRECHG through the FS8205A body diode (Vf up to 1.2 V at 4 A), VM goes negative, the DW01A closes the discharge FET within its detect delay and normal charging resumes. The body-diode dissipation at 2 A (about 2 W in a SOT-23-6 rated 1.5 W) lasts only milliseconds. If the BQ25601 fires first a USB plug-in is required (p26), the same user action. SYS_MIN and supplement mode are unaffected: the DW01A never trips while VM is negative (charging), and supplement mode discharges the pack only when the source is weaker than the load, at currents well below the OCP |
| 2P pairing | design.md: same type and age, no balancing | Direct parallel on VBAT and BAT- | OK | none (standard for matched cells in one holder pair) |
| Gauge behind the protector | MAX17048 VDD = pack + terminal; after a DW01A trip VDD is about 0 V | n/a | OK | The gauge PORs on recovery (RI = 1, p14); firmware reloads RCOMP/VRESET when RI is set |

---

## 6. Sleep current of the new block on battery

**Verdict: change needed** (documentation: the 80 uA figure in design.md uses 25 uA for the BQ25601; the datasheet says 58 uA typical).

| Part | Datasheet says | design.md assumes | Severity | Recommended fix |
|---|---|---|---|---|
| BQ25601, battery only, BATFET on | IBAT (BAT, SW, SYS) with no VBUS, I2C idle, BATFET enabled: **58 uA typ, 85 uA max** at VBAT 4.5 V, TJ < 85 C (p8). REGN is off in this state, so the TS divider draws nothing (p18) | 25 uA | **Medium (doc)** | Update the power budget: BQ25601 58 uA typ. Deep sleep becomes about 115 uA typ (up to about 150 uA max) instead of 80 uA. On 3500 usable mAh that is still 3 to 4 years; no hardware change |
| BQ25601, ship mode (BATFET off) | 17 uA typ, 33 uA max (p8) | "a few uA" | Low (doc) | Ship mode total about 24 uA typ (17 + gauge 4 + protector 3), 45 uA max |
| MAX17048 | Hibernate 4 uA typ with the default reset comparator, 3 uA typ / 5 max with VRESET.Dis = 1 (p2) | 3 uA | OK | Optionally set VRESET.Dis = 1 (saves about 0.5 uA; the fast battery-swap comparator is irrelevant for a captive pack) |
| DW01A | 3 uA typ, 6 uA max at 3.6 V (p4) | 3 uA | OK | none |
| FS8205A | IDSS 1 uA max per FET at 20 V (p2), negligible at 4 V | not listed | OK | none |
| HUSB238 | Powered from VBUS only; dead-battery Rd is a passive pull-down on CC (p10); nothing drawn from VBAT | 0 | OK | none (see section 2 for the unpowered I2C leakage check) |
| Divider currents | R103 (PSEL) and the TS divider are fed from VBUS/REGN, absent on battery; R104 carries nothing with STAT high; R105 carries nothing with PWR_INT high | not listed | OK | none |
| New block total | 58 + 4 + 3 = 65 uA typ, about 96 uA max | 31 uA | Medium (doc) | as above |

---

## Summary of recommended changes (most important first)

1. **High, schematic:** the charger inductor and the TPS62A02 buck inductor are both `L101` (`tools/power_block.py` line 103 vs `tools/gen_schematic.py` line 44); the netlist merges them into one component whose pins sit on the charger SW node, the buck SW node, VSYS and +3V3. Rename the charger inductor to L103, regenerate, re-run ERC and the netlist export, update design.md section 4 (3x C42193), and add a duplicate-reference assertion to the generator.
2. **Medium, documentation:** BQ25601 battery-only quiescent is 58 uA typ / 85 uA max (SLUSCK5A p8), not 25 uA. Deep sleep is about 115 uA typ (up to about 150 uA), ship mode about 24 uA rather than "a few uA". No hardware change needed.
3. **Medium, bench check:** confirm that the unpowered HUSB238 does not load SDA/SCL (abs max +6 V independent of VIN suggests no clamp to VIN, but leakage is unspecified). Keep R125/R126 330 R; fallback is to DNP them.
4. **Medium, firmware rule to document:** never write HUSB238 SRC_PDO/GO_COMMAND for anything but the 5 V PDO (I2C overrides VSET/ISET); the USBLC6 and XC6206 are 6 V parts and the BQ25601 OVP is 6.5 V.
5. **Low, schematic option:** R104 2.2 k gives only about 0.9 mA through the CHRG LED; 1 k (about 1.9 mA, max 2.2 mA at VSYSMAX) is still far below the 6 mA STAT limit.
6. **Low, schematic option:** PWR_INT could go to the now-free GPIO39 (RTC wake, direct edge interrupt) instead of TCA9555 P17, since the BQ25601 INT is a 256 us pulse and the MAX17048 ALRT is a latched level.
7. **Low, firmware notes:** clear EN_HIZ after a QON wake (already in the sheet note); handle CHRG_FAULT = 11 (10 h safety timer, relevant with 500 mA sources); mask VINDPM/IINDPM interrupts (REG0A) if pulses become a nuisance; set MAX17048 VRESET to 2.5 V for the captive pack and reload RCOMP after RI; read PD_STATUS1[1:0] for non-PD Type-C sources; optionally lower VINDPM from 4.5 V to about 4.3 V for full 2 A charging on longer cables.
8. **Low, design option:** R101/R102 can later host the datasheet NTC network (5.23 k / 30.9 k + 103AT) if a thermistor is added to a holder; today the pack charges at full 4.208 V / 2.04 A at any temperature because TS = 50 % of REGN sits in the normal JEITA window (T2 68 % to T3 44.7 %).

Everything else checked in sections 1 to 5 matches the datasheets: pin numbers and footprint pads of U101, U105 and U106; VAC tie; 1 uF 50 V on VBUS; 2x 10 uF 25 V on PMID; 4.7 uF 10 V on REGN; 47 nF BTST; 2x 10 uF SYS; 10 uF BAT; 1 uH 5.7 A inductor; PSEL 10 k to VBUS giving the 500 mA default; CE low; QON button on the internal 200 k; STAT LED sink current; INT and ALRT pull-up; PG open; NC pins floating; register defaults 500 mA / 2.04 A / 4.208 V / 40 s; ship-mode entry and exit; SYS capability for 1.6 A with supplement; HUSB238 VIN 1 uF, internal Rd, 0 R VSET/ISET = 5 V 1.25 A, GATE and D+/D- open, pad grounded, address map free of conflicts; MAX17048 wiring; USB-C 5 A connector with all VBUS/GND pins used; USBLC6 as a shunt clamp; DW01A/FS8205A wiring, OCP 2.0 to 4.2 A versus a 1.6 A maximum discharge, and 2.5 V cut-off recovery through the charger.

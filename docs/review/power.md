# Power sheet review against manufacturer datasheets

Project: LazerGamebox, sheet `power` (plus U202 on `mcu`). Connectivity taken from `hardware/reports/netlist.xml`,
values from the same netlist and `tools/gen_schematic.py::gen_power`. Datasheets downloaded 2026-09-29 (LCSC copies via
wmsc.lcsc.com, TI copies from ti.com); page numbers refer to those PDFs.

Pinout cross-check (all pass): TP4056 ESOP-8, DW01A SOT-23-6, FS8205A SOT-23-6, TPS62A02 DRL, TPS61023 DRL, XC6206 SOT-23,
USBLC6-2SC6, AO3401A SOT-23 and the HRO Type-C pin table all match the pin numbers used in the netlist.

---

## U101 TP4056-42-ESOP8 charger (C16581)

Verdict: **change needed** (value and thermal notes; connectivity is correct).

Netlist: VCC(4)=VBUS, CE(8)=VBUS, GND(3)+EP(9)=GND, BAT(5)=VBAT, PROG(2)=R103 1.2k to GND, TEMP(1)=GND,
CHRG(7)/STDBY(6)=LEDs D102/D103 via R104/R105 1k from VBUS, C101 10uF on VBUS, C102 10uF on VBAT.

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| PROG value vs. 1 A target | IBAT = 1100 / RPROG; table: 1.2k = 900 mA, 1.1k = 1000 mA; "up to 1000 mA" (p.2, p.5 VPROG row, p.9 table) | R103 = 1.2k, texts say "1 A" | low | Either change R103 to **1.1k** (JLC preferred part C22764, no fee) for 1 A, or keep 1.2k and correct the note to "0.9 A". Termination then 100/90 mA |
| Power dissipation at 1 A from 5 V | PD = (VCC - VBAT) x IBAT; thermal regulation starts when TJ = 145 C; example uses theta-JA 125 C/W (p.10, p.12) | 1.8 to 2 W at a 3.0 V cell, 1.2 W at 3.7 V, no heat path defined yet | medium | Plan the layout for it: EP (pin 9) on a solid GND pour with 6+ thermal vias to the other side, 300 to 500 mm2 copper. Even so, expect the charger to throttle toward 0.6 to 0.7 A for the first part of the CC phase at warm ambient. Optional per p.12 Fig.3: 0.4 to 0.5 ohm 1206 in series with U101 VCC/CE only (not the rest of VBUS) to move heat out of the chip |
| Loads on the BAT pin while charging | "Once the average charge current drops below 1/10 ... the TP4056 ceases to provide current through BAT. In this state all loads on the BAT pin must be supplied by the battery" (p.9); termination watches PROG current (p.9) | Boost U104 VIN, VBAT_SW switch Q107 and the DNP SIM7080G all hang on VBAT, not on VSYS. With the radio, backlight or LEDs on, the charger sees their current as charge current: no C/10 termination, STDBY never lights, cell floats at 4.2 V, and after termination those loads run the cell down while USB is plugged in | medium | Move the boost input (U104 VIN, L102 pin 1, C109, C110) and the source of Q107 (and R119 pin 1) from VBAT to **VSYS**. Then everything except the DNP cellular module runs from USB when present, which is what section 2 of design.md claims. Consequences: VBAT_SW and the boost input become 4.5 to 4.9 V on USB (WS2812B, NS4150B, IRM-H638T, backlight resistor all fine, boost enters pass-through mode p.10 of TPS61023), and all battery current then flows through Q102 (see AO3401A section, acceptable) |
| USB source current | Charger is "designed to work within USB power specifications" (p.2) but draws whatever PROG sets | 0.9 to 1 A charge + up to ~0.5 A system through SS34 = 1.3 to 1.5 A from VBUS, no CC sensing (5.1k Rd only) | low | Acceptable with any modern charger (1.5 A or 3 A Rp). Note in docs that a USB 2.0 port (500 mA) will sag; TP4056 UVLO at 3.7 V (p.5) makes this self-limiting, not destructive |
| CE handling | Logic high = enabled, TTL/CMOS level, abs max 10 V (p.2, p.7); typical circuits tie CE to VCC (p.3) | CE tied to VBUS | OK | none |
| TEMP handling | "The temperature sense function can be disabled by grounding the TEMP pin" (p.7) | TEMP to GND | OK | none |
| Input / BAT capacitors | 10 uF on VCC and 10 uF on BAT in every typical circuit (p.3); "capacitance at VCC and BAT as close to TP4056 as possible" (p.13) | C101 10uF VBUS, C102 10uF VBAT | OK | layout: both within a few mm of pins 4 and 5 |
| Ceramic input cap hot-plug ringing | "Adding a 1.5 ohm resistor in series with a ceramic capacitor will minimize start-up voltage transients" (p.13); VCC abs max 8 V (p.2) | 11 uF ceramic straight on VBUS | low | Optional. The USBLC6 VBUS clamp (6 V) already limits the overshoot; leave as is |
| Status LEDs | Open drain, 0.3 V low at 5 mA (p.5), typical circuits use 1k from VCC (p.3) | 1k from VBUS, about 3 mA | OK | none |
| PROG layout | "RPROG at PROG pin should be as close to TP4056 as possible ... parasitic capacitance kept small" (p.13) | n/a | low | layout note for R103 |

## U102 DW01A protection (C351410)

Verdict: **OK** (one text correction, one margin note).

Netlist: VCC(5) via R106 100R from VBAT with C103 100nF to BAT-, GND(6)=BAT-, VM/CS(2) via R107 1k to GND (P-), OD(1)=Q101 G1,
OC(3)=Q101 G2, TD(4) NC. Matches the typical application circuit exactly (p.3: R1 100 ohm, C1 0.1 uF, R2 1 kohm).

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| Thresholds in schematic note | VODP 2.50 V, VOCP 4.30 V +/-50 mV, VOI1 150 +/-20 mV (p.2, p.4) | Note says "2.4 V under-voltage, 4.25 V over-voltage"; design.md says "2.5 V UVLO, 4.25 V OVP" | low | Fix the text in gen_power (sh.text near U102) and design.md section 2 to 2.5 V / 4.3 V |
| Over-current trip point | VEDI 130 to 170 mV across the FET pair (p.4); OD drives gates to VCC - 0.4 V (p.4) | FS8205A pair 36 mOhm typ to 64 mOhm max (Vgs 2.5 V) so trip = 2.0 A (worst) to 4.2 A (typ), delay 20 ms, short-circuit level 0.82 V min with sub-ms delay (p.4) | low | Fine for the 1.6 A peak budget. If the SIM7080G is ever fitted its 2 A bursts stack on top and can trip at a low, cold cell. R107 is only the VM sense resistor, it does not set the threshold |
| Charge current through the FETs | No charge over-current detection, FETs rated 6 A | 0.9 to 1 A charge | OK | none |
| Abs max on VM | VDD-24 to VDD+0.3 V (p.3) | Only ever reaches -5 V (charger with tripped protector) | OK | none |
| Quiescent | 3 uA typ (p.4) | budgeted 3 uA | OK | none |

## Q101 FS8205A dual N-MOSFET (C908265)

Verdict: **OK**.

Netlist: S1(1)=BAT-, G1(6)=OD, D1/D2(2,5) joined only to each other, G2(4)=OC, S2(3)=GND. Same as the DW01A figure (M1 on the cell
side driven by OD, M2 on the P- side driven by OC, p.3 DW01A).

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| Pin assignment | S1, D1/D2, S2 on pins 1-3, G1, D1/D2, G2 on pins 6-4 (marking drawing p.1) | custom symbol uses exactly that | OK | none |
| Ratings | VDS 20 V, VGS +/-12 V, ID 6 A, PD 1.5 W (p.2) | 4.2 V, gate 4.2 V, 1.6 A peak | OK | none |
| RDS(on) | 25 mOhm max at 4.5 V, 32 mOhm max at 2.5 V per FET (p.2) | 1.6 A x 64 mOhm = 0.1 V drop, 0.16 W at the cutoff voltage | OK | fine |
| Body diode | 1.2 V max at 4 A (p.2) | carries charge current only while the protector is tripped | OK | none |

## U103 TPS62A02DRLR buck 3.3 V (C5350187)

Verdict: **OK, small optional changes**.

Netlist: VIN(3)=VSYS, EN(4)=VSYS, SW(2)=L101 1uH to +3V3, FB(5)=R111 100k / R112 22k, PG(6) NC, GND(1)=GND, C105 10uF + C106 100nF
on VSYS, C107 + C108 22uF on +3V3.

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| Output voltage | VFB 0.6 V; R1 = R2 x (VOUT/0.6 - 1); "R2 must not be higher than 100 kOhm" (p.5, p.11) | 0.6 x (1 + 100/22) = 3.327 V, R2 = 22k | OK | none required |
| Divider quiescent | Only the 100k upper bound is given (p.11); Iq 23 uA (p.5) | 3.3 V / 122k = 27 uA, more than the converter's own Iq and not in the sleep budget of design.md | low | Optional: R111 150k (C22807), R112 33k (C4216) gives 3.33 V at 18 uA. (470k/100k would be 3.42 V, too close to the ESP32 3.6 V max in PSM) |
| Inductor | 1 uH effective, standard for all rows of Table 9-3 (p.4, p.11); peak limit 2.7 to 3.4 A (p.5) | L101 1 uH SWPA4030S1R0, Isat 5.7 A | OK | none |
| Output capacitance | 10 uF min for VOUT >= 1.8 V, 22 uF recommended, 2 x 22 uF proven; "designed to operate with 10 uF to 47 uF" (p.4, p.11) | 44 uF at the buck plus 10 uF (C201), 10 uF (C207), 10 uF (C403) and 100 nF x5 elsewhere on +3V3: ~75 uF nominal, roughly 45 to 55 uF after DC bias | low | Acceptable; if you want to stay inside the characterised range make C108 10uF (or delete it) since the module caps already provide the bulk |
| Input capacitance | 4.7 uF sufficient, close to VIN and GND (p.11, p.14) | 10 uF + 100 nF | OK | place C105 directly at pins 3 and 1 |
| EN | "Do not leave the pin floating" (p.3); VEN rising 1.2 V, abs max 6 V (p.4, p.5) | EN tied to VSYS (max ~4.9 V from a 5.25 V USB source) | OK | none |
| PG | "If unused, leave the pin open or connect to GND" (p.3) | NC | OK | none |
| Dropout / 100 % mode | VIN(min) = VOUT + IOUT x (RDSON 100 mOhm + DCR) (p.8) | Rail follows the cell below ~3.4 V (plus Q102 drop) | low | Informational: at a 3.0 V cell the rail is ~2.9 V, still above the ESP32 minimum. Radio is on the boost so unaffected |
| Soft start / thermal | 1 ms internal soft start (p.5); RthJA 157 C/W (p.5) | 0.5 A at ~90 % gives ~0.2 W, +30 C | OK | none |
| Layout | Caps and inductor close, FB trace away from SW, common ground (p.14) | n/a | low | follow Figure 11-1 |

## U104 TPS61023DRLR boost 4.6 V for the radio (C919459)

Verdict: **change needed**.

Netlist: VIN(3)=VBAT, SW(5)=L102 1uH from VBAT, VOUT(6)=RADIO_4V5, FB(1)=R113 220k / R114 33k, EN(2)=RADIO_EN (only other node:
U205 P00), GND(4)=GND, C109 22uF + C110 10uF on VBAT, C111 + C112 22uF on RADIO_4V5; on the radio sheet C303 470uF, C304 10uF,
C305 100nF also sit on RADIO_4V5.

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| EN default state | VEN_H 1.2 V, VEN_L 0.35 V min (p.5); EN high = enabled; "when the voltage at EN is below 0.4 V the device turns into shutdown" (p.9) | RADIO_EN has no pull-down. The TCA9555 has 100 kOhm internal pull-ups on every I/O and all ports come up as inputs (TI SCPS200E, Description p.1, block diagram p.17, Configuration register default = 1). So at power-up, in the bootloader, or after a firmware crash, RADIO_EN sits at 3.3 V through 100k and the radio boost is ON. The other three enables survive this only because they have 10k pull-downs on the 2N7002 gates | **high** | Add **R121 4.7k** (C23162) from RADIO_EN to GND next to U104. 100k/4.7k gives 0.15 V, safely below the 0.35 V minimum low threshold; 10k would give 0.30 V which is too close. Costs 0.7 mA only while the radio is on |
| Output voltage | VREF 595 mV (580 to 610), VOUT = VREF x (1 + R1/R2) (p.5, p.13) | 0.595 x (1 + 220/33) = 4.56 V (4.45 to 4.68 V worst case), PFM adds up to 1 % (p.11) | OK | Within the SA818S-U 3.3 to 5.5 V range. Correct the note "0.6 V x ..." to 0.595 V if you care; net name RADIO_4V5 is fine |
| R2 upper bound | R2 < 300 kOhm for accuracy (p.13) | R114 33k | OK | none |
| Output capacitance and loop | Effective COUT 4 to 1000 uF allowed (p.4, p.14); "for large output capacitance more than 40 uF, TI recommends a feedforward capacitor to set the zero frequency to 1 kHz", C3 = 1 / (2 pi fFFZ R1) (p.15, eq. 10) | ~520 uF nominal on RADIO_4V5 (44 + 10 + 470 uF), no feedforward cap | medium | Add **C113 1nF** (C1588) in parallel with R113 (VOUT to FB): fz = 1 / (2 pi x 220k x 1 nF) = 720 Hz, right where TI asks. 680 pF would be exact but 1 nF is a Basic part |
| Input capacitance | 10 uF sufficient, close to VIN and GND; more is fine (p.15, p.18) | 22 uF + 10 uF, next to C102 of the charger | OK | keep them at pins 3 and 4; if the input moves to VSYS (charger section) move C109/C110 with it |
| Inductor | 0.37 to 2.9 uH, 1 uH typical; Isat above peak current; Table 8-2 lists 1 uH / 7 to 9.6 A parts (p.4, p.13, p.14) | 1 uH SWPA4030S1R0, Isat 5.7 A. Worst case (2.5 V cell, 4.6 V, 0.75 A, 90 %): IL_DC 1.5 A, ripple 1.3 A p-p, peak 2.2 A | OK | none; valley limit 2.7 A min (p.5) is not reached |
| True disconnect | "During shutdown, the TPS61023 is completely disconnected from the input power", 0.1 uA (p.1, p.9); VOUT leakage 1 to 3 uA (p.5) | EN low = radio unpowered, no separate load switch | OK | design intent holds once the pull-down above is added |
| Soft start / inrush | Pre-charge 350 mA below 0.4 V, then 2 ohm load capability, then switching (p.9); 700 us to 5 V with 10 uF (p.5) | 520 uF to charge, so expect ~5 to 10 ms from EN to 4.6 V | low | firmware: wait ~20 ms after RADIO_EN before talking to the module |
| Pass-through | When VIN > VOUT the high-side PMOS is fully on (p.10) | Never happens from a 4.2 V cell; would happen on USB if the input moves to VSYS (4.5 to 4.9 V), giving the radio 4.4 to 4.8 V, fine | OK | none |
| Thermal at 750 mA TX | RthJA 142.7 C/W standard board, 91.4 on the EVM (p.4); TSD 150 C (p.5) | 0.75 A at 4.6 V from a 3.0 V cell: ~0.38 W loss, +35 to +55 C | low | Give the GND pin and SW/VOUT pads generous copper; TX is duty-limited so this is acceptable |
| Layout | Minimise SW loop, input cap at VIN and GND, ground plane under the converter (p.18) | n/a | low | follow section 10.2 |

## U202 XC6206P332MR LDO for the CH340C (C5446)

Verdict: **OK** (one system-level note).

Netlist: VIN(3)=VBUS, VOUT(2)=CH_3V3 (U203 VCC + V3, C204 1uF), VSS(1)=GND, C205 1uF on VBUS.

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| Capacitors | Typical circuit: CIN 1.0 uF ceramic, CL 1.0 uF ceramic (p.1); "compatible with low ESR ceramic capacitors" (p.1) | C205 1uF in, C204 1uF out | OK | none |
| Ratings | VIN abs max 7 V, Pd 250 mW in SOT-23, IOUT = Pd / (VIN - VOUT) (p.3); 3.3 V: IOUTMAX 200 mA min, dropout 250 mV typ at 100 mA (p.5) | 5 V in, CH340C ~15 mA, 25 mW | OK | none |
| Pinout | SOT-23: 1 VSS, 2 VOUT, 3 VIN (p.2) | matches | OK | none |
| Back-powering when VBUS is absent | Not in this datasheet; consequence of the separate-rail choice | With USB unplugged CH_3V3 is 0 V but ESP32 GPIO1 (U0TXD) idles high into the unpowered CH340C RXD pin, which will forward-bias the CH340C's input clamp and lift CH_3V3 to ~2.6 V through C204 (a few mA wasted whenever the ESP32 is awake, CH340C in an undefined state) | medium | Add a 1k series resistor in U0TXD (ESP32 TX to CH340C RXD) and 1k in U0RXD on the mcu sheet, or verify with the CH340C datasheet that its I/O pins tolerate voltage with VCC = 0 (they are not specified to). 1k still allows 921600 baud |

## D101 USBLC6-2SC6 ESD (C7519)

Verdict: **OK**.

Netlist: I/O1(1)=J101 D- pair, I/O1(6)=USB_D- to U203, I/O2(3)=J101 D+ pair, I/O2(4)=USB_D+ to U203, VBUS(5)=VBUS, GND(2)=GND.

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| Orientation / flow-through | Pins 1 and 6 are the same I/O1 node, 3 and 4 the same I/O2 node, 5 VBUS, 2 GND (p.1 functional diagram) | Connector side on 1/3, CH340C side on 6/4, VBUS to 5, GND to 2 | OK | none |
| VBUS clamp | VBR VBUS to GND 6 V at 1 mA, leakage 150 nA at 5.25 V (p.2) | VBUS 5 V | OK | also protects the TP4056 (8 V abs max) and XC6206 (7 V) from hot-plug overshoot |
| Layout | Tracks from data lines to I/O, VBUS to pin 5 and GND to plane "as short as possible" (p.5, Figure 7) | n/a | low | place D101 right behind J101, GND pin straight into the plane |
| Series resistors | none required | design.md mentions "22 ohm series on D+/D-" but the netlist has none; the CH340C does not need them | low | update design.md section 5 (mcu) |

## Q102 to Q107 AO3401A P-MOSFETs (C15127)

Verdict: **change needed** (Q102 turn-over timing and Q107 inrush; the switches themselves are fine).

Netlist: Q102 D=VBAT, S=VSYS, G=VBUS with R108 100k to GND. Q103/Q105 S=+3V3, D=GPS_3V3/LCD_3V3; Q107 S=VBAT, D=VBAT_SW; each
gate has 100k to source (R115/R117/R119) and a 2N7002 (Q104/Q106/Q108) to GND with 10k gate pull-down (R116/R118/R120).

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| Ratings | VDS -30 V, VGS +/-12 V, ID -4 A, RthJA 125 C/W steady state (p.1) | max Vds 5 V, Vgs -4.2 to +2.5 V | OK | none |
| Gate drive of the load switches | VGS(th) -0.5 to -1.3 V; RDS(on) 60 mOhm max at -4.5 V, 85 mOhm max at -2.5 V (p.2, Fig.5 p.3) | Q103/Q105: Vgs -3.3 V, ~70 mOhm, loads < 50 mA, drop < 4 mV. Q107: Vgs -2.5 to -4.2 V, worst 85 mOhm at 0.75 A = 64 mV, 48 mW | OK | none |
| Turn-off of the load switches | Ciss 645 pF (p.2) | 100k pull-up: ~65 us to open, fine | OK | none |
| Q107 inrush into VBAT_SW | Body/ratings only; system effect | Q108 pulls the gate hard low, so the 470 uF C505 + 10 uF are charged through ~0.3 ohm (AO3401A + FS8205A + ESR): ~10 A for a few hundred us. Below the DW01A short-circuit level and shorter than its 20 ms over-current delay, but it dips VBAT while the radio boost may be running | low | Add a soft start: **R122 10k** between Q108 drain and Q107 gate and **C114 100nF** from Q107 gate to source (tau 1 ms, inrush ~1 A). Not needed on Q103/Q105 (10 uF loads) |
| Q102 load sharing, USB present | Vgs must stay above -0.5 V to be off (p.2); body diode VSD -0.7 to -1 V (p.2) | Gate 5 V, source 4.5 to 4.7 V, Vgs = +0.3 to +0.5 V: off, body diode reverse biased. Correct | OK | none |
| Q102 on battery | RDS(on) 85 mOhm max at -2.5 V (p.2) | Vgs = -VBAT. Today only the buck current (< 0.5 A) flows, 40 mV. If the boost and VBAT_SW move to VSYS (charger section) the peak is ~1.6 A: 0.14 V drop, 0.22 W peak, +27 C in bursts, still within 4 A / 1 W (t <= 10 s) (p.1) | OK | acceptable either way |
| Q102 turn-over when USB is unplugged | VGS(th) as low as -1.3 V (p.2) | Gate only falls as fast as R108 100k plus the VBUS loads discharge C101 + C205 (11 uF). With the charger asleep the residual VBUS load is ~0.1 to 0.3 mA (R108, TP4056 shutdown, suspended CH340C), so the gate takes tens of ms to fall 1.3 V below VBAT. During that time VSYS is fed only through the Q102 body diode at VBAT - 0.7 to 1 V: from a 3.6 V cell the 3V3 rail sags to ~2.8 V, from a 3.3 V cell to ~2.4 V, an ESP32 brown-out | medium | Lower **R108 to 4.7k** (1 mA on USB, harmless): the interval drops to about 10 ms and VSYS ripples less. If that is still too long, add a 2N7002 whose gate is VBUS-driven to actively pull Q102's gate low, but try the resistor first |
| Pull-down location | design.md says "100 k to source" | R108 is gate to GND | OK | design.md text only; gate to GND is the AN1149-style connection and what the circuit needs |

## D104 SS34 Schottky, VBUS to VSYS (C8678)

Verdict: **OK**.

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| Current | IF(AV) 3 A, IFSM 80 A (p.1) | Carries only the buck input (and, if moved, the boost input): <= 1.5 A peak. The 1 A charger takes VBUS directly, not through D104 | OK | none |
| Forward drop | VF 0.55 V max at 3 A for SS32 to SS35 (p.1, Fig.3 p.2) | ~0.35 to 0.4 V at 0.5 A, VSYS 4.5 to 4.7 V on USB | OK | none |
| Reverse leakage | 0.5 mA max at rated 40 V and 25 C, much less at 4 V (p.1, Fig.2 p.2) | Battery-side leakage into VBUS is absorbed by R108 | OK | none |
| Thermal | RthJA 70 C/W on 5 x 5 mm pads (p.1) | 0.5 W worst case, +35 C | OK | give the SMA pads the 5 x 5 mm copper |

## J101 TYPE-C-31-M-12 USB-C receptacle (C165948)

Verdict: **OK**.

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| Pin table | A1/A12/B1/B12 GND, A4/A9/B4/B9 VBUS, A5 CC1, B5 CC2, A6/B6 DP, A7/B7 DN, A8/B8 SBU (drawing sheet 1, pin table) | All four VBUS joined, all four GND joined, D+ pair joined, D- pair joined, CC1 to R101 5.1k, CC2 to R102 5.1k, SBU NC, shell to GND | OK | none |
| CC pull-downs | USB-C sink: Rd 5.1k +/-10 % on each CC pin, never tied together | Two separate 5.1k (C23186) | OK | none |
| Ratings | 5 A, 20 V (drawing note 4) | 5 V, < 2 A | OK | none |
| Shield / GND | Shell pins separate from signal GND on the drawing | SHIELD tied straight to GND | OK | direct tie is fine for a handheld; if EMC testing complains add a 1 MOhm + 1 nF footprint in the shell path (DNP) |
| Mechanical | Board-edge layout 0.9 mm setback, four 0.6 mm and two 0.5 mm plated holes (drawing) | KiCad HRO footprint | OK | keep the "PCB EDGE" line at the connector face |

---

## Summary of recommended changes (most important first)

1. **R121 4.7k pull-down on RADIO_EN** at U104 EN. Without it the TCA9555's internal 100k pull-ups turn the radio boost on at every power-up and whenever firmware is not running (TPS61023 p.5, p.9; TCA9555 SCPS200E p.1, p.17).
2. **C113 1nF across R113** (U104 VOUT to FB): feedforward cap TI requires when the boost's output capacitance exceeds 40 uF, and RADIO_4V5 carries about 520 uF (TPS61023 p.15, eq. 10).
3. **Move the boost input (U104 VIN, L102, C109, C110) and the Q107/R119 source from VBAT to VSYS** so the radio, amp, LEDs and backlight run from USB while charging; otherwise the TP4056 never terminates and the cell floats at 4.2 V under those loads (TP4056 p.9).
4. **R108 100k to 4.7k** on the Q102 gate so the load-share FET turns on within ~10 ms of unplugging USB instead of tens of ms of body-diode operation that browns out the 3V3 rail at cell voltages below ~3.6 V (AO3401A p.2).
5. **TP4056 thermal**: at 1 A from 5 V into a 3.0 to 3.7 V cell the chip dissipates 1.2 to 2 W and will thermally throttle unless the EP sits on a large via-stitched GND pour (TP4056 p.10, p.12, p.13). Optionally a 0.4 to 0.5 ohm resistor in series with U101 VCC/CE only.
6. **R103 1.2k to 1.1k (C22764)** if 1 A is really wanted; 1.2k programs about 0.9 A (TP4056 p.9 table). Otherwise fix the "1 A" notes.
7. **Back-powering of the CH340C**: add 1k series resistors in U0TXD and U0RXD (mcu sheet) so the ESP32 TX cannot lift CH_3V3 through the unpowered CH340C when USB is absent.
8. **Q107 soft start**: R122 10k in series with the gate and C114 100nF gate to source, to tame the ~10 A inrush into the 470 uF on VBAT_SW.
9. Optional, low: R111/R112 150k/33k (3.33 V, saves 9 uA of sleep current, TPS62A02 p.11 allows R2 <= 100k); C108 to 10uF to keep total +3V3 capacitance inside the 47 uF characterised range; fix the DW01A note to 2.5 V / 4.3 V; remove the "22 ohm series" and "100 k to source" wording from design.md.

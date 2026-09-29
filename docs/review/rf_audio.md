# RF, GNSS and audio sheet review against datasheets

Project: C:\Edit\LazerGamebox, sheets `radio`, `lora_gps`, `audio`. Connectivity taken from
`hardware/reports/netlist.xml`; symbols from `tools/make_symbols.py`; footprints from
`hardware/lib/LazerGamebox_lcsc.pretty`. Date 2026-09-29.

Datasheets used (all in `scratchpad/ds/`):

| Part | File | Source |
|---|---|---|
| SA818S (NiceRF, Rev 1.1, 17 p) | `sa818.pdf` | wmsc.lcsc.com 2204251600 (C3001549) |
| SA818 V3 (NiceRF, 8 p) and DRA818U (Dorji, Rev 1.13, 10 p, same RDA1846 module family, used only where NiceRF is silent) | `sa818_v3.pdf`, `dra818u.pdf` | dmr.md, dorji.com |
| Ra-01SH (Ai-Thinker, V1.1, 17 p) | `ra01sh.pdf` | datasheet.lcsc.com 2104011234 (C2764087) |
| ATGM336H-5N user manual (V1.3, 19 p) | `atgm336h.pdf` (2018 upload) and `atgm336h_2025.pdf` (2025 upload, identical text) | LCSC (C90770) |
| NS4150B (Nsiway, Mar 2021 V1.1, 9 p, Chinese) | `ns4150b.pdf` | LCSC (C189961) |
| TS5A3159 (TI, SCDS174C, 2015) | `ts5a3159.pdf` | LCSC (C46388) |
| BWSMA-KWE-Z001, BW868SNX20-5Z6, BWGNSCNX18-18W4 (BAT Wireless) | `ant_sma.pdf`, `ant_868.pdf`, `ant_gps.pdf` | LCSC (C496551, C496555, C784395) |

Severity: **high** = can damage a part or stop a function working; **medium** = works but out of
spec or relies on firmware to be safe; **low** = cosmetic, margin or documentation.

---

## 1. U301 SA818S-U UHF module (C3001549)

**Verdict: change needed** (one high, two medium).

Symbol versus datasheet pin table (SA818S p.10): 1 Audio ON, 3 AF_OUT, 5 PTT, 6 PD, 7 H/L, 8 VBAT,
9/10 GND, 12 ANT, 16 RXD, 17 TXD, 18 MIC_IN, 2/4/11/13/14/15 NC. The symbol in
`make_symbols.py` matches on every one of the 18 documented pins. The footprint
`WIRELM-SMD_G-NICERF_SA818S-X` has 20 pads: 1 to 7 on the top edge at 4.45 mm pitch, 8 to 11 on
the right edge at 4.6 mm pitch, 12 to 18 on the bottom edge, plus two 3.9 x 6.3 mm pads 19/20 on
the left short edge. That matches the mechanical drawing (p.11: 7 castellations top and bottom,
4 on the right, two large ones on the left). The datasheet never names pads 19/20; the symbol
stacks them as hidden GND pins.

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| PTT pull-up | SA818S p.10: PTT "0" forces TX, "1" RX. No statement about an internal pull-up. DRA818U p.2 (same module family): "Low TX, High RX", abs max Vin = VCC + 0.3 V (p.4). A field report on the DRA818V (nuclearrambo.com) says a floating PTT puts the module in TX. | `/radio/PTT_N` is only Q301 drain (2N7002, open drain) and U301.5. No pull-up. `design.md` section 5 claims "PTT with 10 k pull-up" and the sheet note says "the module's internal pull-up keeps it in RX"; neither is backed by the datasheet. | **high** | Add **R305 100k** from `/radio/PTT_N` to the PD divider node `/radio/PD` (3.2 V, rises and falls with the boost rail, so nothing back-drives the module when RADIO_4V5 is off). Loading the 10k/22k divider with 100k moves PD from 3.16 V to about 2.96 V, still above 0.7 x 3.3 V. A 100k directly to RADIO_4V5 also works and stays within the DRA818U abs max, but 4.6 V into a 3.3 V logic pin is less comfortable. Fix `design.md` to match. |
| RXD back-drive when the module is off | SA818S p.10, pin 16: "Before enter sleep mode, user need to pull low RXD pin to prevent current leakage or poor reset in the next time." DRA818U p.4: Vin abs max VCC + 0.3 V. | `RADIO_TX` (GPIO17, UART2 TX, idles high at 3.3 V) is wired straight to U301.16 while RADIO_4V5 can be 0 V. Protection is a firmware promise only (`design.md` pin table). | medium | Add **R306 1k** in series in `RADIO_TX` between U201.28 and U301.16 (limits any leakage to about 3 mA and makes a "poor reset" far less likely if firmware forgets). Keep the firmware rule too: drive GPIO17 low (or input) before RADIO_EN goes low and for 300 to 500 ms after it goes high (DRA818U p.3: module init time 300 to 500 ms). Optional **R307 1k** in `RADIO_RX` for symmetry. |
| Supply | SA818S p.4: 3.3 to 5.5 V, typ 4.2 V; power spec at 4.0 V. | 4.6 V from TPS61023 boost (`RADIO_4V5` net). | low | OK. Net name says 4V5, rail is 4.6 V; rename or leave. |
| Current and bulk capacitance | SA818S p.4: RX 60 mA, TX high 650 typ / 750 max mA, TX low 450/550 mA, sleep 1 uA. FAQ p.11 blames "power supply ripple too large" for poor range. No capacitor value given. | C303 470 uF + C304 10 uF + C305 100 nF at the VBAT pad. Boost input from a 3.0 V cell at 750 mA out is about 1.3 A. | low | OK. Keep C303 within a few mm of pad 8. Board note: "Module current ... TX high 750 mA" is consistent. |
| PD pin | SA818S p.10: "0" power down, "1" normal. Block diagram p.4 shows an internal LDO, so logic is 3.3 V class. DRA818V field note: PD "pulled high at 3.3 V". | R302 10k / R303 22k from RADIO_4V5: 4.6 x 22/32 = 3.16 V, 144 uA while the boost is on. `design.md` says "PD tied to RADIO_VBAT via 10 k" (a straight tie to 4.6 V), which is not what the netlist has. | low | Circuit is fine as drawn (divider is the better choice). Update `design.md` section 5 wording. |
| H/L pin | SA818S p.10: leave open for high power, low for low power, "can NOT be connected to VDD or high level of cmos output". | Pin 7 to JP301 solder jumper (open) to GND. | none | OK. |
| Audio ON (SQ) | SA818S p.10: output, low = turn amplifier on, high = off. | To TCA9555 P15 (`RADIO_SQ`), expander has 100k internal pull-ups; module output is 3.3 V class. | low | OK. Note: firmware has to switch AMP_SD itself, and NS4150B start-up is 120 ms (NS4150B p.3), so the first 0.1 s of every squelch opening is lost. If that matters, keep the amp enabled while the radio is on and mute by selecting the DAC on the mux instead. |
| MIC_IN level and coupling | SA818S p.4 and DRA818U p.3: modulation sensitivity 10 mV (at 1 kHz for 2.5 kHz deviation). Both typical schematics (SA818S p.5, DRA818U p.8) hang an electret directly on MIC_IN with no external bias, so the pin carries an internal DC bias. RDA1846 rolls off below 300 Hz regardless of filter setting (DRA818U p.6). | DAC1 -> R505 100k -> R506 1k -> C508 1 uF -> MIC_IN: 3.3 Vpp full-scale gives 32.7 mVpp = 11.6 mVrms, right at the rated-deviation point. AC coupled, so the internal bias is not disturbed. | low | OK. Full-scale DAC sine equals about full deviation; drive DTMF at 50 to 70 % DAC amplitude in firmware. If you want hardware margin make R506 = 2.2k (72 mVpp) and trim in firmware. |
| AF_OUT level and load | SA818S p.4: 700 mV amplitude, 200 ohm output impedance. | AF_OUT feeds R507 47k (ADC path) and U501.NO (mux, 220k amp input behind it). Load is negligible against 200 ohm. | none | OK (see TS5A3159 section for the clamp note). |
| UART levels | SA818S: 9600 8N1 (p.5). DRA818U p.2: "TTL level"; internal LDO in the block diagram (p.4). | Direct to ESP32 UART2 at 3.3 V. | none | OK. |
| Antenna | SA818S p.10: "connect 50 ohm antenna". | ANT -> C301 (DNP) / R301 0R / C302 (DNP) pi pads -> J301 SMA; note asks for a 50 ohm coplanar trace with stitching vias. | none | OK. Keep the trace under 10 mm and put C301 at the module pad, C302 at the SMA. |
| Pads 19/20 | Not in the pin table; visible on the drawing as the two large castellations on the left edge. | Symbol makes them hidden GND pins; footprint has them as 3.9 x 6.3 mm pads. | low | On the SA818/SA818S those two pads are the shield-can ground tabs, so GND is the sensible choice, but confirm on a physical module (continuity to pad 9) before the panel is ordered. If unsure, leave them unconnected copper (no net) instead of GND. |
| Thermal | hamvoip.org SA818 node write-up: do not run high power for long periods without heat sinking. | Nothing on the sheet. | low | Add a layout note: solid ground pour under the module, thermal vias under pads 19/20 and the GND pads, and expect firmware TX time limits at 1 W. |

---

## 2. U401 Ra-01SH LoRa (SX1262, C2764087)

**Verdict: OK** (only low items).

Symbol versus datasheet pin table (Ra-01SH p.11): 1 ANT, 2 GND, 3 3.3V, 4 RESET, 5 TXEN, 6 DIO1,
7 DIO2, 8 DIO3, 9 GND, 10 BUSY, 11 RXEN, 12 SCK, 13 MISO, 14 MOSI, 15 NSS, 16 GND. The symbol
matches all 16. Footprint `WIRELM-SMD_RA-01SH`: pads 1 to 8 down the left at 2.0 mm pitch, 16 to
9 down the right, 16.0 mm apart, matching the package drawing on p.13 (2.0 mm pitch, 13.83 mm
pad-to-pad plus pad length, 17 x 16 mm body).

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| TXEN / RXEN left open | Module schematic p.12: DIO2 -> R8 0R -> TX_EN -> Q1 -> RF switch CTRL, with RX_EN tied to the same node through R1 and pulled up by R7 1M. Note on p.12: "DIO2 = 1, CTRL = 0, RFC to RF1 Tx mode; DIO2 = 0, CTRL = 1, RFC to RF2 Rx mode". Application circuit p.13 leaves TXEN and RXEN unconnected. | TXEN, RXEN, DIO2, DIO3 no-connect. | none | OK, provided firmware calls `setDio2AsRfSwitchCtrl(true)`. Without it the switch stays in RX and TX power goes nowhere. Add this to the firmware notes. |
| RESET / BUSY / DIO1 / NSS / SPI | p.11 and p.13: RESET active low input, BUSY output, DIO1 IRQ, NSS chip select, SPI up to 10 MHz (p.9). p.15 suggests 10 to 100 ohm series resistors on IO for EMI/ESD (optional). | LORA_RST from TCA9555 P10, BUSY GPIO4, DIO1 GPIO33, NSS GPIO5, SCK/MOSI/MISO shared with the display. | low | OK. TCA9555 ports power up as inputs with 100k pull-ups so NRESET floats high at boot, fine. Optional: 33 ohm in series on SCK/MOSI near the ESP32 (shared bus, helps ringing). |
| Supply and decoupling | p.6: 2.7 to 3.6 V, current above 200 mA. p.14: LDO preferred; if DC-DC, ripple under 30 mV; ESD device on the 3.3 V pin recommended; reserve a "dynamic response" capacitor. | +3V3 from TPS62A02 buck, C403 10 uF + C404 100 nF at the module. | low | OK. The buck with 2 x 22 uF will be under 30 mV ripple. If you want to follow p.14 fully, add a 100 uF/1206 DNP pad on +3V3 near U401. |
| Crystal / TCXO | Module schematic p.12 uses a plain crystal Y1 on XTA/XTB; DIO3 is not used for a TCXO. | DIO3 NC. | low | Firmware: do not enable the SX1262 TCXO (`setTCXO`), or the radio will never leave the calibration error state. |
| Antenna | p.6: half-hole or through-hole pad for a soldered antenna or IPEX. p.13 application circuit: 0R series plus two NC shunt caps, exactly the pi pads drawn. p.14: keep the antenna away from metal. | ANT -> C401 (DNP) / R401 0R / C402 (DNP) -> ANT401 spring. | none | OK. |

---

## 3. U402 ATGM336H-5N31 GNSS (C90770)

**Verdict: change needed** (one medium for back-drive, one medium for RF).

Symbol versus datasheet pin table (manual p.9 to 10): 1 GND, 2 TXD, 3 RXD, 4 1PPS, 5 ON/OFF,
6 VBAT, 7 NC, 8 VCC, 9 nRESET, 10 GND, 11 RF_IN, 12 GND, 13 NC, 14 VCC_RF, 15 Reserved, 16 SDA,
17 SCL, 18 Reserved. The symbol matches all 18. Footprint `GPSM-SMD_ATGM336H-TR`: pins 1 to 9
along one edge at 1.1 mm pitch, 10 to 18 along the other, pins 9 and 10 at the same end, which is
the top-view arrangement on p.9.

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| RXD back-drive when GPS_3V3 is off | p.11 limit table: digital input pin voltage max Vcc + 0.2 V. | `GPS_TX` (GPIO14, UART1 TX, idles high at 3.3 V) goes straight to U402.3 while GPS_3V3 is switched off by Q103. VBAT (pin 6) stays on +3V3, so the module is partly powered and the RXD pin is fed through its VCC-domain ESD diode whenever the rail is off (that is most of the time in this design). | medium | Add **R411 1k** in series in `GPS_TX` between U201.13 and U402.3 (put it on the module side of the R409 0R link so the DNP cellular path is unaffected), and in firmware drive GPIO14 low or as input while GPS_EN is low. 1k limits the leakage to about 3 mA, which the module ESD diode tolerates but which also keeps the module's VCC domain from floating up. |
| VCC | p.10: 3.3 V +/-10 %, 100 mA; p.11: 2.7 to 3.6 V, peak 100 mA; p.14: LDO with ripple under 50 mVpp. | GPS_3V3 from +3V3 buck through an AO3401A switch, C406 10 uF + C407 100 nF. | low | OK. Buck ripple with 2 x 22 uF is well under 50 mVpp. |
| VBAT backup | p.10: 1.5 to 3.6 V, 10 uA typ, keeps RTC/SRAM for hot start. | +3V3 always on. | none | OK. |
| ON/OFF | p.10: "shutoff control, low level effective". Reference circuits p.13 and 14 leave it open. | R410 10k pull-up to GPS_3V3. | none | OK (the pull-up follows the switched rail, so it never back-feeds). |
| nRESET | p.10: "left floating when not in use". | Unconnected. | none | OK. |
| 1PPS | p.6: rising edge aligned to UTC. p.11: Voh Vcc - 0.5 V. | To TCA9555 P17. | none | OK. |
| UART | p.12: 4800 to 115200 baud, default 9600 8N1, NMEA. 3.3 V logic (Vih 0.7 Vcc). | UART1 GPIO13/14. | none | OK. |
| RF_IN coupling and bias | Active-antenna circuit p.13 feeds antenna bias from pin 14 VCC_RF through an external 47 nH into RF_IN, so RF_IN itself carries no DC and needs no DC block with a passive antenna. Passive-antenna circuit p.14 adds an external AT2659 LNA with a 470 pF coupling cap and 6.8 nH match; the variant table p.4 lists "External LNA" for every variant. p.7: "supports active antenna and passive antenna". | ANT402 -> C405 100 pF -> RF_IN. VCC_RF unconnected. No LNA, no matching pads. | medium | C405 is harmless (1 ohm at 1575 MHz), keep it. Add a **pi matching network footprint** (shunt C, series L, shunt C, 0402/0603, all DNP, series position fitted with 0R) between ANT402 and C405: an 18 mm patch on a 40 x 40 mm plane will sit a few MHz off 1575 and the pads let you retune. Optionally reserve the p.14 LNA (AT2659 or MAX2659, SOT-363) as a DNP footprint if cold-start sensitivity indoors matters; the bare module works with passive patches in many commercial breakouts, so this is insurance, not a must. |
| Antenna detection | p.14: module monitors VCC_RF and prints `$GPTXT ... ANTENNA OPEN/SHORT/OK`. | VCC_RF open. | low | Expect a permanent "ANTENNA OPEN" text sentence; ignore it in firmware. |
| ESD on RF_IN | p.17 item 4: add ESD protection if the antenna dielectric can be touched. | None. | low | Patch sits inside the enclosure; nothing needed. |
| Layout | p.14: ground fill under the module, antenna as close as possible to RF_IN, 50 ohm. | Note on the sheet says the same. | none | OK. |

---

## 4. U502 NS4150B class-D amplifier (C189961)

**Verdict: change needed** (one medium).

Symbol versus datasheet (p.2 pin table): 1 CTRL, 2 Bypass, 3 INP, 4 INN, 5 VoN, 6 VCC, 7 GND,
8 VoP. The symbol matches all 8. Footprint is the stock KiCad MSOP-8.

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| CTRL driven while VCC is off | p.2 abs max: INP/INN/CTRL pins -0.3 to VDD + 0.3 V. p.3: VIH min 1.2 V, VIL max 0.2 V; ISD 0.1 uA typ. p.7: H = open (on), L = shutdown. | `AMP_SD` from TCA9555 P04 at 3.3 V goes straight to CTRL; R504 100k pull-down. VBAT_SW (the amp VCC) is switched by AUX_EN and is off in sleep. If firmware ever sets P04 high with AUX_EN low, CTRL sits 3.3 V above VDD. | medium | Add **R511 10k** in series in `AMP_SD` between U205.8 and U502.1 (keep R504 100k on the CTRL side; the divider still gives 3.0 V, above VIH 1.2 V). Firmware rule: AMP_SD high only after AUX_EN has been high for a few ms, AMP_SD low before AUX_EN goes low. |
| Gain | p.7 section 9.9: internal feedback 240k, AVD = 2 x 240k / Rin. Typical circuit p.1 uses 30k / 0.1 uF. | R502 = R503 = 220k: gain 2.18 V/V (6.8 dB). | low | OK. Note the implication: a full-scale 3.3 Vpp DAC signal becomes 7.2 Vpp differential, more than 2 x VCC at any cell voltage, so firmware must cap DAC amplitude at roughly 60 % (or use 330k for R502/R503 to bring it to 1.45 V/V). Radio AF at 0.7 V gives 1.5 Vpp, fine. |
| Input coupling | p.7 to 8, 9.10: fc = 1/(2 pi Rin Cin); large coupling caps slow the feedback settling and cause pop, small caps are preferred (speakers do not reproduce below 100 to 150 Hz anyway). | C501 1 uF with R502 220k (fc 0.7 Hz); C503 1 uF with R503 220k on INN. | low | Change **C501 and C503 to 100 nF** (fc 7 Hz, still far below the 30 mm speaker) to cut the source-switch thump: the mux swaps between the DAC (1.65 V mid) and AF_OUT (different DC level) and the 0.22 s RC on C501 is audible with 1 uF. |
| INN handling | p.1 typical circuit: INN through the same R and C to ground. | INN -> R503 220k -> C503 1 uF -> GND. | none | OK. |
| Bypass | p.2: 1 uF to GND. | C504 1 uF. | none | OK. |
| VCC range | p.3: 3.0 to 5.0 V (abs max 5.25 V, "recommended" table 2.2 to 5.0 V); UVLO shuts it down at low supply (p.7, 9.7). | VBAT_SW = 3.0 to 4.2 V, plus a few tens of mV drop in the AO3401A. | low | OK. Near 3.0 V the UVLO may trip; the cell protector cuts at 2.5 V anyway. Firmware can lower the volume below 3.3 V. |
| Decoupling | p.7, 9.8: 1 uF ceramic at VDD, plus 10 uF or more for low-frequency; typical circuit shows 1 uF + 1 nF. | C505 470 uF + C506 10 uF + C507 100 nF. | low | Fine. Optionally swap C507 100 nF for 1 uF to match the datasheet's preferred high-frequency bypass; keep it next to pin 6. |
| Output | p.3: 1.3 W into 8 ohm at 5 V 1 % THD, 1.7 W at 10 %. p.8, 9.11: filter-free, passes FCC with 60 cm leads without beads; beads and caps only for long leads. | VoP/VoN straight to LS501 (8 ohm, 1 W). No bead pads (the `design.md` mention of "ferrite bead pads DNP" is not in the netlist). | low | OK. Scale expectations: about 0.9 W at 4.2 V, 0.45 W at 3.0 V into 8 ohm, not "1 W at 3.7 V". Leads are a few cm, no beads needed. |

---

## 5. U501 TS5A3159DCKR analog switch (C46388)

**Verdict: OK** (one low suggestion).

Symbol versus datasheet (p.3): 1 NO, 2 GND, 3 NC, 4 COM, 5 V+, 6 IN. The symbol matches.
Footprint is the stock KiCad SC-70-6.

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| Select logic | p.3: IN high = COM to NO, low = COM to NC. | NO = RADIO_AF, NC = DAC1 (through R501 1k), IN = MUX_SEL. `design.md`: MUX_SEL low = DAC, high = radio. | none | OK, consistent. |
| Control levels | p.6 (3.3 V supply): VIH 2.0 V min, VIL 0.6 V max; inputs 5 V tolerant. | TCA9555 output at 3.3 V. | none | OK. |
| Signal range | p.4: switch I/O 0 to V+; abs max -0.5 to V+ + 0.5 V, port diode current 50 mA (p.3). | V+ = +3V3, C502 100 nF. DAC is 0 to 3.3 V through R501 1k. AF_OUT is a single-supply output biased above ground on the module (700 mV around an internal DC level), so it should stay inside 0 to 3.3 V. | low | Add **R512 1k** in series between `RADIO_AF` and U501.1 (NO), mirroring R501 on the DAC side, so an unexpected negative excursion or a 4.6 V-referenced fault on AF_OUT cannot exceed the 50 mA clamp rating. Costs nothing against 220k / 47k loads. |
| Ron, THD, bandwidth | p.6: 1.15 ohm typ at 3.3 V, THD 0.015 % into 600 ohm, off isolation -65 dB at 1 MHz. | Loads are 220k (amp) and 47k (ADC). | none | OK. |
| Supply current | p.6: 0.1 uA. | Always on +3V3. | none | OK for the sleep budget. |

---

## 6. Antennas and connectors

**Verdict: OK** (layout notes only).

| Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|
| J301 BWSMA-KWE-Z001 | `ant_sma.pdf` p.1 and 4: passive PCB-end right-angle SMA, 0 to 6 GHz, 50 ohm, insertion loss 0.15 dB at 6 GHz, gold plated phosphor bronze, 14.5 x 13 x 6 mm. | `Conn_Coaxial` J301, footprint `SMA_BAT_Wireless_BWSMA-KWE-Z001` (centre pin 5, four 1.6 mm ground legs). Ext pin to GND. | none | OK. Ground all four legs into the plane with several vias each; the 50 ohm trace from R301/C302 should be a coplanar waveguide with ground on both sides right up to pin 5. |
| ANT401 BW868SNX20-5Z6 | `ant_868.pdf` p.4 and 10: passive spring antenna, 50 ohm, VSWR under 5.3, gain -1.5 to -1.8 dBi, efficiency about 28 % at 860 to 870 MHz, vertical polarisation, 20 x 5 x 6 mm. No ground-plane size stated. | `Device:Antenna` on a 1-pin THT footprint via the DNP pi pads. | low | It is a quarter-wave helical: it needs the board ground plane as its counterpoise. Mount it at a board edge with the ground pour ending at the pin, keep copper away from the coil itself, and keep it at least 15 mm from the SA818S PA and the SMA whip as the sheet already says. With 28 % efficiency expect real range to be modest; the pi pads (C401/R401/C402) are the right provision for tuning. |
| ANT402 BWGNSCNX18-18W4 | `ant_gps.pdf` p.1, 3 and 4: passive ceramic patch ("W = Passive Antenna"), 1575 +/-5 and 1561 +/-5 MHz, 50 ohm, VSWR under 2, RHCP, gain about 0.65 to 0.96 dBi, 18 x 18 x 4 mm, single feed pin. No ground-plane size stated. | `Device:Antenna` on a 1-pin THT footprint (pad 1.8 mm, drill 1.1 mm) via C405 to RF_IN. | low | Passive, correct. Patch resonance depends on the ground plane under it: use a solid, unbroken plane at least 40 x 40 mm (50 x 50 mm is better) with no other copper or components on the antenna side, the patch centred on it, and no traces under the ceramic. Add the pi matching pads recommended in section 3 so the +/-5 MHz band can be recovered after measuring. Keep it away from the 868 spring and the UHF whip. |

---

## 7. Audio chain values and "nothing drives an unpowered module"

| Path | Calculation / check | Result |
|---|---|---|
| DAC1 -> MIC_IN | R505 100k / R506 1k: ratio 1/101. 3.3 Vpp -> 32.7 mVpp = 11.6 mVrms sine. Sensitivity 10 mV for 2.5 kHz deviation (SA818S p.4, DRA818U p.3). C508 1 uF into MIC_IN's internal bias network: fc a few tens of Hz. | OK. Full-scale DAC is about full deviation; run DTMF at 50 to 70 % amplitude. |
| AF_OUT -> ADC_AUDIO | Source 200 ohm + R507 47k into R508 || R509 = 50k bias at 1.65 V: gain 0.51. 700 mV amplitude -> 0.36 V (if rms, about 1.0 Vpp) at GPIO36, centred at 1.65 V, inside the ESP32 11 dB attenuation range (0.15 to 2.45 V). C509 1 uF with 97k: fc 1.6 Hz. R510 10k / C510 1 nF: 15.9 kHz anti-alias. | OK. Consider C510 = 10 nF (1.6 kHz corner is too low for DTMF 1633 Hz, so keep 1 nF, or use 4.7 nF for 3.4 kHz) if you find ADC sampling noise; 1 nF is acceptable. |
| Mux source select | NC = DAC (R501 1k), NO = AF_OUT, IN high = NO. C501 after COM, then 220k. | OK. Thump on switching, see NS4150B C501 note. |
| DAC -> amp headroom | 3.3 Vpp x 2.18 = 7.2 Vpp differential versus 2 x VCC = 6.0 to 8.4 Vpp. | Firmware caps DAC to about 60 %. |
| Radio off (RADIO_4V5 = 0) | RADIO_TX idles high into RXD: **needs R306 and firmware** (section 1). PTT: open-drain, no current. PD: divider from the dead rail, 0 V. H/L: open. MIC_IN: only AC through C508 at 33 mVpp, harmless. AF_OUT: mux NO pin is an input, R507 path is AC coupled. AUDIO_ON: expander pull-up 100k, 33 uA max into the dead pin, harmless. | One fix (R306). |
| GPS off (GPS_3V3 = 0) | GPS_TX idles high into RXD: **needs R411 and firmware** (section 3). ON/OFF pull-up follows the switched rail. 1PPS/TXD are outputs into ESP inputs. VBAT stays on by design. | One fix (R411). |
| Amp off (VBAT_SW = 0) | AMP_SD from the expander can be 3.3 V above VDD: **needs R511 and firmware** (section 4). INP/INN only see AC through C501/C503. | One fix (R511). |
| LoRa | Always powered, nothing to check. | OK. |

---

## Summary of recommended changes, most important first

1. **R305 100k pull-up on `/radio/PTT_N`** (to the 3.2 V PD node `/radio/PD`, or to RADIO_4V5). The SA818S datasheet documents no internal pull-up and the open-drain Q301 leaves PTT floating in the "RX" state; a floating PTT has been reported to key the transmitter. `design.md` already claims this resistor exists; the netlist does not have it.
2. **R411 1k in series in `GPS_TX`** (U201.13 to U402.3) plus firmware driving GPIO14 low while GPS_EN is off: ATGM336H input abs max is Vcc + 0.2 V and the module's VCC domain is off most of the time while VBAT stays powered.
3. **R306 1k in series in `RADIO_TX`** (U201.28 to U301.16), optional R307 1k in `RADIO_RX`, plus the firmware rule the SA818S datasheet demands (RXD low before power-down, wait 300 to 500 ms after power-up).
4. **R511 10k in series in `AMP_SD`** (U205.8 to U502.1) plus AUX_EN-before-AMP_SD sequencing: NS4150B CTRL abs max is VDD + 0.3 V and VBAT_SW is switched.
5. **Pi matching pads (DNP C, 0R L, DNP C) between ANT402 and C405** for the GPS patch; the 18 mm patch on a 40 x 40 mm plane will need retuning. Optional DNP LNA footprint per the ATGM336H passive-antenna reference circuit (p.14).
6. **C501 and C503 from 1 uF to 100 nF** to reduce the source-switch thump (NS4150B p.8 note on coupling caps); firmware caps DAC amplitude at about 60 % into the amp (gain 2.18 exceeds the supply at full scale).
7. **R512 1k between `RADIO_AF` and U501.1** to protect the TS5A3159 clamp diodes, mirroring R501.
8. Firmware notes to record: `setDio2AsRfSwitchCtrl(true)` on the SX1262 (TXEN/RXEN pads are open by design), no TCXO on the Ra-01SH, ignore the ATGM336H "ANTENNA OPEN" sentence, DTMF at 50 to 70 % DAC amplitude (full scale equals rated deviation).
9. Confirm SA818S pads 19/20 are ground on a physical module before ordering; otherwise leave them without a net. Fix `design.md` wording on PD (divider, not a tie), PTT pull-up, RADIO_4V5 = 4.6 V, and the non-existent output bead pads.

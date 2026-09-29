# LazerGamebox schematic review: MCU and IO sheets against datasheets

Reviewed 2026-09-29 against `hardware/reports/netlist.xml` (authoritative), `tools/gen_schematic.py` (`gen_mcu`, `gen_io`), `docs/design.md`, `docs/pinmap.md`.
Datasheets used (saved in `scratchpad/ds/`):

| Part | Document | Note |
|---|---|---|
| ESP32-WROOM-32E | Espressif ESP32-WROOM-32E & 32UE Datasheet v2.1 (`esp32.pdf`), ESP32 Series Datasheet (`esp32_soc.pdf`), ESP32 hardware design guidelines schematic checklist (web), ESP32-DevKitC V4 schematic (`esp32_devkitc_v4-sch.pdf`) | LCSC link returns HTML; Espressif originals used |
| CH340C | WCH CH340 datasheet V3C (`ch340c.pdf`, LCSC mirror) | |
| LIS3DH | ST DocID17530 Rev 2 (`lis3dh.pdf`, LCSC mirror) | |
| TCA9555 | TI SCPS200E (`tca9555.pdf`) | |
| WS2812B-2020-V6 | Worldsemi WS2812B-2020-V6 (`ws2812b2020.pdf`, LCSC mirror, 10 pages) | |
| IRM-H638T/TR2 | Everlight DMO-0000004 Rev 4 IRM-H6XX/TR2 series (`DMO-0000004-IRM-H6XX-TR2_Series_Datasheet_V4.pdf`) | LCSC copy not downloadable; this is the document KiCad's footprint cites |
| VSMY2940G | Vishay doc 84221 Rev 1.1 (`vsmy2940g.pdf`) | |
| SS8050 | JSCJ SS8050 Rev 2.1 (`ss8050.pdf`) | |
| TPS61023 | TI (`tps61023.pdf`), only for the EN threshold | |

Severity: high = will not work or damages a part, medium = out of spec or unreliable, low = cosmetic, documentation or firmware rule.

---

## 1. ESP32-WROOM-32E-N16, U201

**Verdict: change needed** (auto-reset transistor polarity is inverted; otherwise the module wiring matches the datasheet).

| # | Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|---|
| 1.1 | Auto-reset DTR/RTS pair | ESP32-DevKitC V4 schematic, "Auto program" table: DTR=1, RTS=0 gives EN=0, IO0=1; DTR=0, RTS=1 gives EN=1, IO0=0. So the transistor on EN has DTR on its base and RTS on its emitter; the transistor on IO0 has RTS on its base and DTR on its emitter. esptool's classic sequence (DTR high/RTS low = "EN low", then DTR low/RTS high = "IO0 low", then release) relies on this. | Netlist: `/mcu/RTS` = R204.1 (to Q201 base) + Q202.E; `/mcu/DTR` = R205.1 (to Q202 base) + Q201.E; Q201.C = EN, Q202.C = IO0. That is Q201(EN): base RTS, emitter DTR; Q202(IO0): base DTR, emitter RTS. Inverted: esptool's step 1 pulls IO0 low (not EN), step 2 pulls EN low with IO0 high, step 3 releases both, so the chip always boots normally and never enters UART download mode. Manual BOOT+RESET still works. | **High** | In `gen_mcu` change the tuple to `("Q201", "R204", 66, "DTR", "RTS", "EN")` and `("Q202", "R205", 98, "RTS", "DTR", "IO0")`, i.e. R204 from DTR to Q201 base, Q201 emitter to RTS; R205 from RTS to Q202 base, Q202 emitter to DTR. 10 k base resistors are what the DevKitC uses (R21/R22 10 k). |
| 1.2 | EN RC circuit | Module datasheet p39 and design guidelines: R = 10 kΩ, C = 1 µF at EN; VIL_nRST 0.6 V max, VIH_nRST 0.75 VDD (p29); tRST ≥ 50 µs (p17). | R201 10 k to +3V3, C203 1 µF to GND, SW201 to GND, Q201 collector. | OK | none |
| 1.3 | VDD decoupling | Design guidelines: 10 µF on VDD3P3 (plus 0.1 µF in the module reference schematic Fig. 9, p39). | C201 10 µF + C202 100 nF on +3V3. | OK | Layout: both within a few mm of module pin 2, 100 nF nearest. |
| 1.4 | GPIO0 strapping | Table 4 (p13): default pull-up, 1 = SPI boot; 0 with GPIO2 = 0 gives download mode (Table 6, p14). | R202 10 k to +3V3, SW202 to GND, Q202 collector. | OK | none |
| 1.5 | GPIO2 strapping (LCD_BL) | Must be 0 (or floating) for download mode (Table 6, p14); default internal pull-down (45 kΩ, p29). | R203 10 k pull-down; also R602 1 k into Q601 base-emitter, which only pulls low. Nothing pulls it up. | OK | none |
| 1.6 | GPIO12 / MTDI (LCD_DC) | MTDI = 0 at reset keeps VDD_SDIO at 3.3 V for the module flash (p15). No external pull-up allowed. | Net LCD_DC only goes to J601 pin 3 (RS, an ST7789 input). No pull-up. | OK | none. Note the panel is on switched LCD_3V3, so it can never drive RS. |
| 1.7 | GPIO15 / MTDO (LED_DATA) | Default pull-up (p13). 1 = ROM boot log on U0TXD enabled (Table 7, p16); MTDO/GPIO5 only set SDIO slave timing (Table 8), irrelevant here. | R604 330 R to D601 DIN. WS2812B DIN input current ±1 µA (WS2812B p3), so the pin stays high at reset. | OK | none |
| 1.8 | GPIO5 (LORA_CS) | Default pull-up (p13), used only for SDIO slave timing. | Direct to Ra-01SH NSS (input). Pull-up also keeps the LoRa deselected at reset. | OK | none |
| 1.9 | Input-only pins 34/35/36/39 | ESP32 Series Datasheet p61 note 2: GPIO34-39 are input only, no output driver, no internal pull-up/down; guidelines: add external resistors if needed. | IO34 = ADC_POT (RC 10 k/100 nF), IO35 = IR_RX (10 k pull-up R606 to LCD_3V3), SENSOR_VP = ADC_AUDIO, SENSOR_VN = ADC_VBAT. All inputs. | OK | none. IR_RX floats when LCD_EN is off (receiver unpowered, pull-up rail off): firmware must stop the RMT RX channel before dropping LCD_EN (low). |
| 1.10 | Flash pins IO6-IO11 | Not exposed on the -32E; module pins 17-22 are NC (p8-9 pin table). | Pins 17-22 and 32 unconnected in the netlist. | OK | none |
| 1.11 | UART0 to CH340C | Module RXD0 (pin 34, GPIO3) must go to the converter's TXD and TXD0 (pin 35, GPIO1) to its RXD. | `/mcu/U0RXD` = U201.34 + U203.2 (TXD); `/mcu/U0TXD` = U201.35 + U203.3 (RXD). | OK | none |
| 1.12 | Back-feeding the unpowered CH340C through UART0 | U0RXD has ie=1 and wpu at and after reset (IO_MUX table, Series Datasheet p69-70; pull-up ~75 µA, p62). CH340 datasheet p13: CH340C lots whose number starts with 4 have anti-backflow I/O when unpowered; "for other lot numbers ... an additional anti-injection circuit is required" and "it is not recommended that the CH340 and MCU be powered separately". | CH340C is dead on battery (own LDO from VBUS) while U0TXD drives 3.3 V into its RXD pin and GPIO3's pull-up feeds its TXD pin. With an older lot the ESP32 back-powers CH_3V3 through the CH340C protection diodes (mA from GPIO1 while running, ~75 µA in sleep). | Medium | Cheapest insurance: 1 k series resistors in both lines (R210 in U0TXD toward U203.3, R211 in U0RXD toward U203.2); limits any back-feed to about 2.5 mA and does not affect 115200-921600 baud. Or accept the risk and confirm the JLC lot code starts with 4. In deep sleep firmware can also disable the GPIO3 pull-up. |
| 1.13 | GPIO drive for the NPN bases | IOH about 40 mA per pin at VOH ≥ 2.64 V (p29 note 2). | R602/R608 1 k give ≈ 2.3 mA each. | OK | see 7.2 for the IR base current. |
| 1.14 | Driving unpowered loads from GPIOs | General rule (WS2812B abs max VI ≤ VDD + 0.7, p3; ST7789 likewise) | LED_DATA (IO15) sits high via the internal pull-up while VBAT_SW is off; SCK/MOSI/LCD_DC toggle into the unpowered ST7789 whenever LoRa is used with LCD_EN off. R604 330 R limits the LED case to ≈ 8 mA. | Low | Firmware rule: RMT idle level low on LED_DATA, and keep LCD_EN on whenever the SPI bus is active (only drop it for deep sleep, after driving SCK/MOSI/LCD_DC low). No hardware change. |

## 2. CH340C USB-UART, U203

**Verdict: OK with two small additions** (decoupling at the pin, and the polarity fix in 1.1 belongs to this circuit too).

| # | Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|---|
| 2.1 | Pin numbers vs custom symbol `LazerGamebox:CH340C` | SOP-16 column, p3-4: 1 GND, 2 TXD, 3 RXD, 4 V3, 5 UD+, 6 UD-, 7 NC ("CH340C: empty pin, must be suspended"), 8 OUT# (MODEM output, optional second DTR#), 9 CTS#, 10 DSR#, 11 RI#, 12 DCD#, 13 DTR#, 14 RTS#, 15 R232, 16 VCC. | Symbol: 1 GND, 2 TXD, 3 RXD, 4 V3, 5 UD+, 6 UD-, 7 NC, 8 NC, 9 CTS#, 10 DSR#, 11 RI#, 12 DCD#, 13 DTR#, 14 RTS#, 15 R232, 16 VCC. All match; pin 8 is an output left open, which is allowed (p4: unused I/O may be dangled). | OK | Optional: rename symbol pin 8 to OUT# (cosmetic). |
| 2.2 | 3.3 V operation | p3/p5: at 3.3 V connect V3 to VCC and feed 3.3 V into VCC; VCC range for CH340C 3.1 to 3.6 V (p9). | `/mcu/CH_3V3` = U202 VO + U203.16 (VCC) + U203.4 (V3) + C204 1 µF. XC6206P332 gives 3.3 V ±2 %. | OK | none |
| 2.3 | Decoupling | p3: VCC "requires an external 0.1 µF decoupling capacitor"; p10: C8 (V3) and C9 (VCC) 0.1 µF "as close as possible" to the pins. | Only C204 1 µF, which is also the LDO output capacitor and sits at U202 in the drawing. | Low | Add C209 100 nF between U203 pin 16 and GND placed at the chip; keep C204 1 µF at U202 (XC6206 needs ≥ 1 µF ceramic on VO). C205 1 µF on VBUS is fine as LDO input cap. |
| 2.4 | USB D+/D- | p3: "connect directly to the D+/D- data line without a series resistor"; built-in 1.5 k pull-up (p5). | J101 D+/D- through USBLC6-2SC6 pass-through pins to UD+/UD-, no series resistors. | OK | none. `docs/design.md` section 5 still says "22 ohm series on D+/D-": update the text, the schematic is right. |
| 2.5 | DTR#/RTS# polarity for auto-reset | p4: DTR# and RTS# are active-low outputs (pin high = not asserted). esptool "setDTR(True)" drives the pin low. | Used in the SS8050 pair; see 1.1, the pair is cross-wired. | High (same as 1.1) | Apply the fix in 1.1. |
| 2.6 | R232 (pin 15), CTS#/DSR#/RI#/DCD# | p4: R232 has a built-in pull-down (leave open for normal mode); unused inputs may be left floating. | All NC. | OK | none |
| 2.7 | Separate supply from the ESP32 | p13: dual-supply mode is discouraged; use anti-backflow parts unless the CH340C lot is anti-backflow. | Own LDO on VBUS by design. | Medium | See 1.12 (1 k series resistors R210/R211). |
| 2.8 | ESD | Not in the datasheet | USBLC6-2SC6 on D+/D-/VBUS. | OK | none |

## 3. LIS3DHTR accelerometer, U204

**Verdict: change needed** (SA0 is not a valid logic low through 10 k).

| # | Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|---|
| 3.1 | I2C mode select | p9, p20, p24: CS must be tied high (to Vdd_IO) for I2C. | U204.8 CS = +3V3 (= Vdd_IO). | OK | none |
| 3.2 | SA0 / address | p9 Table 3: SDO/SA0 has an internal pull-up of 20.4 kΩ typ at Vdd_IO 3.6 V (about 22 k at 3.3 V), enabled by default (CTRL_REG0, p9 footnote). VIL max = 0.2 × Vdd_IO = 0.66 V (Table 6, p12). Address 0011000b (0x18) needs SA0 low (p25). | R209 10 k from SDO/SA0 to GND. The divider 22 k / 10 k puts the pin at about 1.0 V, above VIL(max) 0.66 V and below VIH(min) 2.64 V: undefined address (0x18 or 0x19, possibly lot dependent). | **High** | Tie SDO/SA0 (pin 7) directly to GND: change R209 to 0 R (`R(sh, "R209", "0R", ...)`, C21189) or delete it and use `sh.pin_power(a, "SDO", G)`. Anything ≤ 1 k also works (≤ 0.15 V). |
| 3.3 | Decoupling | p20: 100 nF ceramic + 10 µF "as near as possible to pin 14 (Vdd)". | C206 100 nF + C207 10 µF on +3V3 in the accelerometer block. | OK | Layout: C206 at pin 14, C207 next to it; pin 1 (Vdd_IO) shares the rail. |
| 3.4 | Vdd_IO vs Vdd | Table 6 (p12): Vdd_IO ≤ Vdd + 0.1 V, both 1.71 to 3.6 V; all supplies present together (p20). | Both on +3V3. | OK | none |
| 3.5 | Pins that must be tied | p9: pin 10 "RES: connect to GND"; pins 2, 3 NC; ADC1-3 may float (p20); INT2 is an output, may float. | Pin 10 = GND, pins 5/12 = GND, 2/3/9/13/15/16 NC. | OK | none |
| 3.6 | INT1 | Push-pull output, VOH ≥ 0.9 Vdd_IO (p12); polarity and latch programmable. | INT1 (pin 11) to TCA9555 P16, expander INT to GPIO32 for wake. | OK | Firmware: enable latched INT1 (LIR_INT1) so the level persists until the ESP32 reads INT1_SRC over I2C after waking. |
| 3.7 | I2C pull-ups | p24: SCL/SDA need external pull-ups to Vdd_IO; fast mode 400 kHz. | R206/R207 4.7 k to +3V3. | OK | none |

## 4. TCA9555PWR I2C expander, U205

**Verdict: change needed** (RADIO_EN has no pull-down, so the expander's power-on state turns the radio boost on).

| # | Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|---|
| 4.1 | Address pins | p4 pin table: A0/A1/A2 "connect directly to VCC or ground"; address 0100 A2 A1 A0 (p13). | A0 (21), A1 (2), A2 (3) all GND: 0x20. | OK | none |
| 4.2 | INT output | p16: open drain, "requires a pull-up resistor to VCC (typically 10 kΩ)". | R208 10 k to +3V3, net EXP_INT to GPIO32. | OK | none |
| 4.3 | VCC decoupling | Typical application: 0.1 µF at VCC. | C208 100 nF on +3V3. | OK | Layout: at pin 24. |
| 4.4 | Button inputs with 100 nF | P-port inputs: high impedance with a 100 kΩ pull-up (p17 Fig. 23); VIH 0.7 VCC, VIL 0.3 VCC (p5); no input hysteresis is specified; any edge on an input generates INT (p16). | SW601-603 to GND with C604-606 100 nF on P12-P14. Release rise time constant is 100 k × 100 nF = 10 ms; the slow ramp through the threshold can produce more than one INT edge. | Low | Acceptable. Firmware: on INT read both input ports, then debounce in software (≥ 20 ms). If cleaner edges are wanted, drop the caps to 10 nF (1 ms) or add 10 k external pull-ups. |
| 4.5 | Power-on state of the outputs | p4 pin table and p16: at power-on every P pin is an input with the 100 kΩ pull-up, i.e. every "output" net floats to about 3.3 V until the ESP32 writes the configuration register. | RADIO_EN net = U104.2 (TPS61023 EN) + U205.4 only, no pull-down. TPS61023 turns on above 1.2 V on EN and off below 0.4 V (TPS61023 p9). So at every power-up, during reset, while flashing, and if firmware crashes before I2C init, the 4.6 V boost and the SA818S-U are powered. GPS_EN/LCD_EN/AUX_EN are fine (10 k gate pull-downs R116/R118/R120 give 0.3 V), AMP_SD has R504, LORA_RST high = not in reset (fine), MUX_SEL/LCD_CS/LCD_RST floating high is harmless. | Medium | Add R121 10 k from RADIO_EN to GND next to U104 (100 k / 10 k divider = 0.3 V < 0.4 V VEN_L). Also configure the expander as the first thing after boot. |
| 4.6 | Output current | IOL 25 mA, IOH 10 mA per P pin (p5). | Loads are 2N7002 gates, IC enable pins, ST7789 CS/RST. | OK | none |
| 4.7 | Inputs above VCC | Inputs may be raised to 5.5 V (p16). | All sources are 3.3 V logic (SA818 AUDIO_ON, GPS 1PPS, LIS3DH INT1). | OK | none |
| 4.8 | INT sharing | INT is asserted by any input change (p16). | GPS_PPS (P17) pulses once per second while the GPS is on, so INT fires every second; RADIO_SQ toggles with carrier. | Low | Firmware: mask by reading; if the 1 Hz wake-ups are unwanted in light sleep, PPS could move to a spare pin later. No hardware change. |

## 5. WS2812B-2020-V6 RGB LEDs, D601 to D603

**Verdict: OK** (one low-battery note).

| # | Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|---|
| 5.1 | Supply range | p3 rated values: VDD +3.3 to +5.3 V; p1: "supports a 3.3 V power supply". | VBAT_SW = cell voltage 3.0 to 4.2 V (minus the AO3401A drop). Below 3.3 V (last 5-10 % of the cell) the LEDs are out of spec: blue/white dim and colour shift, data decoding may still work but is not guaranteed. | Low | Keep VBAT_SW. Firmware: dim or turn the LEDs off below about 3.4 V (VBAT is measured on GPIO39). |
| 5.2 | Data high level from 3.3 V logic | p3: VIH min 0.55 × VDD (2.31 V at 4.2 V), VI abs max VDD + 0.7 V. | ESP32 VOH ≥ 2.64 V (min, p29 note 2), typically 3.2 V. Margin ≥ 0.3 V even at a full cell. | OK | none (the older 0.7 VDD requirement no longer applies to the V6 part). |
| 5.3 | Series resistor on DIN | Typical application (p6) shows only the VDD capacitor; input capacitance 15 pF (p4). | R604 330 R in series with D601 DIN: τ = 5 ns, no effect on 220 ns pulses; also limits current into the unpowered LED (see 1.14). | OK | none |
| 5.4 | Decoupling | p6: "Cn is the filter capacitor for the LED's VDD pin, typically 100 nF". | C607-C609 100 nF on VBAT_SW, one per LED. | OK | Layout: each cap at its LED's VDD/GND pads. |
| 5.5 | Pin mapping | p2: 1 DO, 2 GND, 3 DI, 4 VDD. | KiCad symbol `LED:WS2812B-2020`: 1 DOUT, 2 VSS, 3 DIN, 4 VDD; netlist chain DOUT to next DIN, last DOUT NC. | OK | none |
| 5.6 | Timing | p5: T0H 220-380 ns, T1H 580-1000 ns, T0L/T1L 580-1000 ns, cycle ≥ 1.25 µs, reset ≥ 280 µs, GRB order. | RMT on GPIO15. | OK | Firmware: use the V6 timings above (T0H ≤ 380 ns; older 400 ns T0H works but is marginal). |
| 5.7 | Current | 12 mA per channel, 36 mA per LED white (p1, p4). | 3 LEDs = 108 mA worst case on VBAT_SW (design.md budgets 45 mA at reduced brightness). | OK | none |

## 6. IRM-H638T/TR2 IR receiver, U601

**Verdict: OK** (design.md text is stale).

| # | Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|---|
| 6.1 | Pin order vs footprint | p1 and p6: 1 GND, 2 GND, 3 OUT, 4 Vcc. KiCad `OptoDevice:Everlight_IRM-H6xxT` (pads 1-4) is drawn from this same document (footprint descr cites DMO-0000004 V4). | Custom symbol `LazerGamebox:IRM-H638T`: 1 GND, 2 GND, 3 OUT, 4 VCC; netlist U601.1/2 GND, .3 IR_RX, .4 filtered VCC. | OK | none |
| 6.2 | Supply and filter | p3: Vcc 2.7 to 5.5 V, Icc 1.0 typ / 2.0 mA max; p2: "RC filter should be connected closely between Vcc pin and GND pin" (values shown only in the figure; 100 R / 4.7 µF is the customary set for this series). | R605 100 R from LCD_3V3, C610 4.7 µF at pin 4. Drop across R605 at Icc max 2 mA = 0.2 V, so Vcc ≥ 3.1 V. | OK | Layout: C610 at pins 4 and 2. |
| 6.3 | Output pull-up and level | p3: VOH ≥ Vcc - 0.4 V at Isource ≤ 1 µA (weak internal pull-up only), VOL ≤ 0.5 V at 2 mA sink. | R606 10 k to LCD_3V3 (0.33 mA sink, fine); output referenced to 3.3 V goes to GPIO35 (VIH 0.75 × 3.3 = 2.48 V, VOH ≥ 2.9 V). | OK | none. Keep the pull-up on LCD_3V3 (not +3V3), otherwise +3V3 would back-feed the unpowered receiver through its output pin in sleep. |
| 6.4 | Which rail | Output swings to Vcc, so Vcc must not exceed the ESP32's 3.3 V. | Schematic: LCD_3V3 (correct). `docs/design.md` section 2 and 5 say VBAT_SW. | Low | Update design.md; the schematic is right. |
| 6.5 | Carrier and burst | 38 kHz part (p2 table); test bursts 400-800 µs high/low (p3). | Emitter driven at 38 kHz by RMT. | OK | Firmware: keep mark lengths ≥ 400 µs (10 to 20 carrier cycles minimum) for reliable demodulation. |
| 6.6 | Temperature | Topr -20 to +80 °C (p3). | Outdoor box. | Low | Note only. |

## 7. Tact switches, backlight driver Q601, IR emitter driver Q602 and VSMY2940G

**Verdict: change needed** (IR LED peak current exceeds the Vishay pulse rating at a full cell; IR base drive is soft).

| # | Item | Datasheet says | Schematic has | Severity | Recommended fix |
|---|---|---|---|---|---|
| 7.1 | SS8050 pinout and ratings | SOT-23: 1 B, 2 E, 3 C; IC max 1.5 A, PC 300 mW, hFE rank H 200-350 at IC = 100 mA / VCE = 1 V, hFE ≥ 40 at 800 mA, VCE(sat) ≤ 0.5 V at 800 mA / IB 80 mA (β forced 10) (p1). | Q601/Q602 pins 1 B (via 1 k), 2 E (GND), 3 C (load). | OK | none |
| 7.2 | Backlight Q601 base drive | Saturation needs forced β ≤ ~25. | R602 1 k from IO2: IB ≈ (3.2 - 0.85) / 1 k ≈ 2.3 mA (≥ 1.7 mA worst case). IC 25-60 mA gives forced β 11-35: saturated, VCE(sat) ≈ 0.1 V, dissipation < 10 mW. | OK | none |
| 7.3 | Backlight series resistor | Panel: 3 white LEDs in parallel, VF about 3.0-3.2 V (panel datasheet not reviewed). | R601 20 R 0805 from VBAT_SW: (4.2 - 3.0 - 0.1) / 20 ≈ 55 mA at 4.2 V, ≈ 15 mA at 3.4 V; 60 mW in the 0805 (125 mW). Matches the schematic note "25-60 mA". | OK | design.md section 2 still says 15 R / 80 mA: update. Brightness compensation by PWM vs VBAT as planned. |
| 7.4 | IR LED peak and average current | VSMY2940G p2: IF 100 mA continuous; IFM 200 mA at tp/T = 0.5, tp = 100 µs (this is exactly a 50 % carrier); IFSM 1 A single 100 µs pulse; PV 180 mW; RthJA 250 K/W; VF 1.4 V typ / 1.8 V max at 100 mA, 2.5 V at 1 A. | R607 10 R 1206 from VBAT_SW, 38 kHz 50 % carrier: at 4.2 V with VF ≈ 1.6 V and VCE ≈ 0.3 V the peak is ≈ 230 mA (above IFM 200 mA), average during a burst ≈ 115 mA (above IF 100 mA), LED power ≈ 185 mW (above PV 180 mW). At 3.0 V the peak is ≈ 120 mA, fine. | Medium | Either R607 = 12 R 1206 (≈ 190 mA peak at 4.2 V, ≈ 100 mA at 3.0 V) or keep 10 R and run the RMT carrier at 33 % duty (average 77 mA at 230 mA peak, within PV); combined with the existing rule of bursts ≤ 100 ms at low repetition. Verify the 12 R Basic code with `tools/jlc_search.py` before use. R607 dissipates ≈ 265 mW during a burst (1206 rated 250 mW) so bursts must stay short in any case. |
| 7.5 | IR driver Q602 base drive | For a hard saturation at 200 mA use forced β 20-30 (IB 7-10 mA); with IB 2.3 mA and hFE ≈ 200 the transistor is only just saturated, VCE ≈ 0.3-0.5 V, and the pulse current then depends on the hFE bin. | R608 1 k. Dissipation worst case 230 mA × 0.5 V × 50 % ≈ 60 mW, within 300 mW. | Low | R608 = 330 R (IB ≈ 7 mA, forced β ≈ 30; ESP32 pin sources ≤ 40 mA) for a predictable pulse current. |
| 7.6 | Reset and boot switches | EN RC 10 k / 1 µF and IO0 pull-up 10 k (see 1.2, 1.4). | SW201 EN to GND, SW202 IO0 to GND, no series resistors, same as DevKitC. | OK | none |
| 7.7 | User buttons | See 4.4. | SW601-603 to GND with 100 nF, expander pull-ups. | OK | none |

---

## Summary of recommended changes (most important first)

1. **Auto-reset polarity (high):** swap DTR/RTS on the SS8050 pair. Q201 (collector EN): base from DTR via R204, emitter to RTS. Q202 (collector IO0): base from RTS via R205, emitter to DTR. In `gen_mcu`: `("Q201","R204",66,"DTR","RTS","EN")` and `("Q202","R205",98,"RTS","DTR","IO0")`. As drawn, esptool can never enter download mode (only manual BOOT+RESET works).
2. **LIS3DH SA0 (high):** replace R209 10 k with a direct GND tie (0 R). The internal 20 k pull-up (Table 3, p9) leaves the pin at about 1.0 V, above VIL 0.66 V, so address 0x18 is not guaranteed.
3. **RADIO_EN default state (medium):** add R121 10 k pull-down on RADIO_EN at U104 EN. The TCA9555 powers up with all pins as inputs with 100 k pull-ups, which is above the TPS61023 EN threshold of 1.2 V, so the radio boost and SA818S-U are on at every power-up, reset and flash until firmware writes the expander.
4. **IR emitter current (medium):** at a full cell R607 10 R gives about 230 mA peak / 115 mA average at 50 % carrier, above the VSMY2940G IFM 200 mA (tp/T = 0.5), IF 100 mA and PV 180 mW. Use R607 = 12 R 1206, or keep 10 R and run the 38 kHz carrier at 33 % duty; keep bursts short (R607 runs at about 265 mW during a burst).
5. **UART0 back-feed (medium):** add 1 k series resistors R210 (U0TXD to U203 RXD) and R211 (U0RXD to U203 TXD), or confirm the CH340C lot code starts with 4 (anti-backflow I/O per datasheet p13). The CH340C is unpowered on battery while the ESP32 drives its RXD pin high.
6. **CH340C decoupling (low):** add C209 100 nF at U203 pin 16 (datasheet asks for 0.1 µF at the pin; C204 1 µF sits at the LDO).
7. **IR base drive (low):** R608 1 k to 330 R so Q602 saturates hard at 200 mA pulses.
8. **Firmware/docs (low):** configure the TCA9555 first thing after boot; RMT idle level low on LED_DATA and keep LCD_EN on whenever the SPI bus is active (drop it only for deep sleep after driving SCK/MOSI/LCD_DC low); stop RMT RX before dropping LCD_EN; dim the WS2812B below about 3.4 V (VDD spec 3.3 V min); software debounce on the expander buttons; update `docs/design.md` (no 22 R on USB D+/D-, IRM on LCD_3V3 not VBAT_SW, backlight resistor 20 R not 15 R).

Everything else checked matches the datasheets: ESP32 EN RC 10 k / 1 µF, 10 µF + 100 nF decoupling, strapping pins IO0/IO2/IO12/IO15/IO5 in the right states, input-only pins used as inputs, flash pins not exposed, UART0 crossed correctly; CH340C pin numbering, V3 tied to VCC, USB D+/D- without series resistors; LIS3DH CS high, pin 10 to GND, decoupling; TCA9555 address 0x20, INT 10 k pull-up; WS2812B-2020-V6 pin map, 3.3 V data level (VIH 0.55 VDD), 100 nF per LED; IRM-H638T pin order matches the KiCad footprint, 100 R / 4.7 µF filter, 10 k pull-up to LCD_3V3; backlight driver saturated with 20 R giving 25-55 mA.

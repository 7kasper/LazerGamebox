# Datasheet review of the schematic (2026-09-29)

Every important component was checked against its manufacturer datasheet (typical application
circuit, pin requirements, absolute maximums) and the exported netlist. The three detailed
reports with page citations are in `docs/review/` (power.md, mcu.md, rf_audio.md). This file
lists what was found, what was changed in the generator, and what stays as a firmware rule.

Severity: high = can damage a part or stop a function; medium = works but outside the
datasheet's recommended operating conditions; low = robustness or documentation.

## Changes applied to the schematic

| # | Sev | Component | Finding | Change |
|---|---|---|---|---|
| 1 | high | SA818S-U PTT | Module has no documented internal pull-up; with the open-drain driver PTT floated in "RX", and a floating PTT is reported to key the transmitter | R305 100 k from PTT to the 3.2 V PD node (follows the boost rail, so it cannot back-drive a dead module) |
| 2 | high | CH340C auto-reset | Transistor pair was cross-wired versus the DevKitC truth table; esptool could never enter download mode | Q201: base from DTR, emitter to RTS, collector EN. Q202: base from RTS, emitter to DTR, collector IO0 |
| 3 | high | LIS3DHTR SA0 | 10 k to GND against the 20 k internal pull-up leaves SA0 near 1 V, above VIL; address 0x18 not guaranteed | R209 changed to 0 R (hard tie) |
| 4 | medium | TPS61023 EN | TCA9555 ports power up as inputs with 100 k pull-ups, so the radio boost was on at every power-up, in the bootloader and after a crash | R121 4.7 k pull-down on RADIO_EN (0.15 V, below VEN_L 0.35 V) |
| 5 | medium | TPS61023 FB | Output capacitance is about 520 uF; TI requires a feed-forward capacitor above 40 uF | C113 1 nF across R113 |
| 6 | medium | Load sharing | Radio boost and the VBAT_SW switch drew from VBAT, bypassing the load-share FET; on USB the charger could never terminate | U104 VIN, L102, C109, C110 and Q107 now on VSYS. Q102 carries the 1.6 A peak (85 mR, 0.22 W bursts) |
| 7 | medium | Q102 gate | 100 k pull-down with 11 uF on VBUS gave tens of ms of body-diode operation after unplug: 3V3 sagged to an ESP32 brown-out | R108 4.7 k |
| 8 | medium | TP4056 PROG | 1.2 k programs 900 mA, not 1 A | R103 1.1 k (C22764, preferred) |
| 9 | medium | ATGM336H RXD | Input abs max is VCC + 0.2 V and GPS_3V3 is off most of the time while VBAT stays on | R411 1 k in GPS_TX at the module, plus firmware rule |
| 10 | medium | SA818S-U RXD | Datasheet asks for RXD low before power-down; UART2 TX idles high into a dead module | R306 1 k in RADIO_TX at the module, plus firmware rule |
| 11 | medium | NS4150B CTRL | Abs max VDD + 0.3 V and VBAT_SW is switched | R511 10 k in AMP_SD with R504 100 k on the chip side, plus sequencing rule |
| 12 | medium | CH340C UART0 | Unpowered chip on battery is back-fed by GPIO1 and the GPIO3 pull-up; anti-backflow I/O only on some lots | R210 and R211 1 k in U0RXD and U0TXD |
| 13 | medium | VSMY2940G | 10 R gave about 230 mA peak at 4.2 V; IFM is 200 mA at 50 % duty | R607 12 R 1206 (190 mA at 4.2 V, 100 mA at 3.0 V); bursts under 100 ms |
| 14 | medium | GPS antenna | An 18 mm patch on a 40 x 40 mm plane needs retuning | Pi pads C412 / R412 0 R / C413 between the DC block and the patch, shunts DNP |
| 15 | low | Q107 inrush | About 10 A into the 470 uF on VBAT_SW | R122 10 k in the gate pull-down path and C114 100 nF gate to source (about 1 ms edge) |
| 16 | low | Q602 base drive | 1 k gave forced beta 100 at 190 mA | R608 330 R |
| 17 | low | CH340C decoupling | 100 nF at the VCC pin required | C209 100 nF |
| 18 | low | TS5A3159 NO | Clamp diodes unprotected on the radio audio input | R512 1 k, mirroring R501 |
| 19 | low | Source-switch thump | 1 uF couplers charge slowly through 220 k when the mux switches | C501 and C503 100 nF |
| 20 | low | TPS62A02 divider | 100 k / 22 k drew 27 uA, more than the buck's own Iq | R111 / R112 150 k / 33 k (3.33 V) |
| 21 | low | TPS62A02 Cout | 44 uF was at the edge of the characterised range | C108 10 uF (total 32 uF) |
| 22 | low | Notes | DW01A thresholds are 2.5 / 4.3 V, PD is a divider not a tie, RADIO_4V5 is 4.6 V, no bead pads, no 22 R on USB, IRM is on LCD_3V3, backlight is 20 R | design.md and sheet notes corrected |

## Verified correct, no change

- ESP32: EN RC 10 k / 1 uF, decoupling, strapping states (IO0 pull-up, IO2 pull-down, IO12
  floating, IO5 and IO15 internal pull-ups with high-impedance loads), input-only pins used as
  inputs, flash pins not exposed, UART0 crossed correctly, auto-reset resistor values.
- DW01A + FS8205A: matches the typical circuit exactly; OCP 2 to 4 A versus a 1.6 A budget.
- TPS62A02: EN to VIN, inductor and capacitor values, PG open. XC6206 caps and load. USBLC6
  orientation. Type-C pin table, dual 5.1 k Rd, shield to GND. SS34 only carries the buck input.
- AO3401A load switches: gate drive and drop (64 mV worst case at 750 mA).
- SA818S-U: pin numbering, 4.6 V supply inside 3.3 to 5.5 V, PD divider level, H/L handling,
  Audio-ON polarity, UART levels, 470 uF bulk, TX current budget, MIC_IN level (33 mVpp full
  scale equals the rated 10 mV deviation sensitivity at about 30 %), AF_OUT to ADC bias network.
- Ra-01SH: pin numbering, TXEN/RXEN open with DIO2 as RF switch, SPI and control pins, supply.
- ATGM336H: pin numbering, VCC and V_BCKP, ON_OFF pull-up, RESET may float, RF_IN carries no DC
  (bias comes from the separate VCC_RF pin), UART levels.
- NS4150B and TS5A3159: pin numbering, gain 2.2, bypass, VCC range, select polarity.
- TCA9555: address, INT pull-up, decoupling, button inputs with 100 nF against the 100 k pull-ups
  (software debounce still needed). WS2812B-2020-V6: 3.3 V data is valid, 100 nF each, 330 R.
- IRM-H638T: pin order matches symbol and footprint, supply filter, 10 k pull-up to LCD_3V3.
- All antennas and the SMA are passive.

## Power block redesign (2026-09-29, after the review)

The TP4056, SS34 and AO3401A load-share FET were replaced by a BQ25601 charger with NVDC
power path, plus a HUSB238 USB PD sink and a MAX17048 fuel gauge, and a second 18650 holder
was added in parallel. The three new parts were drawn from their datasheet extracts
(docs/review/bq25601_spec.md, husb238_spec.md, max17048_spec.md) and then given the same
independent review (docs/review/power_block_v2.md). Items 6 and 7 above (load sharing, Q102
gate) no longer apply. Second-review results: one high finding, a duplicate reference L101
on the charger and buck inductors that the netlist silently merged (renamed L103, the
generator now refuses duplicate references); STAT LED resistor 1 k; PWR_INT moved from the
expander to GPIO39 (RTC wake, direct edge interrupt) which gives P17 back to GPS 1PPS; sleep
current corrected to about 115 uA. Everything else matched the datasheets: all pins and pads
of the three parts, capacitor values and ratings, inductor margin, PSEL strap, TS window at
50 % of REGN, SYS supplement for the 1.6 A peak, protector thresholds, USB-C ratings.
Datasheet-driven choices:

- BQ25601: PSEL strapped to VBUS through 10 k so a fresh plug-in draws 500 mA until firmware
  programs IINDPM; /CE to GND; TS satisfied by 10 k / 10 k from REGN (no NTC in the holders);
  47 nF BTST, 2x 10 uF PMID, 2x 10 uF SYS, 10 uF BAT, 4.7 uF REGN, 1 uH with 5.7 A saturation;
  STAT LED through 2.2 k from VSYS; /INT to the expander with 10 k; /PG open; QON to a
  dedicated PWR tact switch (hold about 1 s to leave ship mode, 8 s without USB for a full
  BATFET reset).
- HUSB238: VSET and ISET 0 R (5 V, 1.25 A request, which matches every 5 V PDO); GATE and
  D+/D- open (the CH340C owns D+/D-); Rd is internal, so the two 5.1 k resistors are gone;
  330 R in series with its I2C pins because the chip is unpowered without USB and the datasheet
  does not specify bus loading in that state.
- MAX17048: VDD and CELL on VBAT with 100 nF, CTG, QSTRT and pad to GND, ALRT wire-ORed with
  the charger interrupt on PWR_INT (GPIO39). I2C pins are rated independent of VDD, so no level shifting.

## Firmware rules the hardware depends on

0. Charger and gauge: after any boot or PWR_INT, read the HUSB238 (PD_STATUS1 5V_CURRENT or
   SRC_PDO_5V) and write the BQ25601 IINDPM accordingly (500 mA default, up to 3 A); clear
   EN_HIZ after a QON wake; feed or disable the 40 s I2C watchdog; keep ICHG at 2 A, VREG at
   4.208 V; enter ship mode with BATFET_DIS for storage. Update the MAX17048 RCOMP with
   temperature about once a minute and clear ALRT after servicing it. Expect NACKs from the
   HUSB238 whenever USB is unplugged. Never request anything but the 5 V PDO from the
   HUSB238 over I2C (the USBLC6 and the XC6206 are 6 V parts, the charger OVP is 6.5 V).
   Handle CHRG_FAULT = 11 (10 h safety timer) on weak sources; optionally set VINDPM to
   4.3 V for full 2 A on long cables; set MAX17048 VRESET to 2.5 V for the captive pack.
   Bench check once: with USB unplugged, confirm the unpowered HUSB238 does not load SDA/SCL
   (R125/R126 can be left unfitted if it does).

1. Write the TCA9555 configuration and outputs first after boot. Until then all enables are
   held low by the pull-downs.
2. AUX_EN on a few ms before AMP_SD high; AMP_SD low before AUX_EN off.
3. GPIO17 (RADIO_TX) low or input before RADIO_EN goes low; wait 300 to 500 ms after RADIO_EN
   goes high before the first AT command.
4. GPIO14 (GPS_TX) low or input while GPS_EN is low.
5. Keep LCD_EN on whenever SPI is active; before deep sleep drive SCK, MOSI and LCD_DC low.
   Stop RMT receive before dropping LCD_EN (IR_RX floats).
6. IR carrier 38 kHz at 50 % duty or less; bursts under 100 ms; R607 dissipates about 0.27 W
   during a burst.
7. DTMF at 50 to 70 % DAC amplitude; full-scale DAC into the amplifier clips (gain 2.2).
8. Dim the WS2812B below a 3.4 V cell (VDD spec 3.3 V minimum).
9. `setDio2AsRfSwitch(true)` on the SX1262; the Ra-01SH is a crystal module, no TCXO.
10. Ignore the ATGM336H "ANTENNA OPEN" text sentence with a passive antenna.

## Layout notes carried forward

- TP4056 exposed pad on a large via-stitched ground pour; expect fold-back to about 0.7 A anyway.
- Solid ground under the SA818S-U with thermal vias under the ground pads; firmware TX time
  limits at 1 W. Confirm pads 19 and 20 are ground on a physical module before ordering.
- 470 uF (C303) within a few mm of the SA818S-U VBAT pad; C505 next to the NS4150B.
- GPS patch on a 40 x 40 mm ground, 15 mm or more from the UHF and LoRa antennas.
- Optional 33 R in series on SCK and MOSI at the ESP32 (shared bus, ringing).

# Game Box PCB: design document (step 1, for review)

Status: **step 2 done, schematic drawn (hardware/), ERC clean, layout not started.** Decisions from the
review round are folded in below (section 0). Every LCSC number below was checked
against the JLCPCB assembly parts API on 2026-09-28 (stock and price at that moment,
scripts in `tools/jlc_search.py` and `tools/jlc_ds.py`). Prices are USD at the tier
reached when buying 25 pcs; EUR figures use 0.92 EUR/USD.

CONFIG as given (unchanged, but see open questions 1 and 2):

```
RADIO_UHF    = SA818          (fitted part: G-NiceRF SA818S-U, drop-in successor)
LORA_SEP     = yes            (Ai-Thinker Ra-01SH, SX1262, 868 MHz)
GPS          = yes            (ATGM336H-5N31 + 18x18 ceramic patch)
CELLULAR_DNP = yes            (SIM7080G footprint + nano-SIM + antenna, all DNP)
DISPLAY      = ST7789_320x240_2.0in (HS20HS072RX, approved substitute; 240x240 not stocked)
POT_STYLE    = THT_POT        (Alps RK09K 10k, 15 mm flat shaft)
TARGET_BOM_EUR = 40
```

## 0. Decisions from the review (2026-09-28) and what changed

| Topic | Decision | Effect on the design |
|---|---|---|
| Display | 2.0" HS20HS072RX 320x240 accepted | 12-pin ZIF J601, backlight from VBAT_SW via 20 R + NPN PWM |
| Radio | SA818S-U accepted | U301 |
| GPIO shortage | TCA9555 expander accepted, buttons on it are fine | U205 on I2C, INT on GPIO32 |
| Speaker | THT is fine (SMA, antennas and pot are THT anyway) | FS-3013 30 mm, 1 W |
| SMA | KWE right-angle THT | J301 |
| IR | laser-tag range | Vishay VSMY2940G 75 mW/sr, 12 R / 1206, about 100-190 mA pulses (datasheet review 2026-09-29) |
| Radio supply | boost preferred | TPS61023 boost to 4.6 V with true disconnect (EN = RADIO_EN), replaces the radio load switch. Costs about 55 % more input current only while transmitting |
| Buck | lower Iq preferred | TPS62A02 (23 uA Iq, 2 A) replaces SY8089A1; sleep estimate now about 55 uA |
| Charging | faster | PROG 1.1k = 1 A (1.2k is 900 mA per the TP4056 table). Superseded on 2026-09-29, see next rows |
| Cells (2026-09-29) | two 18650 in parallel for a full day of play | BT101 + BT102 on one 1S rail; nothing else changes electrically. About 4000 mAh, 3500 usable |
| Charger (2026-09-29) | negotiated 2 A USB-C charge, integrated battery management | BQ25601 (switching, NVDC power path, ship mode, I2C 0x6B) replaces TP4056, SS34 and the AO3401A load-share FET. HUSB238 PD sink (I2C 0x08) reports the source's 5 V current so firmware sets the input limit; 5 V only, never 9 V. MAX17048 fuel gauge (I2C 0x36) replaces the VBAT divider, GPIO39 is now free. New PWR button on QON (wake from ship mode). Charger INT + gauge ALRT go to GPIO39 (PWR_INT, RTC wake); the expander keeps GPS 1PPS |
| Expansion (2026-09-29) | spare IO wanted for game gadgets | second TCA9555 (U602, 0x21) with EXP0-9 on a 2x10 header J602 (GND, +3V3, VBAT_SW, VSYS, SDA, SCL, EXP0-9, OUT1, OUT2, GND), two AO3400A low-side drivers with SS34 flyback for motors or solenoids up to 2 A; INT shared with the first expander on GPIO32 |
| Datasheet review (2026-09-29) | all findings applied, see docs/review.md | 22 component changes: PTT pull-up, RADIO_EN pull-down, boost and VBAT_SW fed from VSYS, series resistors on UART lines into switched modules, auto-reset polarity fixed, LIS3DH SA0 tied hard, IR drive limits, soft start, feed-forward cap, GPS pi pads |
| Flash | 16 MB | ESP32-WROOM-32E-N16 |
| Board sides | battery and most parts on the back, screen/buttons/pot/LEDs/IR on the front | two-sided SMT assembly; the 5 THT parts (speaker, SMA, 2 antennas, pot) can be JLC-assembled or hand-soldered |
| USB serial | (new) CH340C gets its own XC6206 3.3 V LDO on VBUS | never drives 5 V into the ESP32, dead on battery |

Schematic sources: `hardware/LazerGamebox.kicad_sch` (root) + `power`, `mcu`, `radio`, `lora_gps`, `audio`, `io`.
PDF: `hardware/reports/LazerGamebox_schematic.pdf`. ERC: `hardware/reports/erc.json` (0 errors, 0 warnings).
Pin map regenerated from the netlist: `docs/pinmap.md` (`python tools/check_pinmap.py`).
Libraries: every part has a symbol, a footprint and a STEP model. Standard packages and connectors use KiCad's own
footprints and models; JLC-specific modules, antennas, holder, speaker, ZIF, SIM socket and IR LED were imported from
the LCSC/EasyEDA library (`hardware/lib/LazerGamebox_lcsc.*`) with their STEP files. The ZIF's STEP is a Hirose
FH12-12S stand-in (same size, EasyEDA has no model for it).

---

## 1. Block diagram

```
                 USB-C 16p --ESD--+-- XC6206 3V3 --> CH340C -- 1k -- UART0 --+
                 (5 V VBUS)       |   + 2x SS8050 autoreset (DTR/RTS)         |
                                  |                                           |
   VBUS -->BQ25601 charger + NVDC power path (I2C) --> VSYS            v
    |       |  2 A charge, 500 mA default input limit,   +--> TPS62A02 buck --> +3V3 (always on) --> ESP32-WROOM-32E-N16
    |       |  ship mode, PWR button on QON, STAT LED    |                         |  (VSPI, I2C, UART1/2,
    |       v                                            |                         |   DAC1, ADC1, RMT)
    |     VBAT <-- 2x 18650 in parallel, DW01A+FS8205A   |                         |
    |       +-- MAX17048 fuel gauge (I2C)                |                         +-- I2C --> TCA9555 16-bit expander
    +-->HUSB238 PD sink on CC1/CC2 (I2C): source 5 V current capability
                             |
                             +-->TPS61023 boost "RADIO_EN" --> RADIO_4V5 (4.6 V) --> SA818S-U --> CPW --> SMA
                             |   (4.7k pull-down on EN)      470 uF + 10 uF + 100 nF   |  <-- UART2 (1k), PTT
                             |                                                         |  --> AF_OUT, SQ
                             +-->AO3401A "AUX_EN" (RC soft start) --> VBAT_SW --> NS4150B class-D --> speaker
                             |                                             --> 3x WS2812B-2020, IR LED, LCD backlight
                             |
   VBAT ------------------------>(DNP) SIM7080G + nano-SIM + spring antenna, 1.8 V level shifters, PWRKEY

   +3V3 -->AO3401A "GPS_EN" --> GPS_3V3 --> ATGM336H-5N31 <-- UART1 (1k) --> pi pads --> 18x18 patch
   +3V3 -->AO3401A "LCD_EN" --> LCD_3V3 --> ST7789 panel, pot, IRM-H638T IR receiver
   +3V3 -->AO3401A "LCD_EN" --> LCD_3V3 --> 2.0" ST7789 320x240 via 12p 0.5 mm ZIF, + 10k pot
   +3V3 ------------------------------> Ra-01SH LoRa (VSPI, own CS, DIO1, BUSY) --> 868 spring ant.
   +3V3 ------------------------------> LIS3DHTR (I2C, INT1 --> expander --> GPIO32 wake)

   Audio:  DAC1 (GPIO25) -+-> TS5A3159 mux <-- radio AF_OUT --> 1 uF --> 220k --> NS4150B INP
                          +-> 100k/1k divider --> 1 uF --> radio MIC_IN
           radio AF_OUT --> 47k --> 1 uF --> 100k/100k bias 1.65 V --> 10k/1nF --> ADC1 GPIO36
```

Six hierarchical sheets, as requested: `power`, `mcu`, `radio`, `lora_gps`, `audio`, `io`
(io = display, buttons, pot, LEDs, IR, accelerometer, expander, cellular DNP block).

---

## 2. Power architecture

| Rail | Source | Switch | Loads | Notes |
|---|---|---|---|---|
| VBUS | USB-C | none | BQ25601 VBUS/VAC, HUSB238 VIN, CH340C LDO, PSEL strap | CC1/CC2 go to the HUSB238 (Rd inside it), USBLC6-2SC6 clamps VBUS and D+/D- |
| VBAT | 2x 18650 in parallel via DW01A + FS8205A | none | BQ25601 BAT, MAX17048, (DNP) SIM7080G | 2.5 V UVLO, 4.3 V OVP, 2 to 4 A OCP from the protector; BQ25601 charges to 4.208 V, 2 A, 180 mA termination |
| VSYS | BQ25601 SYS (NVDC power path) | BATFET: ship mode = true off, exit by USB plug or PWR button | buck input, radio boost input, VBAT_SW switch, STAT LED | runs from USB when present (cells supplement peaks), from the cells otherwise; SYS_MIN 3.5 V |
| +3V3 | TPS62A02, 1 uH SWPA4030, 22 uF + 10 uF | always on | ESP32, LoRa, LIS3DH, expander, GPS backup pin, I2C pull-ups | 2 A, 2.4 MHz, Iq 23 uA, FB 0.6 V: RH 150k / RL 33k gives 3.33 V |
| RADIO_4V5 | VSYS via TPS61023 boost | boost EN = RADIO_EN, 4.7 k pull-down (off at power-up) | SA818S-U | 4.6 V (220k / 33k, 1 nF feed-forward); 470 uF/10 V electrolytic + 10 uF + 100 nF at the module; true disconnect when EN is low |
| VBAT_SW | VSYS | AO3401A + 2N7002 (AUX_EN), 10 k + 100 nF gate soft start | NS4150B, 3x WS2812B, IR LED, LCD backlight | 470 uF + 10 uF; everything that must be dead in sleep and likes more than 3.3 V |
| GPS_3V3 | +3V3 | AO3401A + 2N7002 (GPS_EN) | ATGM336H VCC | GPS VBAT backup pin on +3V3 (10 uA) for hot start |
| LCD_3V3 | +3V3 | AO3401A + 2N7002 (LCD_EN) | ST7789 VCC/IOVCC, 10 k pot | pot on the switched rail so it draws nothing in sleep |
| CELL_VBAT (DNP) | VBAT | none (PWRKEY controls the module) | SIM7080G | 2x 100 uF DNP |

Load switch cell: P-channel AO3401A (JLC Basic) high side, 100 k gate pull-up to source,
2N7002 (Basic) pulls the gate low, 10 k pull-down on the 2N7002 gate. Result: **all switched
rails default OFF** at power-up until firmware enables them. SiP32431 is not used (only 15
pieces in stock in SOT-363).

### Power budget

| Mode | +3V3 loads | VBAT direct loads | Cell current (buck 90 %) | Note |
|---|---|---|---|---|
| Deep sleep | ESP32 10 uA, LoRa sleep 1 uA, LIS3DH 2 uA (low power), TCA9555 1 uA, GPS backup 10 uA | buck Iq 23 uA, BQ25601 battery-only 58 uA typ (85 max), MAX17048 hibernate 3 uA, DW01A 3 uA | **about 115 uA** (up to 150) | all switched rails off. The BQ25601 BATFET path costs about 35 uA more than the old TP4056 design. Ship mode (BATFET open) about 24 uA for storage |
| Standby, screen on | ESP32 (Wi-Fi off) 40 mA, LCD logic 10 mA, LoRa RX 5 mA | backlight 30 mA | about 85 mA | about 40 h on 2P |
| Standby with radio listening | as above | SA818S-U RX 60 mA at 4.6 V = 83 mA at the cell | about 170 mA | about 20 h on 2P |
| Game, LoRa only | ESP32 50 mA, GPS 25 mA, LoRa 10 mA, LCD 10 mA | radio RX 83 mA, backlight 40 mA, 3x WS2812 45 mA, IRM 1.2 mA | about 260 mA | about 13 h on 2P |
| Game with Wi-Fi | ESP32 Wi-Fi 150 mA, GPS 25 mA, LoRa RX 10 mA, LCD 10 mA | as above | about 360 mA | about 10 h on 2P, 7.5 h with 10 % radio TX time |
| Peak | ESP32 Wi-Fi TX 400 mA | radio TX high 750 mA at 4.6 V, amp 1 W into 8 ohm about 400 mA | about 1.6 A | within the cells, the protector (2 to 4 A) and the BQ25601 BATFET (6 A) limits |

Two cells in parallel (about 4000 mAh, 3500 usable) give a full day of play when firmware keeps the radio
powered only while a channel is in use and prefers LoRa over Wi-Fi during play (about 100 to 130 mA, 25 to 30 h).
Charging: 2 A from a 3 A USB-C source (about 2.5 h from empty), 500 mA from a laptop port.

Backlight: the panel has 3 white LEDs in parallel (LEDA/LEDK). They run from VBAT_SW
through 15 ohm and an SS8050 low-side switch driven by the LCD_BL PWM. Brightness varies
with cell voltage (4.2 V about 80 mA, 3.4 V about 25 mA); firmware can compensate using
the VBAT reading.

---

## 3. Pin map

The brief lists roughly 40 MCU signals; the ESP32-WROOM-32E exposes 26 usable GPIO
(0, 1, 2, 3, 4, 5, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33, 34, 35,
36, 39). **Proposal: everything that needs speed, PWM, RMT, SPI, UART or ADC stays on the
ESP32; slow enables, resets, mux select, buttons and three slow interrupts move to a TCA9555
I2C expander** (0.59 USD, 39 k in stock). Its open-drain INT pin lands on GPIO32 (RTC
capable) so buttons and motion still wake the ESP32 from deep sleep. See OQ 3 before I
draw this.

### ESP32-WROOM-32E

| GPIO | Net | Dir | Function | Why this pin |
|---|---|---|---|---|
| 0 | BOOT | in | boot button (also usable as a 4th button at runtime) | strapping, 10 k pull-up |
| 1 | U0TXD | out | CH340C RXD | UART0 programming |
| 3 | U0RXD | in | CH340C TXD | UART0 programming |
| 2 | LCD_BL | out | backlight PWM via SS8050 | strapping: 10 k pull-down keeps it low at boot |
| 4 | LORA_BUSY | in | SX1262 BUSY | plain input, read before every SPI command |
| 5 | LORA_CS | out | Ra-01SH NSS | strapping pin with internal pull-up at boot = CS idle high |
| 12 | LCD_DC | out | ST7789 RS (data/command) | MTDI must not be pulled high at boot; the display never drives this line |
| 13 | GPS_RX | in | ATGM336H TXD (UART1 RX) | also SIM7080G UART1_TXD via 0 ohm DNP |
| 14 | GPS_TX | out | ATGM336H RXD (UART1 TX) via 1 k | also SIM7080G UART1_RXD via 0 ohm DNP; firmware drives it low while GPS_EN is off |
| 15 | LED_DATA | out | WS2812B chain (RMT) | strapping (pull-up default, harmless for LED DIN) |
| 16 | RADIO_RX | in | SA818S-U TXD (UART2 RX) | |
| 17 | RADIO_TX | out | SA818S-U RXD (UART2 TX) via 1 k | firmware drives it low before RADIO_EN goes off and waits 300 to 500 ms after power-up (datasheet note) |
| 18 | SCK | out | VSPI clock | LoRa + display |
| 19 | MISO | in | VSPI MISO | LoRa only |
| 21 | SDA | bi | I2C data | LIS3DH 0x18, TCA9555 0x20, 4.7 k pull-ups |
| 22 | SCL | out | I2C clock | |
| 23 | MOSI | out | VSPI MOSI | LoRa + display SDA |
| 25 | DAC1 | out | audio out (DAC) | fixed by silicon |
| 26 | IR_TX | out | IR LED, 38 kHz via RMT, SS8050 (330 R base) + 12 R from VBAT_SW | DAC2 pin, unused as DAC. About 190 mA peak at 4.2 V, bursts under 100 ms |
| 27 | RADIO_PTT | out | 2N7002 open-drain inverter to SA818S-U PTT (GPIO high = PTT low = TX) | 100 k pull-up from PTT to the 3.2 V PD node keeps RX when the ESP32 sleeps; nothing back-drives a dead module |
| 32 | EXP_INT | in | TCA9555 INT (buttons, motion, SQ, PPS) | RTC GPIO: ext0 wake source |
| 33 | LORA_DIO1 | in | SX1262 IRQ | RTC GPIO: can wake on a LoRa packet |
| 34 | ADC_POT | in | pot wiper, ADC1_CH6 | input only, RC 10 k / 100 nF |
| 35 | IR_RX | in | IRM-H638T OUT (RMT RX) | input only; 36 and 39 avoided for digital use (ESP32 errata glitch) |
| 36 | ADC_AUDIO | in | radio AF_OUT biased at 1.65 V, ADC1_CH0 | Goertzel DTMF |
| 39 | PWR_INT | in | BQ25601 /INT (256 us pulse) wire-ORed with MAX17048 ALRT, 10 k pull-up | RTC GPIO: wakes from deep sleep on USB plug/unplug, charge events and low battery |

All analog inputs on ADC1, strapping pins hold nothing at boot, UART0 free, GPIO12 never
pulled high. Spare pins: none, all 26 are taken.

### TCA9555 I2C expander (address 0x20, INT to GPIO32)

| Pin | Net | Dir | Function |
|---|---|---|---|
| P00 | RADIO_EN | out | SA818 load switch |
| P01 | GPS_EN | out | GPS load switch |
| P02 | LCD_EN | out | display + pot load switch |
| P03 | AUX_EN | out | VBAT_SW: amp, LEDs, IR, backlight supply |
| P04 | AMP_SD | out | NS4150B CTRL (low = shutdown) |
| P05 | MUX_SEL | out | TS5A3159: DAC (0) or radio AF_OUT (1) to the amp |
| P06 | LCD_CS | out | ST7789 chip select (set once per frame; LoRa keeps its own fast CS) |
| P07 | LCD_RST | out | ST7789 reset |
| P10 | LORA_RST | out | SX1262 NRESET |
| P11 | CELL_PWRKEY | out | SIM7080G PWRKEY via NPN (DNP) |
| P12 | BTN1 | in | tact switch to GND (internal 100 k pull-up) |
| P13 | BTN2 | in | |
| P14 | BTN3 | in | |
| P15 | RADIO_SQ | in | SA818 "Audio ON" pin (low = carrier, squelch open) |
| P16 | ACC_INT1 | in | LIS3DH wake-on-motion, reaches GPIO32 through INT |
| P17 | GPS_PPS | in | 1PPS, edge visible through INT (about 0.2 ms latency) |

Deviations from the brief caused by the pin shortage: LIS3DH INT1, radio SQ, GPS PPS,
display CS and RST and the amp shutdown reach the ESP32 through the expander instead of a
direct GPIO. Radio PTT, LoRa DIO1 and BUSY, IR, LEDs, backlight PWM and all ADCs stay direct.

`docs/pinmap.md` holds the same tables and will be regenerated from the schematic.

---

## 4. Part selection (LCSC numbers verified 2026-09-28)

Lib: **B** = JLC Basic (no loading fee), **P** = Preferred extended (no fee), **E** =
Extended (about 3 USD fee per part number per order). KiCad column: "lib" = stock KiCad 10
symbol and footprint usable as is, "custom" = drawn from the datasheet.

### Modules and ICs

| Ref | Part | LCSC | Lib | Stock | USD @25 | KiCad | Notes |
|---|---|---|---|---|---|---|---|
| U201 | ESP32-WROOM-32E-N16 | C701343 | E | 9 871 | 4.46 | lib | classic ESP32 with DAC pins, 16 MB flash for sound storage |
| U2 | G-NiceRF **SA818S-U** | C3001549 | E | **34** | 9.49 | custom | SA818 successor, same footprint, pinout and AT set (datasheet: "interfaces the same as before"). 400-480 MHz, 1 W, 3.3-5.5 V. Stock tight, see sourcing.md |
| U3 | Ai-Thinker Ra-01SH (SX1262) | C2764087 | E | 1 904 | 3.92 | lib (Ra-01 footprint, same 16 pads, 17x16 mm, 2.0 mm pitch) | RF switch driven internally by DIO2 (setDio2AsRfSwitch); TXEN and RXEN pads left NC |
| U4 | ZHONGKEWEI ATGM336H-5N31 | C90770 | E | 11 120 | 2.87 | custom (LCC-18, 10.1x9.7 mm) | passive antenna on RF_IN, VCC_RF unused |
| U5 | SIMCom SIM7080G | C2943992 | E, **DNP** | 932 | (13.03) | custom (77-pad LGA) | 1.8 V UART, needs level shift; package compatible with the SIM868/SIM800C family |
| U6 | ST LIS3DHTR | C15134 | E | 1 210 | 1.58 | lib | I2C mode (CS high, SA0 to GND through 0 R because of its 20 k internal pull-up, address 0x18) |
| U7 | WCH CH340C | C84681 | E | 141 858 | 0.51 | lib | internal oscillator, no crystal |
| U8 | Nsiway NS4150B | C189961 | E | 157 685 | 0.15 | custom symbol, MSOP-8 footprint | gain = 2 x 240 k / Rin, Rin 220 k gives 2.2 |
| U9 | TI TS5A3159DCKR | C46388 | E | 40 715 | 0.37 | lib | SC-70-6 SPDT audio mux |
| U10 | TI TCA9555PWR | C465732 | E | 39 363 | 0.59 | lib | 16-bit I2C expander with INT |
| U101 | TI BQ25601RTWR | C468236 | E | 6 094 | 1.00 | custom symbol, LCSC WQFN-24 footprint with STEP | 3 A switching 1S charger, NVDC power path, ship mode, I2C 0x6B. 1 uH SWPA4030 (Isat 5.7 A), 2x 10 uF PMID, 2x 10 uF SYS, 10 uF BAT, 4.7 uF REGN, 47 nF BTST, TS 10 k / 10 k, PSEL 10 k to VBUS |
| U105 | Hynetek HUSB238_002DD | C7471904 | E | 8 650 | 0.47 | custom symbol, LCSC DFN-10 footprint with STEP | PD sink, VSET and ISET 0 R (5 V, 1.25 A request), I2C 0x08 through 330 R, runs from VBUS only |
| U106 | Maxim MAX17048G+T10 | C2682616 | E | 24 759 | 1.92 | custom symbol, LCSC TDFN-8 footprint with STEP | ModelGauge fuel gauge on the cell pair, I2C 0x36, ALRT to PWR_INT |
| U12 | PUOLOP DW01A | C351410 | E | 116 947 | 0.04 | lib | |
| Q1 | FUXINSEMI FS8205A | C908265 | E | 22 478 | 0.07 | custom symbol, SOT-23-6 footprint | dual N-FET for DW01A |
| U103 | TI TPS62A02DRLR | C5350187 | E | 33 628 | 0.08 | lib (SOT-563) | 3V3 buck, 2 A, 2.4 MHz, Iq 23 uA (replaces SY8089A1) |
| U104 | TI TPS61023DRLR | C919459 | E | 36 746 | 0.25 | custom symbol, SOT-563 | radio boost 4.6 V, 3.7 A switch, true disconnect |
| U202 | Torex XC6206P332MR-G | C5446 | **B** | 480 132 | 0.14 | lib | 3.3 V LDO for the CH340C |
| L101, L102, L103 | Sunlord SWPA4030S1R0NT 1 uH | C42193 | E | 9 505 | 0.06 | lib 4x4 mm | Isat 5.7 A, one part number for buck, boost and charger |

### Connectors, electromechanical, RF

| Ref | Part | LCSC | Lib | Stock | USD @25 | KiCad | Notes |
|---|---|---|---|---|---|---|---|
| J1 | Korean Hroparts TYPE-C-31-M-12 (16 p) | C165948 | E | 446 427 | 0.19 | lib (HRO_TYPE-C-31-M-12) | |
| D1 | ST USBLC6-2SC6 | C7519 | E | 44 699 | 0.18 | lib | |
| BT101, BT102 | MYOUNG BH-18650-B1BA002, SMT, gold | C2988620 | E | 4 430 | 2x 1.27 | custom (86 x 20.7 mm, two 7.8 x 8 mm pads, 2.4 mm locating hole) | two holders in parallel, reflow; about 86 x 43 mm of the back side |
| LS1 | FUET FS-3013 speaker, 30 mm, 8 ohm, 1 W, 90 dB | C482323 | E | 552 | 1.06 | custom (2 pins, 15 mm pitch, 13 mm tall) | THT. Largest 8 ohm PCB-mount speaker JLC stocks. SMD fallback: KELIKING KLJ-01304T-08R07W C18186315, 13x13x4 mm, 0.7 W, 87 dB, 1.52 USD |
| DS1 | HS **HS20HS072RX** 2.0" IPS 320x240 ST7789V2, 12-pin 0.5 mm FPC | C5329582 | E | 2 244 | 3.05 | n/a (panel, off board) | substitute for the 1.3"/1.54" 240x240, see OQ 1. Pins: 1 GND, 2 CS, 3 RS, 4 SCL, 5 SDA, 6 RST, 7 NC, 8 IOVCC, 9 VCC, 10 LEDA, 11 LEDK, 12 GND |
| J2 | HanElectricity 05A20H12P, 0.5 mm 12 p flip lock, **dual-side contacts** | C5362174 | E | 1 225 | 0.12 | custom | dual contact, so the FPC contact side does not matter |
| ANT1 | BAT WIRELESS BWSMA-KWE-Z001 SMA right angle | C496551 | E | 162 353 | 0.41 | lib (exact footprint) | THT, at the board edge; whip fitted by hand. True edge-launch alternative: ZIISOR SMA-KE-10 C2987686 (OQ 6) |
| ANT2 | BAT WIRELESS BW868SNX20-5Z6 spring, 868 MHz, 20 mm | C496555 | E | 1 030 | 0.15 | custom (1 pin) | THT. SMD alternative: Rainsun AN1603-868 C115720 (1.40 USD, needs matching) |
| ANT3 | BAT WIRELESS BWGNSCNX18-18W4 ceramic patch 18x18x4 | C784395 | E | 1 800 | 0.57 | custom (1 pin + keepout) | THT pin. Needs about 40 x 40 mm ground under it |
| RV1 | Alps RK09K1130A6S 10 k linear, 15 mm flat shaft, vertical | C209770 | E | 3 975 | 0.48 | lib (RK09K_Single_Vertical) | THT |
| SW101, SW201, SW202, SW601-603 | XKB TS-1187A-B-A-B 5.1 mm tact | C318884 | **B** | 550 693 | 0.02 | lib | PWR (QON) + boot + reset + 3 user |
| LED1-3 | Worldsemi WS2812B-2020-V6 | C52917434 | E | 784 830 | 0.09 | lib | powered from VBAT_SW |
| U14 | Everlight IRM-H638T/TR2 38 kHz | C91447 | E | 185 891 | 0.26 | lib (Everlight_IRM-H6xxT) | pins 1 GND, 2 GND, 3 OUT, 4 VCC; 100 ohm + 4.7 uF filter |
| D604 | Vishay VSMY2940G 940 nm, 10 deg, 75 mW/sr at 100 mA | C499547 | E | 5 699 | 0.76 | LCSC import with STEP | laser-tag emitter, 12 R 1206 series (190 mA peak, IFM 200 mA at 50 %), SS8050 driver with 330 R base |
| J3 | SHOU HAN NANO SIM XG6P H1.35 | C7529386 | E, DNP | 38 598 | (0.15) | custom | |
| ANT4 | DreamLNK T10 GSM spring 900/1800 MHz | C381192 | E, DNP | 229 | (0.20) | custom | |

### Discretes and passives (all JLC Basic unless noted)

| Part | LCSC | Qty | Use |
|---|---|---|---|
| AO3401A P-FET | C15127 | 3 | load switches |
| 2N7002 N-FET | C8545 | 6 (+4 DNP) | gate drivers, 1.8 V level shift for SIM7080G |
| SS8050 NPN | C2150 | 4 (+1 DNP) | autoreset x2, backlight, IR LED, PWRKEY |
| 47 nF 0603 | C1622 | 1 | BQ25601 bootstrap |
| 470 uF 10 V SMD electrolytic KNSCHA | C2858856 (E) | 2 | radio bulk (C303), VBAT_SW bulk at the amp (C505) |
| 20 R 0805 | C17544 | 1 | backlight series resistor |
| 12 R 1206 | C17913 (E) | 1 | IR emitter series resistor |
| 330 R 0603 | C23138 | 3 | LED data, HUSB238 I2C series |
| 22 uF 0805 | C45783 | 4 | buck input, boost input and output |
| 10 uF 0805 | C15850 | 8 | rails and modules |
| 4.7 uF 0603 | C19666 | 3 | IRM filter, misc |
| 1 uF 0603 | C15849 | 8 | audio coupling, NS4150B bypass, ESP EN RC |
| 100 nF 0603 | C14663 | 25 | decoupling |
| 22 pF 0603 | C1653 | 2 | spare |
| Resistors 0603 1 %: 10 k C25804, 100 k C25803, 1 k C21190, 4.7 k C23162, 470 C23179, 2.2 k C4190, 5.1 k C23186, 22 C23345, 1 M C22935, 100 C22775, 330 C23138 | | about 60 | 220 k, 47 k, 15, 33 and 2 k to be confirmed Basic during BOM |
| Red LED 0603 KT-0603R | C2286 | 2 | CHRG, STDBY |

---

## 5. Circuit notes per sheet

This section describes the schematic as generated (hardware/, 2026-09-29). The netlist is
the reference; docs/pinmap.md is generated from it.

**power**: USB-C 16 p, CC1/CC2 to the HUSB238 (Rd internal), shield to GND, USBLC6-2SC6 on
VBUS and D+/D-. BQ25601: VBUS and VAC on VBUS with 1 uF, PMID 2x 10 uF, REGN 4.7 uF, BTST
47 nF to SW, 1 uH SWPA4030 from SW to VSYS, SYS 2x 10 uF, BAT 10 uF, TS 10 k / 10 k from
REGN (no NTC), PSEL 10 k to VBUS (500 mA default until firmware programs IINDPM), /CE to GND,
/QON to the PWR tact switch, STAT to a red LED with 1 k from VSYS, /INT to PWR_INT (GPIO39) with a
10 k pull-up, /PG open, SDA/SCL on the 3.3 V bus. Two 18650 holders in parallel on VBAT,
DW01A + FS8205A on the cell negative side (100 R / 100 nF on VCC, 1 k on CS). HUSB238 on
VBUS with 1 uF, VSET and ISET 0 R, GATE and D+/D- open, I2C through 330 R. MAX17048 VDD and
CELL on VBAT with 100 nF, CTG and QSTRT to GND, ALRT to PWR_INT. TPS62A02 buck (EN to VIN,
1 uH, FB 150 k / 33 k, 22 uF + 10 uF out) to +3V3; TPS61023 boost from VSYS (1 uH, FB
220 k / 33 k with 1 nF feed-forward, 2x 22 uF out, EN = RADIO_EN with 4.7 k pull-down) to
RADIO_4V5; three load switches (AO3401A + 2N7002 + 10 k gate pull-down): GPS_3V3 and
LCD_3V3 from +3V3, VBAT_SW from VSYS with a 10 k + 100 nF gate soft start.

**mcu**: ESP32-WROOM-32E-N16, EN with 10 k + 1 uF and reset switch, IO0 with 10 k and boot
switch, IO2 10 k pull-down, 10 uF + 100 nF; CH340C on its own XC6206 3.3 V LDO from VBUS
(1 uF at the LDO, 100 nF at VCC, V3 tied to VCC), USB D+/D- direct, 1 k series in both UART0
lines (chip is unpowered on battery), DTR/RTS SS8050 auto-reset pair in the DevKitC
polarity (DTR to Q201 base, RTS to Q201 emitter, EN on its collector; mirrored for IO0);
LIS3DHTR in I2C mode (CS to +3V3, SA0 through 0 R to GND, 100 nF + 10 uF) with INT1 to the
expander; TCA9555 at 0x20 (A0-A2 low, INT with 10 k to GPIO32, 100 nF); 4.7 k I2C pull-ups.

**radio**: SA818S-U on RADIO_4V5 with 470 uF + 10 uF + 100 nF at the pad; PD from a
10 k / 22 k divider off RADIO_4V5 (3.2 V, so PD follows the rail); PTT driven by a 2N7002
open-drain inverter from GPIO27 with a 100 k pull-up to the PD node (RX by default, no
current into a dead module); H/L open, solder jumper to GND for 0.5 W; RXD via 1 k from
GPIO17, TXD to GPIO16; Audio-ON to the expander; ANT pad through pi pads (0 R fitted, shunt
DNP) to the SMA on a 50 ohm coplanar trace.

**lora_gps**: Ra-01SH on +3V3 with 10 uF + 100 nF, NRESET from the expander, DIO1 to GPIO33,
BUSY to GPIO4, NSS to GPIO5, VSPI, TXEN/RXEN open (DIO2 drives the switch), ANT through pi
pads to the 868 MHz spring. ATGM336H on GPS_3V3 (10 uF + 100 nF), VBAT backup on +3V3, RXD
via 1 k from GPIO14, TXD to GPIO13, 1PPS to the expander, ON/OFF pulled up to GPS_3V3 with
10 k, RESET open, RF_IN through a 100 pF DC block and pi pads (0 R fitted, shunt DNP) to the
18 mm patch. SIM7080G block fully DNP: module on VBAT with 2x 100 uF + 100 nF, nano-SIM
socket, 2x 2N7002 1.8 V level shifters, PWRKEY NPN, GSM spring, 0 R links to the GPS UART.

**audio**: DAC1 through 1 k to the TS5A3159 NC input, radio AF_OUT through 1 k to NO,
MUX_SEL on IN (low = DAC); COM through 100 nF and 220 k to NS4150B INP, INN through 220 k
and 100 nF to GND, Bypass 1 uF, VCC on VBAT_SW with 470 uF + 10 uF + 100 nF, CTRL through
10 k from AMP_SD with 100 k to GND on the chip side, BTL outputs straight to the speaker.
DAC1 through 100 k / 1 k and 1 uF to MIC_IN (33 mVpp full scale). AF_OUT through 47 k and
1 uF to a 100 k / 100 k bias, then 10 k and 1 nF to GPIO36.

**io**: 12-pin ZIF for the HS20HS072RX (logic on LCD_3V3, backlight LEDs from VBAT_SW
through 20 R with an SS8050 PWM sink on LCD_BL), 10 k pot on LCD_3V3 with 10 k / 100 nF to
GPIO34, 3 buttons to the expander with 100 nF each, 3x WS2812B-2020 on VBAT_SW with 100 nF
each and 330 R on data, IRM-H638T on LCD_3V3 with 100 R + 4.7 uF and 10 k pull-up on OUT to
GPIO35, VSMY2940G from VBAT_SW through 12 R with an SS8050 driver (330 R base) on GPIO26.
Expansion: second TCA9555 at 0x21 (A0 high, INT wire-ORed onto EXP_INT, 100 nF), P00-P11 as
EXP0-9 plus DRV1/DRV2, P14-P17 spare; 2x10 header J602: 1 GND, 2 +3V3, 3 VBAT_SW, 4 VSYS,
5 SDA, 6 SCL, 7-16 EXP0-9, 17 OUT1, 18 OUT2, 19-20 GND; OUT1/OUT2 are AO3400A low-side
switches (10 k gate pull-down, SS34 flyback to VBAT_SW) driven by DRV1/DRV2.

Firmware rules that the hardware relies on: configure the TCA9555 first thing after boot
(RADIO_EN, AUX_EN, GPS_EN, LCD_EN default low through the pull-downs until then); AUX_EN on
before AMP_SD, AMP_SD off before AUX_EN; drive GPIO17 low before RADIO_EN goes low and wait
300 to 500 ms after it goes high; drive GPIO14 low while GPS_EN is low; keep LCD_EN on while
SPI is active; IR carrier at 38 kHz and 50 % duty or less, bursts under 100 ms; DTMF at 50 to
70 % DAC amplitude; dim the WS2812B below 3.4 V cell voltage.

---

## 6. Cost estimate per unit at 25 pcs (excluding cell and enclosure)

| Item | USD | EUR |
|---|---|---|
| ESP32-WROOM-32E-N4 | 3.25 | 2.99 |
| SA818S-U | 9.49 | 8.73 |
| Ra-01SH | 3.92 | 3.61 |
| ATGM336H-5N31 + patch antenna | 3.44 | 3.16 |
| Display HS20HS072RX + ZIF | 3.17 | 2.92 |
| LIS3DHTR | 1.58 | 1.45 |
| 2x 18650 holder | 2.54 | 2.34 |
| Speaker FS-3013 | 1.06 | 0.98 |
| CH340C, USB-C, ESD | 0.88 | 0.81 |
| Charger and power path BQ25601 + L, HUSB238 PD sink, MAX17048 gauge, DW01A, FS8205A, buck | 3.75 | 3.45 |
| NS4150B, TS5A3159, TCA9555 | 1.11 | 1.02 |
| SMA, 868 spring, pot, 5 buttons, 3x WS2812, IRM, IR LED, 2x 470 uF | 1.88 | 1.73 |
| Discretes (FETs, NPN) and passives (about 130 pcs) | 1.30 | 1.20 |
| Expansion: second TCA9555, 2x10 header, 2x AO3400A, 2x SS34 | 0.95 | 0.87 |
| Review-round additions: N16 instead of N4 (+1.21), boost TPS61023 + L (+0.31), high-power IR LED (+0.73), LDO (+0.14) | 2.4 | 2.2 |
| **Parts subtotal** | **40.8** | **37.5** |
| Extended-part loading fees: about 31 part numbers x 3 USD / 25 boards | 3.7 | 3.4 |
| SMT assembly (about 330 joints x 0.0017 USD + 25 USD setup / 25) | 1.6 | 1.5 |
| THT assembly (speaker, 3 antennas and SMA, pot): about 10 joints, setup about 35 USD / 25 | 1.8 | 1.7 |
| PCB, 2 layer, 70 x 100 mm, 1.6 mm, ENIG (about 55 USD / 25) | 2.2 | 2.0 |
| **Estimated total per unit** | **about 50** | **about 46** |

About 5 EUR over the 40 EUR target after the 2026-09-29 power decision (second cell holder 1.2, charger/PD/gauge
stack 3.3 plus one more loading fee). The SA818S-U alone is 20 % of it. The cellular option adds about 14 USD when
fitted. Dropping the fuel gauge saves 1.9 USD, going back to N4 flash 1.1 EUR.

---

## 7. Open questions from the first round (answered, kept for the record)

1. **Display substitute.** Neither JLC nor LCSC stocks a 1.3" or 1.54" 240x240 ST7789 bare
   panel. Closest stocked panel: HS20HS072RX, 2.0" IPS 320x240 ST7789V2, 51.8 x 36.2 mm
   outline, 12-pin 0.5 mm FPC, 3.05 USD, 2 244 in stock. Do I change CONFIG to
   `DISPLAY = ST7789_320x240_2.0in`? Alternative: keep 240x240 and buy the panel elsewhere;
   then only the ZIF is on the board and I need that panel's exact pinout from you.
   -> Bigger panel is okay!
2. **SA818 to SA818S-U.** Plain SA818 is not stocked; SA818S-U (C3001549) is the drop-in
   successor with an added LNA. Only 34 in stock right now; 25 boards plus attrition needs
   about 27. OK to commit, and do you want the SA818S-V (VHF, same footprint) listed as a
   BOM alternative?
   -> Okay to commit
3. **GPIO expander.** 26 usable ESP32 GPIO versus about 40 signals in the brief. Proposed:
   TCA9555 for the slow signals listed in section 3 (this moves LIS3DH INT1, radio SQ, GPS
   PPS, display CS and RST and the amp shutdown off the ESP32). If you prefer a different
   split (for example INT1 direct and PPS dropped), say which signals must stay direct.
   Only the expander or dropping features solves the shortage.
   -> Expander is perfectly fine especially for low frequency signals.
4. **Buttons on the expander.** Consequence of 3: the three tact switches are read over I2C
   (about 100 us latency, wake-up through INT). Fine for menu buttons; tell me if one of
   them is a trigger that needs microsecond timing, then it swaps with GPIO27 and PTT moves
   to the expander.
   -> No dont need microsecond timing.
5. **Speaker choice.** FS-3013 is a 30 mm THT box speaker, 13 mm tall, 1 W, 90 dB. It is
   the loudest PCB-mount speaker JLC stocks, but it is a through-hole part (JLC THT assembly,
   extra setup fee) and needs a 30 mm sound opening in the enclosure. The SMD fallback (13 mm,
   87 dB at 0.7 W, 1.52 USD) is much quieter. Which one?
   -> If its the only THT component and much extra feee and time then we go for the SMD option. Otherwise THT is fine.
6. **SMA connector style.** BWSMA-KWE-Z001 is the right-angle 4-leg THT SMA that JLC
   assembles routinely, placed at the board edge. A true edge-launch SMA-KE exists (ZIISOR
   SMA-KE-10, 786 in stock) but is a hand-solder style part; I recommend the KWE.
   -> KWE is fine
7. **IR LED power.** IR26-51C/L110 (0.03 USD, 65 mA continuous, 20 deg beam) is fine for
   remote-control style signalling. If this is laser-tag style shooting at range, I would
   switch to Vishay VSMB2020X01 (0.35 USD, 20 mW/sr at 100 mA, 12 deg) driven with 100 mA
   pulses. Which?
   -> Its for laser tag style shooting.
8. **Radio at low cell voltage.** SA818S-U minimum supply is 3.3 V; the cell goes down to
   3.0 V. Plan: firmware refuses TX below 3.4 V and the 470 uF bulk handles the 1 A TX
   bursts. OK, or do you want a boost converter for the radio (about +0.8 USD and space)?
   -> Does it impact battery budget much? Otherwise I think boost converter is better. Or beefy buck boost?
9. **Deep sleep budget** lands at about 80 uA against your 100 uA limit; the buck (50 uA)
   dominates. If you need margin, swap SY8089A1 for a lower-Iq buck (TPS62A02, about 6 uA)
   at about +0.25 USD. Keep the SY8089A?
   -> Good buck better.
10. **Charge current** 500 mA (PROG 2 k). Go to 1 A (PROG 1.2 k) for faster charging? The
    holder and the ESOP-8 TP4056 can take it with a copper pour.
    -> Yeah faster charging better.
11. **ESP32 flash size**: N4 (4 MB) assumed. N8 is +0.75 USD.
    -> I think even 16MB for sounds storage.
12. **Board layout intent**: with the 18650 holder (86 x 21 mm), the 30 mm speaker, the
    2.0" display (52 x 36 mm) and three antennas I expect to need close to the full
    70 x 100 mm. I assume the display lies over the 18650 holder area on the component side
    with the ZIF at the display's short edge, buttons and pot below it, USB-C and SMA on
    opposite short edges, GPS patch in a corner away from the SMA. Say so if the enclosure
    wants something else.
    -> I think battery + some components at the back and screen + buttons at the front!
    Perhaps if it is much cheaper we can do a stock of THT components on one side and only populate the back with the rest.
    Im fine with soldering THT myself if its not too many components per board.

---

## 8. Sourcing risks

See `docs/sourcing.md` for the flagged parts and their identical-footprint alternatives.

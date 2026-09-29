# BQ25601RTWR (WQFN-24 RTW, 4x4 mm) schematic spec

Source: TI datasheet SLUSCK5A, March 2017, revised March 2023, 64 pages.
Local copy: scratchpad/ds/bq25601.pdf (text dump: scratchpad/ds/bq25601.txt).
Quotes are verbatim from the datasheet; page numbers are the printed page numbers.
Lines marked "[design note]" are my inference for this project, not datasheet text.

Project context: 1S (2P 18650) charger + NVDC power path, 5 V USB-C only, ICHG up to 2 A,
SYS feeds a 3.3 V buck and 4.6 V boost (peak 1.6 A), I2C from ESP32, no NTC, ship-mode
push button, one status LED.

Important family facts (p4, Table 6 Device Comparison):
- BQ25601: "D+/D- USB detection: No". There are NO D+/D- pins and NO ILIM pin on this part
  (BQ25601D has D+/D-). Input current limit is set only by the PSEL pin and the IINDPM register.
- "Default ICHG 2.04 A", "Default VACOV 6.4 V", "TS profile: JEITA, with fixed temperature thresholds",
  "TS ignore bit: No" (so the TS pin must be satisfied with resistors when there is no NTC),
  "Charge safety timer 5 hr, 10 hr (default)", "Allow QON fire when adapter is present: No".
- No OTG pin: boost/OTG is only enabled by the OTG_CONFIG register bit (REG01[5], default 0).

---------------------------------------------------------------------------------------------------

## 1. Pin table, WQFN-24 (Table 7-1, p5-p6; pinout Figure 7-1, p5)

Type legend (p6): "AI = Analog input, AO = Analog Output, AIO = Analog input Output, DI = Digital input,
DO = Digital Output, DIO = Digital input Output, P = Power". KiCad electrical type in parentheses.

| Pin | Name | DS type (KiCad type) | Function (verbatim, p5-p6) | If unused / this design |
|---|---|---|---|---|
| 1 | VAC | AI (input) | "Charge input voltage sense. This pin must be connected to VBUS pin." | Always tie to VBUS (pin 24). |
| 2 | PSEL | DI (input) | "Power source selection input. Set 500 mA input current limit by pulling this pin high and set 2.4A input current limit by pulling this pin low. Once the device gets into host mode, the host can program different input current limits to IINDPM register." | Must not float (no internal pull stated). Tie high (500 mA safe default) or low (2.4 A default), or to an ESP32 GPIO. See section 3. |
| 3 | /PG | DO (open collector) | "Open drain active low power good indicator. Connect to the pull up rail through 10-k resistor. LOW indicates a good input source if the input voltage is between UVLO and ACOV, above SLEEP mode threshold, and current limit is above 30 mA." | Optional; 10 k pull-up to logic rail, or leave open (NC) if not used. Typical app shows optional LED. |
| 4 | STAT | DO (open collector) | "Open-drain charge status output. Connect the STAT pin to a logic rail via 10-k resistor. The STAT pin indicates charger status. Collect a current limit resister and a LED from a rail to this pin. Charge in progress: LOW. Charge complete or charger in SLEEP mode: HIGH. Charge suspend (fault response): 1-Hz, 50% duty cycle Pulses. This pin can be disabled via EN_ICHG_MON[1:0] register bits." | LED + series resistor from SYS (typical app: 2.2 k). Max sink 6 mA (p7), VOL 0.4 V (p13). |
| 5 | SCL | DI (input) | "I2C interface clock. Connect SCL to the logic rail through a 10-k resistor." | 10 k pull-up to ESP32 3.3 V rail. |
| 6 | SDA | DIO (bidirectional) | "I2C interface data. Connect SDA to the logic rail through a 10-k resistor." | 10 k pull-up to ESP32 3.3 V rail. |
| 7 | /INT | DO (open collector) | "Open-drain interrupt Output. Connect the INT to a logic rail through 10-k resistor. The INT pin sends an active low, 256-us pulse to host to report charger device status and fault." | 10 k pull-up to 3.3 V, to ESP32 GPIO. If not used, leave open. |
| 8 | NC | -- (no connect) | "No Connect. Keep the pins float." | Leave floating. |
| 9 | /CE | DI (input) | "Charge enable pin. When this pin is driven low, battery charging is enabled." | Must not float (no internal pull stated). Tie to GND for always-enabled, or ESP32 GPIO with pull-down. VIL max 0.4 V, VIH min 1.3 V (p12). "Charge is enabled when both CE pin is pulled low AND CHG_CONFIG bit is 1." (REG01, p34) |
| 10 | NC | -- (no connect) | "No Connect. Keep the pins float." | Leave floating. |
| 11 | TS | AI (input) | "Temperature qualification voltage input to support JEITA profile. Connect a negative temperature coefficient thermistor. Program temperature window with a resistor divider from REGN to TS to GND. Charge suspends when TS pin is out of range. When TS pin is not used, connect a 10-k resistor from REGN to TS and connect a 10-k resistor from TS to GND. It is recommended to use a 103AT-2 thermistor." | No NTC in this design: 10 k REGN-TS + 10 k TS-GND. |
| 12 | /QON | DI (input) | "BATFET enable/reset control input. When BATFET is in ship mode, a logic low of tSHIPMODE duration turns on BATFET to exit shipping mode. When VBUS is not plugged in, a logic low of tQON_RST (minimum 8 s) duration resets SYS (system power) by turning BATFET off for tBATFET_RST (minimum 250 ms) and then re-enable BATFET to provide full system power reset. The pin contains an internal 200-k pull-up to maintain default high logic." | Push button from /QON to GND (typical app Figure 10-1, p45, "Optional"). If unused leave open (internal 200 k pull-up). |
| 13 | BAT | P (power in/out, passive) | "Battery connection point to the positive terminal of the battery pack. The internal BATFET and current sensing is connected between SYS and BAT. Connect a 10 uF close to the BAT pin." | Both BAT pins to battery +. |
| 14 | BAT | P | same as 13 | |
| 15 | SYS | P (power out) | "Converter output connection point. The internal current sensing network is connected between SYS and BAT. Connect a 20 uF capacitor close to the SYS pin." | Both SYS pins to SYS rail. |
| 16 | SYS | P | same as 15 | |
| 17 | GND | P (power in) | "Ground." | |
| 18 | GND | P | "Ground." | |
| 19 | SW | P (power out, passive) | "Switching node output. Connected to output inductor. Connect the 0.047-uF bootstrap capacitor from SW to BTST." | Both SW pins to inductor. |
| 20 | SW | P | same as 19 | |
| 21 | BTST | P (passive) | "PWM high side driver positive supply. Internally, the BTST pin is connected to the cathode of the boost-strap diode. Connect the 0.047-uF bootstrap capacitor from SW to BTST." | 47 nF to SW. |
| 22 | REGN | P (power out) | "LSFET driver and internal supply output. Internally, REGN is connected to the anode of the boost-strap diode. Connect a 4.7-uF (10-V rating) ceramic capacitor from REGN to GND. The capacitor should be placed close to the IC." | 4.7 uF 10 V to GND; also bias for the TS divider. VREGN = 4.6 V min / 4.7 V typ at VBUS = 5 V, IREGN = 20 mA (p12). REGN is OFF when running from battery only (p18, 9.3.2). |
| 23 | PMID | DO per table (power out, passive) | "Connected to the drain of the reverse blocking MOSFET (RBFET) and the drain of HSFET. Put 10 uF ceramic capacitor on PMID to GND." | 10 uF (see section 2 for 22 uF note). |
| 24 | VBUS | P (power in) | "Charger input. The internal n-channel reverse block MOSFET (RBFET) is connected between VBUS and PMID pins. Place a 1-uF ceramic capacitor from VBUS to GND close to device." | USB-C VBUS. |
| EP | Thermal Pad | P (power in) | "Thermal pad and ground reference. This pad is ground reference for the device and it is also the thermal pad used to conduct heat from the device. This pad should be tied externally to a ground plane through PCB vias under the pad." | Tie to GND with via array. |

---------------------------------------------------------------------------------------------------

## 2. Typical application circuit and external components (Figure 10-1, p45; 10.2.2, p45-p46)

Figure 10-1 "Power Path Management Application" (p45) shows, verbatim values:
- Input 3.9 V to 13.5 V into VAC and VBUS (VAC tied to VBUS), TVS/diode symbol to GND at the input, 1 uF VBUS to GND.
- 10 uF PMID to GND.
- SW to 1 uH inductor to SYSTEM "3.5V - 4.6V", 10 uF SYS to GND (see 20 uF note below).
- 47 nF from SW to BTST.
- 4.7 uF REGN to GND.
- 10 uF BAT to GND, battery on BAT.
- /PG: "Opt." LED with 2.2 k from SYS. STAT: LED with 2.2 k from SYS.
- SDA, SCL, /INT: "3 x 10 k" pull-ups to VREF (host logic rail), to Host. /CE from Host. PSEL from "PHY".
- TS: 5.23 k from REGN to TS, 30.1 k from TS to GND, 10 k NTC (103AT) in the battery pack from TS to GND.
- /QON: push button to GND, marked "Optional".

Design parameters Table 10-1 (p45): VVBUS 4 V to 13.5 V; Input current limit (REG00[4:0]) 2.4 A;
Fast charge current limit (REG02[5:0]) 2.04 A; Minimum system voltage (REG01[3:1]) 3.5 V;
Battery regulation voltage (REG04[7:3]) 4.2 V.

### Component list

| Ref | Value | Rating / notes | Datasheet text |
|---|---|---|---|
| C_VBUS | 1 uF ceramic | [design note] 25 V X7R 0603/0805 (abs max VBUS 22 V) | p6: "Place a 1-uF ceramic capacitor from VBUS to GND close to device." |
| C_PMID | 10 uF ceramic (22 uF for 3 A) | "A rating of 25 V or higher capacitor is preferred for 15-V input voltage." X7R/X5R. [design note] for 5 V only input a 16 V or 25 V X7R is fine; use 2 x 10 uF for margin against DC bias. | p6: "Put 10 uF ceramic capacitor on PMID to GND." p46 (10.2.2.2 Input Capacitor): "Low ESR ceramic capacitor such as X7R or X5R is preferred for input decoupling capacitor and should be placed to the drain of the high-side MOSFET and source of the low-side MOSFET as close as possible. Voltage rating of the capacitor must be higher than normal input voltage level. ... Capacitance of 22 uF is suggested for typical of 3-A charging current." Worst-case RMS: "ICIN = ICHG x sqrt(D x (1 - D))" (Eq. 5). |
| C_REGN | 4.7 uF ceramic | 10 V rating, close to IC | p5: "Connect a 4.7-uF (10-V rating) ceramic capacitor from REGN to GND. The capacitor should be placed close to the IC." |
| C_BTST | 47 nF (0.047 uF) ceramic | [design note] 16 V or 25 V X7R (BTST-SW abs max 7 V, BTST to GND up to 22 V) | p5: "Connect the 0.047-uF bootstrap capacitor from SW to BTST." Layout example Figure 12-2 (p53) also shows an "R_BTST" in series with C_BTST (value not given; not in the schematic Figure 10-1). |
| C_SYS | 20 uF total (2 x 10 uF) ceramic | 10 V X7R or X5R | p6: "Connect a 20 uF capacitor close to the SYS pin." p46 (10.2.2.3): "The charger device has internal loop compensation optimized for 20-uF ceramic output capacitance. The preferred ceramic capacitor is 10-V rating, X7R or X5R." |
| C_BAT | 10 uF ceramic | [design note] 10 V X7R | p5: "Connect a 10 uF close to the BAT pin." |
| L1 | 1 uH | Isat >= ICHG + IRIPPLE/2; see below | p45: "ISAT >= ICHG + (1/2) IRIPPLE" (Eq. 3). p46: "IRIPPLE = VIN x D x (1 - D) / (fs x L)" (Eq. 4). "The maximum inductor ripple current occurs when the duty cycle (D) is 0.5 or approximately 0.5. Usually inductor ripple is designed in the range between 20% and 40% maximum charging current". fs = 1.5 MHz. |
| R_STAT + LED | 2.2 k + LED from SYS to STAT | STAT sink max 6 mA (p7), VOL 0.4 V max (p13) | p6 and Figure 10-1. |
| R_PG (+ LED, opt.) | 10 k pull-up, or 2.2 k + LED | optional | p5: "Connect to the pull up rail through 10-k resistor." |
| R_INT | 10 k to logic rail | | p5: "Connect the INT to a logic rail through 10-k resistor." |
| R_SCL, R_SDA | 10 k each to logic rail | fSCL max 400 kHz (p13) | p5. |
| R_TS1, R_TS2 | 10 k REGN-TS, 10 k TS-GND (no NTC) | 1% | p6: "When TS pin is not used, connect a 10-k resistor from REGN to TS and connect a 10-k resistor from TS to GND." |
| SW_QON | momentary push button /QON to GND | | p45 Figure 10-1 "Optional"; p28: "QON is pulled up to VQON by an internal 200-k pull-up resistor." |
| PSEL | strap to logic rail or GND (or GPIO) | | p5. |
| Input TVS | shown as diode symbol on VBUS in Fig 10-1 | [design note] TVS at the USB-C connector, e.g. 5 V working / ~ 6.5 V standoff | Figure 10-1, p45 (no part number given). |

### Inductor sizing for this design [design note, using datasheet Eq. 3 and 4]
- VIN = 5 V, L = 1 uH, fs = 1.5 MHz: IRIPPLE at D = 0.5 (worst case) = 5 x 0.25 / (1.5e6 x 1e-6) = 0.83 A;
  at VBAT = 4.2 V (D = 0.84) IRIPPLE = 0.45 A.
- NVDC: the inductor carries ISYS + ICHG, up to the 3 A converter rating (Recommended Operating Conditions
  p7: "ISWOP Output current (SW) 3.25 A" max, "IBATOP Fast charging current 3.0 A" max). With the 5 V USB
  input limited to 2.4 A (or 2 A via IINDPM), the converter output is bounded near 2.4 A x 5 V x eff / VSYS.
- Cycle-by-cycle HSFET OCP: "IHSFET_OCP HSFET cycle-by-cycle over-current threshold 5.2 A min, 8.0 A max" (p12).
- Suggested: 1 uH, Isat >= 3.5 A (better 4 A or more, so the inductor is not saturated when the 5.2 A OCP
  comparator acts), Irms >= 3 A, DCR <= 30 mOhm, shielded (e.g. 4x4 or 5x5 mm power inductor).

### ILIM resistor
- Not applicable: the BQ25601 has no ILIM pin. The hardware default input limit is only PSEL high = 500 mA or
  PSEL low = 2.4 A (Table 9-1, p19); a 2 A limit is set by the host writing IINDPM (REG00[4:0]) = 10011
  (100 mA offset + 19 x 100 mA = 2000 mA). See section 3.

### TS pin without NTC
- 10 k / 10 k divider puts TS at 50% of VREGN. Buck-mode JEITA thresholds (p11-p12): VT1 rising 73.3% typ
  (cold, charge suspended above), VT2 rising 68% typ (cool below this), VT3 rising 44.7% typ (warm above this),
  VT5 rising 34.2% typ (hot, charge suspended below). 50% is inside the T2-T3 "normal" window with about
  5% margin on each side, so charging runs at full ICHG and VREG. NTC_FAULT reads 000 Normal.

### PSEL pin
- Table 9-1 (p19): PSEL High -> "USB SDP" -> 500 mA, VBUS_STAT = 001; PSEL Low -> "Adapter" -> 2.4 A, VBUS_STAT = 011.
- p19: "When the device operates in host-control mode, the host needs to IINDET_EN bit to read the PSEL value and
  update the IINDPM register. When the device is in default mode, PSEL value updates IINDPM in real time."
- [design note] Tie PSEL high (3.3 V or REGN-independent rail) for a safe 500 mA default until the ESP32 has
  confirmed the USB-C source (CC resistors/PD) and writes IINDPM. Tie low only if the 5 V source is always
  guaranteed >= 2.4 A. Since PSEL must be valid before the ESP32 boots (SYS may be off in ship mode), a
  fixed strap is preferable to a GPIO; or use a GPIO with an external pull-up.

### CE pin
- Active low, digital input, VIL max 0.4 V / VIH min 1.3 V (p12). No internal pull-up/down is specified.
- REG01 (p34): "Charge is enabled when both CE pin is pulled low AND CHG_CONFIG bit is 1." CHG_CONFIG default 1.
- [design note] Tie to GND (charge controlled by CHG_CONFIG over I2C), or ESP32 GPIO with 100 k pull-down so
  charging is on when the ESP32 is not driving it.

### QON pin and push button (9.4.4, p28-p29)
- Internal 200 k pull-up; push button to GND, "Optional" in Figure 10-1.
- Exit ship mode: "A QON logic transition from high to low with longer than tSHIPMODE deglitch turns on BATFET to
  exit shipping mode." tSHIPMODE = 0.9 s min, 1.3 s max (p13).
- "When exiting shipping mode, HIZ is enabled (EN_HIZ = 1) as well. HIZ can be disabled (EN_HIZ = 0) by the
  host after exiting shipping mode." (p28) -> the ESP32 firmware must clear EN_HIZ (REG00[7]) after a QON wake
  or the USB input will stay in high impedance.
- Full system reset: "When QON is driven to logic low by at least tQON_RST while adapter is not plugged in (and
  BATFET_DIS = 0), the BATFET is turned off for tBATFET_RST." tQON_RST = 8 s min, 12 s max; tBATFET_RST = 250 ms
  min, 400 ms max (p13). Disable via BATFET_RST_EN = 0 (REG07[2], default 1).
- Abs max on QON: -0.3 V to 7 V (p7).

### STAT LED
- Table 9-4 (p29): Charging in progress (including recharge) = LOW; Charging complete = HIGH; Sleep mode,
  charge disable = HIGH; Charge suspend (input overvoltage, TS fault, timer fault or system overvoltage) =
  Blinking at 1 Hz; Boost mode suspend (due to TS fault) = Blinking at 1 Hz.
- "The STAT pin function can be disabled by setting the EN_ICHG_MON bits = 11." (p29)
- LED + 2.2 k from SYS (Figure 10-1); keep current <= 6 mA (abs max sink, p7).

### INT and PG
- Both open drain, 10 k pull-up to logic rail (p5). INT: 256 us active-low pulses. Abs max sink 6 mA each (p7).
- PG low when: VBUS above UVLO, VBUS above battery, VBUS below VAC_OV, VBUS above 3.8 V with 30 mA load,
  input source type detection completed (p29).

### D+/D- and OTG pins
- Not present on BQ25601 (only BQ25601D has D+/D-). OTG is register-only (OTG_CONFIG, REG01[5]).

---------------------------------------------------------------------------------------------------

## 3. Power-up register defaults that matter (9.6 Register Maps, p33-p44)

I2C: "I2C Target Address: 6BH" (p33) = 0x6B 7-bit. fSCL max 400 kHz (p13). Registers REG00 to REG0B.
"A register read beyond REG0B (0x0B)" is not supported (p31). Device ID: REG0B PN[3:0] = "BQ25601 : 0010" (p44).

| Item | Default | Register | Verbatim / notes |
|---|---|---|---|
| EN_HIZ | 0 (disabled) | REG00[7] | Set to 1 automatically on QON ship-mode exit (p28). |
| STAT pin enable | 00 (enabled) | REG00[6:5] EN_ICHG_MON | "11 - Disable STAT pin function (float pin)" |
| Input current limit IINDPM | 2400 mA (10111) | REG00[4:0] | "Offset: 100 mA, Range: 100 mA (000000) - 3.2 A (11111). Default: 2400 mA (10111), maximum input current limit, not typical. IINDPM bits are changed automatically after input source detection is completed. PSEL = Hi = 500 mA, PSEL = Lo = 2.4 A. Host can over-write IINDPM register bits after input source detection is completed." (p33). 2.0 A = 10011. IINDPM is NOT reset when the watchdog expires (p20). |
| Charge enable CHG_CONFIG | 1 (charge) | REG01[4] | "Charge is enabled when both CE pin is pulled low AND CHG_CONFIG bit is 1." |
| OTG_CONFIG | 0 (OTG disable) | REG01[5] | |
| SYS_MIN | 3.5 V (101) | REG01[3:1] | "000: 2.6 V ... 111: 3.7 V. Default: 3.5 V (101)". SYS regulated typ 180 mV above SYS_MIN when VBAT below it; SYS = VBAT + 50 mV typ when charge disabled/terminated (p26, p9). |
| Fast charge current ICHG | 2040 mA (100010) | REG02[5:0] | "Range: 0 mA (0000000) - 3000 mA (110010)", 60 mA steps. "ICHG = 0 mA disables charge." (p35). Table 9-2 (p21) "Charging current 2.048 A". |
| Q1_FULLON | 0 | REG02[6] | "0 - Use higher Q1 RDSON when programmed IINDPM < 700mA (better accuracy), 1 - Use lower Q1 RDSON always (better efficiency)" |
| BOOST_LIM | 1 (1.2 A) | REG02[7] | OTG only. |
| Precharge current IPRECHG | 180 mA (0010) | REG03[7:4] | offset 60 mA, 60 mA steps, clamp 780 mA. |
| Termination current ITERM | 180 mA (0010) | REG03[3:0] | offset 60 mA, 60 mA steps. |
| Charge voltage VREG | 4.208 V (01011) | REG04[7:3] | "Offset: 3.856 V, Range: 3.856 V to 4.624 V (11000)", 32 mV steps. "Special Value: (01111): 4.352 V" (p37). Use default 4.208 V for 4.2 V cells. |
| TOPOFF_TIMER | 00 disabled | REG04[2:1] | |
| VRECHG | 100 mV (0) | REG04[0] | |
| EN_TERM | 1 | REG05[7] | |
| Watchdog | 40 s (01) | REG05[5:4] WATCHDOG | "00 - Disable timer, 01 - 40 s, 10 - 80 s, 11 - 160 s" (p38). tWDT 40 s (p13). |
| EN_TIMER | 1 | REG05[3] | safety timer on; CHG_TIMER REG05[2] default 1 = 10 hrs. |
| TREG thermal regulation | 110 C (1) | REG05[1] | "0 - 90 C, 1 - 110 C" (p38). p25: "When the internal junction temperature exceeds thermal regulation limit (110 C), the device lowers down the charge current." Thermal shutdown 160 C, 30 C hysteresis. |
| JEITA_ISET | 20% (1) | REG05[0] | irrelevant with fixed TS divider. |
| OVP (VAC OVP) | 6.5 V (01) | REG06[7:6] | "00 - 5.5 V, 01 - 6.5 V (5-V input), 10 - 10.5 V (9-V input), 11 - 14 V (12-V input)". Keep 6.5 V for a 5 V only design. |
| VINDPM | 4.5 V (0110) | REG06[3:0] | "Offset: 3.9 V, Range: 3.9 V (0000) - 5.4 V (1111), Default: 4.5 V (0110)". Not reset by watchdog expiry. |
| BATFET_DIS (ship mode) | 0 (allow Q4 on) | REG07[5] | "0 - Allow Q4 turn on, 1 - Turn off Q4 with tBATFET_DLY delay time (REG07[3])" |
| BATFET_DLY | 1 | REG07[3] | "Turn off BATFET after tBATFET_DLY (typ. 10 s) when BATFET_DIS bit is set"; tSM_DLY 10 s min / 15 s max (p13). Set BATFET_DLY = 0 for immediate shutdown. |
| BATFET_RST_EN | 1 | REG07[2] | QON long-press system reset enabled. |
| VDPM_BAT_TRACK | 00 | REG07[1:0] | |
| REG_RST | 0 | REG0B[7] | "1 - Reset to default register value and reset safety timer" |

Default mode vs host mode (9.3.5.1, p20):
- "After power-on-reset, the device starts in default mode with watchdog timer expired, or default mode. All the
  registers are in the default settings. During default mode, any change on PSEL pin will make real time IINDPM
  register changes."
- "In default mode, the device keeps charging the battery with default 10-hour fast charging safety timer."
- "Writing a 1 to the WD_RST bit transitions the charger from default mode to host mode. ... To keep the device
  in host mode, the host has to reset the watchdog timer by writing 1 to WD_RST bit before the watchdog timer
  expires (WATCHDOG_FAULT bit is set), or disable watchdog timer by setting WATCHDOG bits = 00."
- "When the watchdog timer expires (WATCHDOG_FAULT bit = 1), the device returns to default mode and all registers
  are reset to default values except IINDPM, VINDPM, BATFET_RST_EN, BATFET_DLY, and BATFET_DIS bits."
- [design note] So without firmware the chip autonomously charges at 2.04 A / 4.208 V with the PSEL-selected
  input limit, and a BATFET_DIS ship-mode command survives a watchdog reset.

Ship mode entry (9.4.4.1, p28): "When the host set BATFET_DIS bit, the charger can turn off BATFET immediately
or delay by tSM_DLY as configured by BATFET_DLY bit."
Ship mode exit (9.4.4.2, p28): "1. Plug in adapter 2. Clear BATFET_DIS bit 3. Set REG_RST bit ... 4. A logic
high to low transition on QON pin with tSHIPMODE deglitch time".
Note on battery-only operation (9.3.2, p18): "If only battery is present ... the BATFET turns on and connects
battery to system. The REGN stays off to minimize the quiescent current." When the system is overloaded
"(IBAT > IBATFET_OCP), the device turns off BATFET immediately and set BATFET_DIS bit" (needs adapter or QON to recover).
Sleep/battery discharge: "IBATOP Discharging current (continuous) 6 A" max (p7).

Charging cycle start conditions (p21): "Converter starts; Battery charging is enabled (CHG_CONFIG bit = 1 and
ICHG register is not 0 mA and CE is low); No thermistor fault on TS".

---------------------------------------------------------------------------------------------------

## 4. Absolute maximum ratings (8.1, p7) and recommended operating conditions (8.3, p7)

Absolute maximum, all with respect to GND:
- VAC, VBUS (converter not switching): -2 V to 22 V. "(2) VBUS is specified up to 22 V for a maximum of one hour at room temperature"
- BTST, PMID (converter not switching): -0.3 V to 22 V
- SW: -2 V to 16 V
- BTST to SW: -0.3 V to 7 V
- PSEL: -0.3 V to 7 V
- REGN, TS, CE, PG, BAT, SYS (converter not switching): -0.3 V to 7 V
- SDA, SCL, INT, QON, STAT: -0.3 V to 7 V
- PGND to GND (QFN package only): -0.3 V to 0.3 V
- Output sink current STAT: 6 mA; INT: 6 mA
- TJ: -40 to 150 C; Tstg: -65 to 150 C
- ESD: HBM +-2000 V, CDM +-250 V (8.2, p7)

Recommended operating conditions (p7):
- VBUS input voltage: 3.9 V min, 13.5 V max
- Iin input current (VBUS): 3.25 A max
- ISWOP output current (SW): 3.25 A max
- VBATOP battery voltage: 4.624 V max
- IBATOP fast charging current: 3.0 A max
- IBATOP discharging current (continuous): 6 A max
- TA: -40 to 85 C
- "(1) The inherent switching noise voltage spikes should not exceed the absolute maximum voltage rating on either the BTST or SW pins. A tight layout minimizes switching noise."

Thermal (8.4, p7): RthJA 35.6 C/W, RthJB 11.9 C/W, RthJC(bot) 2.6 C/W (RTW 24-pin).

Logic pins (8.5, p12-p13): CE and PSEL VIL max 0.4 V, VIH min 1.3 V, leakage 1 uA (pull-up rail 1.8 V test);
PG and STAT VOL max 0.4 V. REGN: 4.6 V min / 4.7 V typ at VBUS 5 V, 20 mA.

---------------------------------------------------------------------------------------------------

## 5. Layout notes (12.1 Layout Guidelines, p52; Figure 12-2 Layout Example, p53)

Verbatim, p52:
1. "Place input capacitor as close as possible to PMID pin and GND pin connections and use shortest copper trace connection or GND plane."
2. "Place inductor input pin to SW pin as close as possible. Minimize the copper area of this trace to lower electrical and magnetic field radiation but make the trace wide enough to carry the charging current. Do not use multiple layers in parallel for this connection. Minimize parasitic capacitance from this area to any other trace or plane."
3. "Put output capacitor near to the inductor and the device. Ground connections need to be tied to the IC ground with a short copper trace connection or GND plane."
4. "Route analog ground separately from power ground. Connect analog ground and connect power ground separately. Connect analog ground and power ground together using thermal pad as the single ground connection point. Or using a 0-ohm resistor to tie analog ground to power ground."
5. "Use single ground connection to tie charger power ground to charger analog ground. Just beneath the device. Use ground copper pour but avoid power pins to reduce inductive and capacitive noise coupling."
6. "Place decoupling capacitors next to the IC pins and make trace connection as short as possible."
7. "It is critical that the exposed thermal pad on the backside of the device package be soldered to the PCB ground. Ensure that there are sufficient thermal vias directly under the IC, connecting to the ground plane on the other layers."
8. "Ensure that the number and sizes of vias allow enough copper for a given current path."

Figure 12-1 (p52) "High Frequency Current Path": the hot loop is input (PMID) capacitor -> HSFET -> LSFET -> GND, i.e. C_PMID must sit right at PMID (pin 23) and GND (pins 17/18 and EP).

Figure 12-2 (p53) layout example: C_BUS at VBUS pin 24 corner, C_PMID and C_REGN along the top edge next to
pins 22/23, R_BTST + C_BTST next to pins 21/20, inductor L directly off the SW pins (19/20) at the top-right,
C_SYS at SYS pins 15/16 on the right edge, C_BAT at BAT pins 13/14, 3x3 via array in the thermal pad to a
2nd-layer PGND plane, PGND copper on the top layer under the capacitors' ground ends.

Reference: "BQ25601 and BQ25601D (PWR877) Evaluation Module User's Guide" for placement (p52).

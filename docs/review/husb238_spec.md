# HUSB238_002DD (Hynetek) USB PD sink controller, DFN-10L 3x3, LCSC C7471904

Sources (all in scratchpad/ds/):
- `husb238.pdf`  : LCSC-hosted datasheet, Chinese, Rev 2.5 04/2023, 17 pages (https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2404071728_Hynetek-HUSB238-002DD_C7471904.pdf). Cited as "CN p.N".
- `husb238_en.pdf`: English datasheet Rev 2.0 01/2021, 15 pages (Adafruit mirror of the Hynetek file; hynetek.com copy `husb238_hyn.pdf` is byte-identical text). Cited as "EN p.N". Content is the same as Rev 2.5 except Rev 2.5 drops the SOT33-6L package and adds 005DD/006DD to the ordering guide.
- `husb238_regs.pdf`: "HUSB238 REGISTER INFORMATION" Rev 1.1 01/14/2021, 8 pages (SparkFun mirror). Cited as "REG p.N". The datasheet itself contains NO register map.
- `husb238_evb.pdf`: "User Guide for the EVB_HUSB238_002DD Evaluation Board" RD-2010 Rev 1.1 10/2020. Cited as "EVB p.N".

LCSC C7471904: Hynetek HUSB238_002DD, DFN-10L(3x3), extended part, stock 8650, 0.58 USD @1, 0.35 USD @100 (jlc_ds.py, 2026-09-29).

Ordering variant (EN p.14 / CN p.15): "HUSB238_002DD | DFN-10L | SOP' NO | OTP Threshold 150C / 130C | RDO Mismatch Action: Next PDO | GATE_ON_TIME: During POR (CN Rev 2.5 only) | Tape & Reel, 4k".

## 1. Pin table, DFN-10L (EN p.3 Table 1 / CN p.4 Table 1)

Pin configuration (top view, EN p.3 Fig. 2): pins 1..5 down the left side (VIN, D+, D-, CC1, CC2), pins 6..10 up the right side (SDA, SCL, VSET, ISET, GATE), pin 11 = centre pad GND.

| Pin | Name | Type | Description (verbatim, EN p.3) | Unused / this design |
|---|---|---|---|---|
| 1 | VIN | P | "Power supply input. Connect this pin to VBUS of USB Type-C connector and bias this pin via a 1uF ceramic capacitor." | Always used. |
| 2 | D+ | DIO | "Positive line of USB 2.0 data line for Apple Divider 3 and BC1.2." | Datasheet gives no NC instruction. The SOT33-6L variant has no D+/D- pins at all (EN p.3, "-" in SOT column), so the chip works without them (PD and Type-C Rp detection use CC only). See note 2.7. |
| 3 | D- | DIO | "Negative line of USB 2.0 data line for Apple Divider 3 and BC1.2." | Same as D+. |
| 4 | CC1 | AIO | "Configuration line 1 used to negotiate a voltage/current with the attached adapter." | Direct to receptacle CC1. |
| 5 | CC2 | AIO | "Configuration line 2 used to negotiate a voltage/current with the attached adapter." | Direct to receptacle CC2. |
| 6 | SDA | DIO | "I2C communication data signal." | To ESP32 SDA, external pull-up. |
| 7 | SCL | DIO | "I2C communication clock signal." | To ESP32 SCL, external pull-up. |
| 8 | VSET | AI | "Connect a resistor to indicate the maximum voltage needed by the system from the attached power adapter." | Short to GND for 5 V (Table 5: RVSET 0 = 5 V). "Open" = 20 V, so do NOT leave floating. |
| 9 | ISET | AI | "Connect a resistor to indicate the maximum current needed by the system from the attached power adapter." | Resistor to GND per Table 6; "Open" = 3.25 A. See 2.5. |
| 10 | GATE | OD | "Open drain gate driver output. Connect this signal to the gate of an external PMOS through a series resistor. Leave this pin open if not used." | Leave open (no PMOS load switch in this design). |
| 11 | GND (exposed pad) | P | "Ground reference. All signals are referred to this pin." | MUST be soldered to GND: pin 11 is the ONLY ground pin of the package (EN p.3 pinout, the "11 GND" is the centre pad; CN p.13 package drawing shows pad D1 1.7 x E1 2.4 mm). |

Legend (EN p.3): A = Analog, P = Power, D = Digital, I = Input, O = Output, OD = Open Drain.

Package (CN p.13 Fig. 5, DFN-10L 3 x 3 mm): body D = E = 3.000 nom, pitch e = 0.500 BSC, lead b = 0.25 nom, L = 0.40 nom, exposed pad D1 = 1.70 nom x E1 = 2.40 nom, height A = 0.75 nom. Matches KiCad `Package_DFN_QFN:DFN-10-1EP_3x3mm_P0.5mm_EP1.65x2.38mm` (check pad size in footprint vs 1.7 x 2.4).

## 2. Application circuit

### 2.1 Supply
- VIN is powered directly from VBUS; there is no separate VDD/VCC pin. "VIN pin is the power supply input of the HUSB238, which is derived from the output of the PD source." (EN p.8). Internal LDO: block diagram shows "VOLTAGE REGULATOR -> VREG" fed from VIN (EN p.7 Fig. 3).
- Operating range: "Supply Voltage VIN 3 min, 25 max V"; "VIN_UVLO_RISE 3.1 V typ, VIN_UVLO_FALL 2.9 V typ"; "Supply Current ISC_OPR, VIN = 5V, CC is attached, normal operation, 3.1 mA typ" (EN p.4 Table 2). CN p.5 Table 2 additionally: "VIN input voltage 3.24V~21V" (recommended operating).
- "The VIN pin is also connected to an internal MOSFET and 500Ohm discharging resistor, which is used as a bleeder to help discharge the output capacitor to vSafe5V upon the hard reset, over-voltage fault, over-temperature fault or detachment of a connected device." (EN p.8). RDIS = 500 ohm typ (EN p.5).
- The chip is unpowered whenever USB is unplugged; there is no way to power it from the battery (VIN must be VBUS).

### 2.2 Decoupling
- "Connect a 1uF decoupling MLCC between VIN pin and GND pin as closer as possible." (EN p.8).
- Typical application circuit Fig. 1 (EN p.1 / CN p.1) has a 10 ohm series resistor from VBUS to VIN with the 1 uF after it; Fig. 4 "USB-C Device Application" (EN p.11 / CN p.12) has no series resistor, just 1 uF VIN to GND. EVB schematic (EVB p.13): R1 = 10R 0603 in series VBUS -> VIN, C1 = "105K50V X7R 0603" (1 uF 50 V).
- EVB (EVB p.13/14) also fits C2, C3 = 330 pF 50 V from CC1 and CC2 to GND, and optional (NC) TVS SOD-323 ZD1..ZD4 on CC1, CC2, D+, D-.

### 2.3 CC1 / CC2
- Connect directly to the receptacle CC1/CC2. Rd is internal: "When HUSB238 is connected to power source, it applies Rd to both CC lines" (EN p.8); "Pull-down resistor RD 4.6 / 5.1 / 5.6 kohm" (EN p.4); "internal 5.1k Rd resistor" (EN p.10). Remove any external 5.1 k CC pull-downs, otherwise the source sees 2.55 k and Type-C detection fails.
- Dead battery: "The HUSB238 works as PD sink role which requires RD resistor to be presented on the CC pins even in the un-powered state for successful Type-C detection by source adapter. The dead battery function in the HUSB238 supports default USB, 1.5A and 3.0A source broadcast RP current." (EN p.10). So Rd is present with VIN = 0 V; the source will enable VBUS.
- "CC1 and CC2 pins can support as high as 25V voltage, which is used for protection when CC1 or CC2 is shorted to VBUS pin on the connector." (EN p.8).
- Rp detection thresholds (EN p.4): VTH_DEF 0.20 V, VTH_1P5 0.66 V, VTH_3P0 1.23 V typ.

### 2.4 VBUS sense
No separate VBUS sense pin or resistor; OVP/UVP are sensed on VIN itself: "The HUSB238 senses the voltage on VIN pin for overvoltage protection. The over-voltage threshold is 1.2 times of max requested voltage." (EN p.10). UVP "disabled for default option" (EN p.10).

### 2.5 Requested PD voltage / current (VSET, ISET, fuses, I2C)
- VSET: "A fixed 100uA current source is applied on VSET pin. Connect a resister between VSET and GND to indicate the VSET_VOLTAGE value" (EN p.8). Table 5 (EN p.8): RVSET 0 -> 5 V; 6.04 k -> 9 V; 10 k -> 12 V; 14 k -> 15 V; 17.8 k -> 18 V; Open -> 20 V. "The RDO voltage of the HUSB238 is determined by the lower value between VSET_VOLTAGE and SNK_PDO2_VOLTAGE ... default value is 20V."
- ISET: Table 6 (EN p.9): RISET 0 -> 1.25 A; 4.53 k -> 1.5 A; 7.5 k -> 1.75 A; 10.5 k -> 2 A; 13.7 k -> 2.25 A; 16.5 k -> 2.5 A; 19.6 k -> 2.75 A; 22.6 k -> 3 A; Open -> 3.25 A. IISET = 100 uA +-5 %, debounce 2 ms (EN p.4).
- RDO matching (EN p.9): the chip picks the first source PDO, highest voltage first, with "1. SOURCE_PDO_VOLTAGE <= RDO_VOLTAGE 2. SOURCE_PDO_CURRENT >= RDO_CURRENT". On mismatch, the 002DD variant does "Next PDO" (EN p.14). What happens when no PDO matches at all is not stated; EVB p.3: "the PD power adapter will fail to match the HUSB238. In this situation, the request current can be set to 3A (or smaller) by changing the external resistor RISET".
- 5 V only: VSET = 0 ohm to GND (RDO voltage 5 V). Hynetek's own recommendation for MCU designs: "It is suggested the VEST pin be shorted to ground such that the default request voltage 5V. Then the MCU request the actual required voltage & current through the I2C interface." (EVB p.5).
- ISET for 5 V only: RDO current must be <= the source's 5 V PDO current or the request mismatches. RISET = 0 ohm (1.25 A) matches every practical 5 V PDO; RISET = 22.6 k (3 A) mismatches on 5 V/2.4 A or 5 V/1.5 A sources. Recommended for this design: RISET = 0 ohm (or a value equal to the minimum current the charger will be programmed to), then read SRC_PDO_5V over I2C for the real limit. Note: PD sinks are nominally not supposed to draw more than the RDO operating current; the I2C request path (PDO_SELECT + GO_COMMAND) does not document which operating current it puts in the RDO.
- "I2C has the highest priority. If using I2C to select a source PDO, it over writes the internal RDO which is created by VSET, ISET pins and internal factory fuse option" (EN p.9).
- OTP behaviour: at 150 C the chip "requests 5V source PDO directly" (EN p.10), irrelevant when already at 5 V.

### 2.6 GATE
"The GATE pin is open-drain output which allows to drive an external PMOS load switch directly. The GATE pin can be programmed to turn on after POR or after the explicit contract. The default option is to turn on after POR." (EN p.8). 002DD: GATE_ON_TIME "During POR" (CN p.15). GATE pin: max sink current 10 mA, pull-low impedance 100..300 ohm (EN p.4). Reference circuit (EN p.11 Fig. 4): PMOS in VBUS path, 49.9 k gate-to-source, 5.1 k series GATE-to-gate; EVB uses 100 k / 30 k. Not needed for a 5 V-only sink: "Leave this pin open if not used." (EN p.3).

### 2.7 D+ / D-
Used only for legacy detection after PD fails: "After the power on reset, if the HUSB238 does not establish PD contract with source adapter, the HUSB238 will waits for 1.5 seconds and then switches to Apple Divider 3 and BC1.2 detections sequentially." (EN p.9). During detection the chip drives VDP_SRC / VDM_SRC 0.6 V and sinks 100 uA on D+/D- (EN p.4). Since the CH340C shares D+/D- and the ESP32 only needs the Type-C/PD current info from CC, recommend leaving HUSB238 D+/D- unconnected (the SOT33-6L variant omits them entirely, EN p.3). If they are connected, the 0.6 V source during BC1.2 detection can disturb CH340C enumeration on a PC (SDP) host. Abs max on D+/D- is 12 V (EN p.6). Datasheet does not state a required termination for unused D+/D-.

### 2.8 I2C
- Slave address 0x08 (7-bit): "The HUSB238 works as I2C slave role and the I2C address is 0x08." (EN p.9; REG p.3).
- Levels (EN p.4, "I2C PARAMETERS"): "Supply Range 2.5 min 5.5 max V" (the I2C bus / pull-up voltage), "Low Level Input Voltage, SDA, SCL pins, 0.4 V max", "High Level Input Voltage, SDA, SCL pins, 1.4 V min", "Low Level Output Voltage, SDA pin, 2mA load current, 0.4 V max". Compatible with 3.3 V ESP32 GPIO. No internal pull-ups shown; EVB schematic (EVB p.13) routes SCL/SDA straight to header pins with no pull-ups, so fit 4.7 k..10 k pull-ups to ESP32 3V3.
- Unpowered tolerance: abs max for SDA, SCL is "-0.3V to +6V" (EN p.6) with no VIN-relative clause, and the I2C block has its own 2.5..5.5 V "supply range" spec, so holding SDA/SCL at 3.3 V while VIN = 0 V is inside absolute maximum ratings. The datasheet does NOT explicitly state that the I2C pins do not load the bus when the chip is unpowered; verify on hardware that an unplugged HUSB238 does not hold SDA/SCL low (it shares the ESP32 bus). Firmware must handle NACK from 0x08 when USB is unplugged.
- SDA/SCL pins are DIO (EN p.3): SCL is an input only in practice (slave), SDA open-drain bidirectional.

### 2.9 Interrupt / attach-detect output
None. The DFN-10 has no INT, ALERT or attach pin (EN p.3). Attach state is only available by polling PD_STATUS1.ATTACH (bit 6) over I2C (REG p.4), or by sensing VBUS presence externally (VIN = VBUS; a resistor divider from VBUS to an ESP32 GPIO/ADC gives the plug-in event).

## 3. I2C registers (REG p.3..7, Rev 1.1)

Register summary (REG p.3 Table 1): 0x00 PD_STATUS0, 0x01 PD_STATUS1, 0x02 SRC_PDO_5V, 0x03 SRC_PDO_9V, 0x04 SRC_PDO_12V, 0x05 SRC_PDO_15V, 0x06 SRC_PDO_18V, 0x07 SRC_PDO_20V, 0x08 SRC_PDO, 0x09 GO_COMMAND; all default 0x00.

### 3(a) Negotiated / available current at 5 V
- PD_STATUS0 (0x00), REG p.3 Table 2: bits [7:4] PD_SRC_VOLTAGE R "The voltage information when an explicit contract is established. 0000 = Unattached, 0001 = PD 5V, 0010 = PD 9V, 0011 = PD 12V, 0100 = PD 15V, 0101 = PD 18V, 0110 = PD 20V". Bits [3:0] PD_SRC_CURRENT R "The current information when an explicit contract is established. 0000 = 0.5A, 0001 = 0.7A, 0010 = 1A, 0011 = 1.25A, 0100 = 1.5A, 0101 = 1.75A, 0110 = 2A, 0111 = 2.25A, 1000 = 2.5A, 1001 = 2.75A, 1010 = 3A, 1011 = 3.25A, 1100 = 3.5A, 1101 = 4A, 1110 = 4.5A, 1111 = 5A". This is the contract actually negotiated (i.e. the RDO current, limited by ISET), not the source maximum.
- SRC_PDO_5V (0x02), REG p.4 Table 4: bit 7 SRC_5V_DETECT R "0 = Not detected, 1 = Detected"; bits [3:0] SRC_5V_CURRENT R, same 0.5 A..5 A encoding as above. This is the source's advertised 5 V PDO maximum current, which is what the charger limit should be programmed from when a PD source is attached. Same layout at 0x03..0x07 for 9/12/15/18/20 V.
- PD_STATUS1 (0x01) bits [2:0], REG p.4 Table 3: bit 2 5V_VOLTAGE R "Voltage information of 5V contract: 0 = Others, 1 = 5V"; bits [1:0] 5V_CURRENT R "Current information of 5V contract: 00 = Default current, 01 = 1.5A, 10 = 2.4A, 11 = 3A".

### 3(b) PD source vs plain Type-C source
- PD_STATUS1 (0x01) bit 6 ATTACH R "0 = HUSB238 is in unattached mode, 1 = HUSB238 is in modes other than unattached mode"; bit 7 CC_DIR R "0 = CC1 is connected to CC line or unattached mode, 1 = CC2 is connected to CC line"; bits [5:3] PD_RESPONSE R "000 = No response, 001 = Success, 011 = Invalid command or argument, 100 = Command not supported, 101 = Transaction fail. No GoodCRC is received after sending" (REG p.4).
- PD source: SRC_PDO_5V.SRC_5V_DETECT = 1 (source capabilities received) and/or PD_STATUS0.PD_SRC_VOLTAGE != 0000 (explicit contract). Plain Type-C / legacy source: ATTACH = 1 while PD_SRC_VOLTAGE = 0000 and all SRC_xV_DETECT = 0. The register document does not have a dedicated "PD vs non-PD" bit; this is the inference.

### 3(c) Type-C current advertisement (default / 1.5 A / 3 A)
PD_STATUS1 (0x01) bits [1:0] 5V_CURRENT: "00 = Default current, 01 = 1.5A, 10 = 2.4A, 11 = 3A" (REG p.4). The encoding matches the Type-C Rp classes (Default / 1.5 A / 3 A) plus Apple divider-3 2.4 A; the document only labels it "Current information of 5V contract" and does not explicitly say it reflects Rp when no PD contract exists, so verify on hardware with a non-PD Type-C source (the chip does measure Rp: VTH_DEF/VTH_1P5/VTH_3P0, EN p.4, and dead-battery text lists "default USB, 1.5A and 3.0A source broadcast RP current", EN p.10).

### Write registers (for completeness)
- SRC_PDO (0x08) bits [7:4] PDO_SELECT RW "0000 = Not selected, 0001 = SRC_PDO_5V, 0010 = SRC_PDO_9V, 0011 = SRC_PDO_12V, 1000 = SRC_PDO_15V, 1001 = SRC_PDO_18V, 1010 = SRC_PDO_20V" (REG p.7).
- GO_COMMAND (0x09) bits [4:0] COMMAND_FUNC RW "00001 = Requests the PDO set by PDO_SELECT, 00100 = Send out Get_SRC_Cap command, 10000 = Send out hard reset command" (REG p.7).

## 4. Absolute maximum ratings (EN p.6 Table 3 / CN p.7 Table 4)
- "VIN, GATE: -0.3V to +30V"
- "CC1, CC2: -0.3V to +25V"
- "D+, D-: -0.3V to +12V"
- "VSET, ISET, SDA, SCL: -0.3V to +6V"
- "Operating Temperature Range (Junction): -40C to +125C"; ESD HBM +-6000 V; thermal DFN-10L thetaJA 75 C/W, thetaJC 54 C/W (EN p.6).
- Recommended operating (CN p.5 Table 2): VIN 3.24 V..21 V, TA -40..85 C.

## 5. Schematic summary for this design (5 V only, ESP32 reads current over I2C)
- U: HUSB238_002DD, DFN-10L, EP = GND.
- VIN <- VBUS via optional 10 ohm 0603 (R1 per EVB; Fig. 4 omits it), C 1 uF 50 V X7R 0603 VIN to GND, close to pin 1.
- CC1, CC2 <- receptacle CC1/CC2 direct; no external 5.1 k Rd; optional 330 pF 50 V to GND on each (EVB).
- D+, D- : leave NC (recommended, CH340C owns D+/D-).
- VSET: 0 ohm (short) to GND -> 5 V request.
- ISET: 0 ohm to GND -> 1.25 A RDO current (guaranteed match on any 5 V PDO), or 22.6 k 1% for 3 A if a 3 A contract must be negotiated; never leave open (3.25 A never matches a 3 A source).
- GATE: NC.
- SDA, SCL: to ESP32 I2C, 4.7 k pull-ups to 3V3 (bus voltage 2.5..5.5 V allowed). Address 0x08.
- No INT pin; poll PD_STATUS1/SRC_PDO_5V after VBUS appears; add a VBUS divider to an ESP32 GPIO for plug detection if desired.

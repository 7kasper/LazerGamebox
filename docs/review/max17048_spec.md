# MAX17048G+T10 (LCSC C2682616) schematic spec

Source: MAX17048/MAX17049 datasheet 19-6171 Rev 7, 11/16 (Maxim Integrated), 19 pages.
Local copy: scratchpad/ds/max17048.pdf (from cdn.sparkfun.com mirror; analog.com download stalled at TLS, LCSC CDN served a "Datasheet temporarily unavailable" placeholder). Text dump: scratchpad/ds/max17048.txt.
Part ordered: MAX17048G+T10, -40 to +85 C, 8 TDFN-EP, package code T822+3, outline 21-0168, land pattern 90-0065 (p18). JLC lists it as DFN-8-EP(2x2), Extended part.
Page numbers below are datasheet page numbers.

## 1. Pin table, 8 TDFN (p6, "Pin/Bump Descriptions", verbatim)

Top view (pad side down): pins 1-4 along the bottom edge left to right (CTG, CELL, VDD, GND), pins 5-8 along the top edge right to left (ALRT=5, QSTRT=6, SCL=7, SDA=8). "+" marks the pin 1 corner. (p6 figure)

| TDFN pin | Name | Type (derived) | Function (verbatim, p6) | Unused / notes |
|---|---|---|---|---|
| 1 | CTG | ground reference | "Connect to Ground" | Always tie to GND. |
| 2 | CELL | input (NC on MAX17048) | "Connect to the Positive Battery Terminal. MAX17048: Not internally connected. MAX17049: Voltage sense input." | Tie to PACK+ anyway (Fig 14 shows it joined with VDD). |
| 3 | VDD | power in + sense | "Power-Supply Input. Bypass with 0.1uF to GND. MAX17048: Voltage sense input. Connect to positive battery terminal. MAX17049: Connect to regulated power-supply voltage." | Battery directly, 2.5 to 4.5 V. |
| 4 | GND | ground | "Ground. Connect to negative battery terminal." | |
| 5 | ALRT (active low) | open-drain output | "Open-Drain, Active-Low Alert Output. Optionally connect to interrupt input of the system microcontroller." | Table 3 p15: "Leave unconnected" if unused. Needs external pull-up if used (p14). |
| 6 | QSTRT | digital input | "Quick-Start Input. Allows reset of the device through hardware. Connect to GND if not used." | Tie to GND (Fig 14, Table 3). |
| 7 | SCL | input | "I2C Clock Input. SCL has an internal pulldown (IPD) for sensing disconnection." | External pull-up required (p14). |
| 8 | SDA | open-drain I/O | "Open-Drain I2C Data Input/Output. SDA has an internal pulldown (IPD) for sensing disconnection." | External pull-up required (p14). |
| EP | EP | exposed pad | "Exposed Pad (TDFN Only). Connect to GND." | Connect to GND. |

Internal pulldown IPD on SDA, SCL: 0.2 uA typ, 0.4 uA max at VSDA = VSCL = 0.4 V, "This current is always present" (p2, Note 5).

## 2. Typical application circuit (Fig 14 "MAX17048 Application Circuit (1S Cell Pack)", p15, plus Table 3 and p14 text)

Fig 14 wiring, 1S pack, host-side with low-cell interrupt:
- PACK+ (after the pack protection circuit) goes directly to VDD and to CELL (the two pins are joined on the same net). No series resistor on VDD or CELL.
- 0.1 uF from VDD to GND, placed at the IC (p6: "Bypass with 0.1uF to GND"). This is the only external component ("ONLY ONE EXTERNAL COMPONENT", p1).
- CTG to GND (p6). CTG exists on both parts, function "Connect to Ground"; it is not MAX17049-only.
- GND to PACK- (p6: "Connect to negative battery terminal").
- QSTRT to GND (p14: "The QSTRT pin is unused in this application and is connected to GND"). Only tie it to a "rising-edge reset signal" if hardware quick-start is wanted (Table 3, p15); p9: "Most systems should not use quick-start".
- ALRT to the microcontroller interrupt input (p14). Table 3 (p15) for "1S host-side location, low-cell interrupt": VDD "Power directly from battery", ALRT "Connect to system interrupt", QSTRT "Connect to GND".
- SDA, SCL to the I2C master.

Pull-ups (p14, verbatim): "In all cases, the system must provide pullup circuits for ALRT (if used), SDA, and SDL." The datasheet gives no pull-up resistor value; the only bus constraints are 400 kHz max, CB 400 pF max per line, rise/fall time 20+0.1CB min to 300 ns max (p3). 4.7 k to 10 k to 3.3 V is normal for an ESP32 bus at 100 to 400 kHz; ESP32 GPIO pull-ups are too weak for reliable 400 kHz, so use discrete resistors. Because of the 0.2 to 0.4 uA internal pulldowns, do not use pull-ups larger than a few hundred k.

Logic-level and rail mixing (VDD 2.5 to 4.2 V from the cell, ESP32 at 3.3 V):
- All voltages are referenced to GND (p3, Note 2). Data I/O pins SCL, SDA, ALRT allowed range -0.3 to +5.5 V (p2, Electrical Characteristics), independent of VDD. Absolute max on all pins except CELL is -0.3 to +6 V (p2).
- Input thresholds: VIH min 1.4 V, VIL max 0.5 V for SDA, SCL, QSTRT (p2). Output low VOL 0.4 V max at IOL = 4 mA on SDA and ALRT (p2). Sink current limit 20 mA continuous on SDA, ALRT (p2).
- So: pull SDA, SCL and ALRT up to the ESP32 3.3 V rail, connect straight to the ESP32 pins. No level shifter is needed whether VDD is above or below 3.3 V. Only VDD and CELL see the battery voltage.
- Caveat when the 3.3 V rail is off but the battery stays connected: the pull-ups go to 0 V and SDA/SCL sit low. Note 6 p3: "The IC enters shutdown mode after SCL < VIL and SDA < VIL for longer than 2.5s", but the Sleep Mode section (p10) states this bus-low sleep only applies after "write MODE.EnSleep = 1"; MODE default is 0x0000 (p10), so with defaults the gauge keeps running (hibernate) while the ESP32 is off. Do not set EnSleep if the gauge should track SOC during system off.

Component list for the schematic:
- U: MAX17048G+T10, 8 TDFN-EP 2x2 mm (T822+3), LCSC C2682616.
- C: 0.1 uF ceramic, VDD to GND, close to pins 3/4 (p6, Fig 14). Rated 10 V or more for a 4.2 V cell.
- R: pull-up SDA to +3V3 (value not specified by datasheet; 4.7 k typical).
- R: pull-up SCL to +3V3 (same).
- R: pull-up ALRT to +3V3 if ALRT is used (p14); omit the resistor and leave ALRT unconnected if not (Table 3, p15).
- Net ties: CTG, QSTRT, EP to GND; CELL to the VDD net (PACK+).

## 3. I2C address, quiescent current, ModelGauge with two parallel 18650s

I2C (p16): "The 7-bit slave address is fixed to 0x6C (write)/0x6D (read)", binary 0110110. 7-bit address is 0x36. Slave only, up to 400 kHz (p16, p3). All registers must be written and read as 16-bit words, 8-bit writes have no effect (p10).

Supply current (p2, Electrical Characteristics, VDD 2.5 to 4.5 V):
- IDD0 Sleep mode, TA <= +50 C: 0.5 uA typ, 2 uA max.
- IDD0 Hibernate mode, reset comparator disabled (VRESET.Dis = 1): 3 uA typ, 5 uA max.
- IDD0 Hibernate mode, reset comparator enabled (VRESET.Dis = 0): 4 uA typ.
- IDD1 Active mode: 23 uA typ, 40 uA max.
- Hibernate is entered automatically when |CRATE| < HibThr for 6 min, default HIBRT 0x8030 (p10, p12). ADC sample period 250 ms active, 45 s hibernate (p2).
Operating range: VDD 2.5 to 4.5 V (p2). Voltage measurement range on the VDD pin 2.5 to 5 V, resolution 1.25 mV, error +/-7.5 mV at 3.6 V 25 C, +/-20 mV over temp (p2). VCELL register LSb 78.125 uV (p10).

ModelGauge and a parallel pair of cells: the datasheet does not mention parallel cells explicitly. Relevant statements:
- p10, SOC register: "This register automatically adapts to variation in battery size since ModelGauge naturally recognizes relative SOC." The algorithm uses only voltage (p7), so 2P of the same cell type looks like one cell of double capacity and needs no capacity setting. There is no capacity or design-capacity register in this part.
- p7: "ModelGauge performs best with a custom model ... At power-on reset (POR), the ICs have a preloaded ROM model that performs well for some batteries. Contact Maxim if you need a custom model." p14: TABLE registers 0x40 to 0x7F "The default value is appropriate for some Li+ batteries."
- p12: "RCOMP is an 8-bit value that can be adjusted to optimize IC performance for different lithium chemistries or different operating temperatures ... The POR value of RCOMP is 0x97." CONFIG default 0x971C (p11): RCOMP 0x97, ATHD 0x1C = 4% low-SOC alert (p12).
- p8, Temperature compensation: host should update RCOMP at least once per minute from measured battery temperature; RCOMP0 default 0x97, TempCoUp default -0.5, TempCoDown default -5.0; RCOMP = RCOMP0 + (T-20) x TempCoUp for T > 20 C, else RCOMP0 + (T-20) x TempCoDown.
- Only the cell chemistry matters, both 18650s must be the same type. The higher currents of a 2P pack change nothing since no current is measured.
- CRATE register (p13) is in %/hr, "not for conversion to ampere".
- VRESET (p13): "For captive batteries, set to 2.5V. For removable batteries, set to at least 300mV below the application's empty voltage." Default VRESET/ID 0x96__ = 3.0 V threshold (p2 "Trimmed at 3V", p11). For soldered/captive 18650s consider VRESET 2.5 V so the gauge does not quick-start on a deep sag.
- VALRT default 0x00FF (no voltage alerts), STATUS default 0x01__ (RI set at power-up, model not configured) (p11, p14).
- Sleep mode "does not detect self-discharge" (p10); "Applications which can tolerate 4uA should use hibernate rather than sleep mode" (p10).

## 4. Absolute maximum ratings (p2, verbatim)

- CELL to GND: -0.3V to +12V
- All Other Pins to GND: -0.3V to +6V
- Continuous Sink Current, SDA, ALRT: 20mA
- Operating Temperature Range: -40 C to +85 C
- Storage Temperature Range: -55 C to +125 C
- Lead Temperature (TDFN only) (soldering, 10s): +300 C
- Soldering Temperature (reflow): +260 C

Recommended operating: VDD 2.5 to 4.5 V; Data I/O pins SCL, SDA, ALRT -0.3 to +5.5 V; electrical characteristics specified at TA = -20 C to +70 C (p2).

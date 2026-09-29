# Sourcing notes (checked against the JLCPCB parts API on 2026-09-28)

Re-run `python tools/jlc_ds.py <LCSC codes>` before ordering; stock moves daily.

## Flagged parts

| Part | LCSC | Stock | Risk | Same-footprint alternative |
|---|---|---|---|---|
| G-NiceRF SA818S-U (fitted instead of SA818) | C3001549 | 34 | 25 boards + attrition needs about 27. Plain SA818 not stocked at all. | SA818S-CE (C19632390, 8 pcs, CE version same footprint). SA868-U (C3001507, 1 pc). If both dry up: buy SA818S-U from NiceRF directly and let JLC place it as a consigned part, or hand-solder (18 castellated pads). |
| INGHAi GSPK1504S-8R0.8W speaker (only if you pick the SMD speaker) | C7507399 | 63 | small stock | KELIKING KLJ-01304T-08R07W C18186315 (261 pcs) is the chosen SMD fallback anyway |
| ST LIS3DHTR | C15134 | 1 210 | fine, but single source | none pin-compatible at JLC (LIS2DH12 is a different package) |
| HanElectricity 05A20H12P ZIF (dual contact) | C5362174 | 1 225 | fine | 05A20L12P C5362155 (bottom contact only, 2 124 pcs) if the panel's contact side is confirmed |
| BAT WIRELESS BW868SNX20-5Z6 spring | C496555 | 1 030 | fine | DreamLNK T3-868M C381193 (694), Vollgo VG868SNX18-5W2 C718843 (1 773), all single-pin THT |
| BAT WIRELESS BWGNSCNX18-18W4 patch | C784395 | 1 800 | fine | BWGNSCNX18-18W2 C2826453 (2 395, 2 mm thick, lower gain), Kinghelm KH-GPS181804-WY C962215 (164) |
| Alps RK09K1130A6S pot | C209770 | 3 975 | fine | RK09K1130A70 C351173 (6 827, different shaft length, same footprint) |

## Not available at JLC or LCSC

| Wanted | Result | Substitute proposed |
|---|---|---|
| 1.3" or 1.54" 240x240 ST7789 bare panel with FPC | none listed in the "LCD Screen" category (only 128x64 OLEDs at those sizes) | HS HS20HS072RX 2.0" 320x240 ST7789V2, C5329582, 2 244 pcs, 3.05 USD. Needs a CONFIG change (open question 1) |
| SiP32431 load switch | SOT-363 version C141606 has 15 pcs; TDFN version C727398 has 5 646 but is a 1.2 x 1.6 mm package | AO3401A (Basic) + 2N7002 (Basic) discrete switch on every rail |
| Dorji DRA818U | not stocked | SA818S-U (compatible footprint) |
| JLC Basic power inductor 2.2 uH | none in Basic (only 0603/0805 signal inductors) | Sunlord SWPA4030S2R2MT C36409, Extended |

## Extended part count

About 28 Extended part numbers (each about 3 USD loading fee per order). Basic parts used
wherever one exists: all 0603 R/C, 0805 caps, AO3401A, 2N7002, SS8050, SS34, tact
switches, red LEDs. TP4056 C16581 is "Preferred" (no fee).

## Added in the review round (verified 2026-09-28)

| Part | LCSC | Stock | Note |
|---|---|---|---|
| TI TPS62A02DRLR buck | C5350187 | 33 628 | SOT-563, 0.5 mm pitch: fine for JLC |
| TI TPS61023DRLR boost | C919459 | 36 746 | SOT-563 |
| Sunlord SWPA4030S1R0NT 1 uH | C42193 | 9 505 | used twice per board |
| Torex XC6206P332MR-G LDO | C5446 | 480 132 | Basic |
| Vishay VSMY2940G IR emitter | C499547 | 5 699 | |
| ESP32-WROOM-32E-N16 | C701343 | 9 871 | |
| Uni-Royal 20 R 0805 (backlight) | C17544 | Basic | |
| Uni-Royal 12 R 1206 (R607, IR emitter series) | C17913 | 169 030 | Extended; 12 R keeps the VSMY2940G under its 200 mA pulse limit at 4.2 V |
| TI BQ25601RTWR charger (U101) | C468236 | 6 094 | Extended, WQFN-24; replaces TP4056, SS34 and the load-share FET |
| Hynetek HUSB238_002DD PD sink (U105) | C7471904 | 8 650 | Extended, DFN-10 |
| Maxim MAX17048G+T10 gauge (U106) | C2682616 | 24 759 | Extended, TDFN-8 2x2, the most expensive small part (about 1.9 USD) |
| Uni-Royal 2.2 k, Samsung 47 nF 0603 | C4190, C1622 | Basic | STAT LED, bootstrap |
| second MYOUNG 18650 holder (BT102) | C2988620 | 4 430 | two per board now |

## Library provenance (symbols, footprints, STEP)

- KiCad 10 stock libraries: passives, SOT-23/SOT-23-6/SOT-563/SC-70/MSOP/SOIC/TSSOP/LGA packages, USB-C
  (HRO TYPE-C-31-M-12), ESP32-WROOM-32E, WS2812B-2020, SMA BWSMA-KWE-Z001, Alps RK09K pot, XKB TS-1187A switches,
  Everlight IRM-H6xxT, 6.3x7.7 electrolytic. All carry STEP models from the KiCad packages3D set.
- `hardware/lib/LazerGamebox_lcsc.*`: imported with easyeda2kicad from the LCSC/EasyEDA library (the same footprints JLC
  uses in its own tooling): SA818S-U, Ra-01SH, ATGM336H, SIM7080G, 18650 holder, FS-3013 speaker, 05A20H12P ZIF,
  868 spring, GPS patch, GSM spring, nano-SIM socket, VSMY2940G. STEP files in `LazerGamebox_lcsc.3dshapes`.
  The ZIF has no EasyEDA model, so a same-size Hirose FH12-12S STEP from KiCad is attached.
- Before ordering, CPL rotations of the LCSC-imported footprints must be checked against JLCPCB's DFM preview
  (their rotation database is keyed by footprint name); this is a layout-stage task.

# Pin map

Generated from the schematic netlist by `python tools/check_pinmap.py`; do not edit by hand.
Net names are the global labels in the schematic, `/mcu/EN` style names are sheet-local nets.
Unconnected (NC) pins are omitted.

## U201 ESP32-WROOM-32E-N16

| Module pin | GPIO | Net |
|---|---|---|
| 1 | GND | GND |
| 2 | VDD | +3V3 |
| 3 | EN | /mcu/EN |
| 4 | SENSOR_VP | ADC_AUDIO |
| 5 | SENSOR_VN | PWR_INT |
| 6 | IO34 | ADC_POT |
| 7 | IO35 | IR_RX |
| 8 | IO32 | EXP_INT |
| 9 | IO33 | LORA_DIO1 |
| 10 | IO25 | DAC1 |
| 11 | IO26 | IR_TX |
| 12 | IO27 | RADIO_PTT |
| 13 | IO14 | GPS_TX |
| 14 | IO12 | LCD_DC |
| 15 | GND | GND |
| 16 | IO13 | GPS_RX |
| 23 | IO15 | LED_DATA |
| 24 | IO2 | LCD_BL |
| 25 | IO0 | /mcu/IO0 |
| 26 | IO4 | LORA_BUSY |
| 27 | IO16 | RADIO_RX |
| 28 | IO17 | RADIO_TX |
| 29 | IO5 | LORA_CS |
| 30 | IO18 | SCK |
| 31 | IO19 | MISO |
| 33 | IO21 | SDA |
| 36 | IO22 | SCL |
| 37 | IO23 | MOSI |
| 38 | GND | GND |
| 39 | GND | GND |

## U205 TCA9555 I2C GPIO expander (address 0x20, INT on GPIO32)

| Pin | Port | Net |
|---|---|---|
| 1 | ~{INT} | EXP_INT |
| 2 | A1 | GND |
| 3 | A2 | GND |
| 4 | P00 | RADIO_EN |
| 5 | P01 | GPS_EN |
| 6 | P02 | LCD_EN |
| 7 | P03 | AUX_EN |
| 8 | P04 | AMP_SD |
| 9 | P05 | MUX_SEL |
| 10 | P06 | LCD_CS |
| 11 | P07 | LCD_RST |
| 12 | GND | GND |
| 13 | P10 | LORA_RST |
| 14 | P11 | CELL_PWRKEY |
| 15 | P12 | BTN1 |
| 16 | P13 | BTN2 |
| 17 | P14 | BTN3 |
| 18 | P15 | RADIO_SQ |
| 19 | P16 | ACC_INT1 |
| 20 | P17 | GPS_PPS |
| 21 | A0 | GND |
| 22 | SCL | SCL |
| 23 | SDA | SDA |
| 24 | VCC | +3V3 |

## U301 SA818S-U radio module

| Pin | Name | Net |
|---|---|---|
| 1 | AUDIO_ON | RADIO_SQ |
| 3 | AF_OUT | RADIO_AF |
| 5 | PTT | /radio/PTT_N |
| 6 | PD | /radio/PD |
| 8 | VBAT | RADIO_4V5 |
| 9 | GND | GND |
| 10 | GND | GND |
| 12 | ANT | Net-(U301-ANT) |
| 16 | RXD | Net-(U301-RXD) |
| 17 | TXD | RADIO_RX |
| 18 | MIC_IN | RADIO_MIC |
| 19 | GND | GND |
| 20 | GND | GND |

## U401 Ra-01SH LoRa module

| Pin | Name | Net |
|---|---|---|
| 1 | ANT | Net-(U401-ANT) |
| 2 | GND | GND |
| 3 | 3V3 | +3V3 |
| 4 | RESET | LORA_RST |
| 6 | DIO1 | LORA_DIO1 |
| 9 | GND | GND |
| 10 | BUSY | LORA_BUSY |
| 12 | SCK | SCK |
| 13 | MISO | MISO |
| 14 | MOSI | MOSI |
| 15 | NSS | LORA_CS |
| 16 | GND | GND |

## U402 ATGM336H-5N31 GNSS module

| Pin | Name | Net |
|---|---|---|
| 1 | GND | GND |
| 2 | TXD | GPS_RX |
| 3 | RXD | Net-(U402-RXD) |
| 4 | 1PPS | GPS_PPS |
| 6 | VBAT | +3V3 |
| 8 | VCC | GPS_3V3 |
| 10 | GND | GND |
| 11 | RF_IN | Net-(U402-RF_IN) |
| 12 | GND | GND |

## J601 display ZIF (HS20HS072RX pinout)

| Pin | Name | Net |
|---|---|---|
| 1 | GND | GND |
| 2 | CS | LCD_CS |
| 3 | RS | LCD_DC |
| 4 | SCL | SCK |
| 5 | SDA | MOSI |
| 6 | RST | LCD_RST |
| 8 | IOVCC | LCD_3V3 |
| 9 | VCC | LCD_3V3 |
| 10 | LEDA | Net-(J601-LEDA) |
| 11 | LEDK | Net-(J601-LEDK) |
| 12 | GND | GND |

## Strapping and analog notes

- GPIO0 boot button, GPIO2 pulled down 10k (LCD_BL), GPIO12 has no pull-up, GPIO5 and GPIO15 keep internal pull-ups.
- All ADC inputs on ADC1: GPIO34 pot, GPIO36 radio audio, GPIO39 VBAT/2. GPIO35 is the IR receiver (digital).
- UART0 (GPIO1/3) is the CH340C programming port only. UART1 = GPS (shared with the DNP cellular module), UART2 = radio.
- Wake sources from deep sleep: GPIO32 (expander INT: buttons, motion, squelch, PPS) and GPIO33 (LoRa DIO1).

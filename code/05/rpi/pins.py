"""Raspberry Pi Pico GPIO numbers for the stripboard backplane.

REQ, VOTE, SDA and SCL run to all 30 card slots in parallel; the SSD1306 sits on
the same I2C bus. The jig socket has its own numbers in jig_pins.py.

Strips run horizontally, so one strip is one row. The Pico's right-hand column of pins stands on rows y=2.3 to 3.0,
the same rows as the first card slot, with no trace cut between them:

    signal   strip   Pico pin   GP
    vote      2.4       27      21
    updi      2.5       26      20
    SCL       2.6       25      19
    SDA       2.7       24      18
    req       2.9       22      17

Pin to GP numbering: the Pico datasheet pinout,
https://datasheets.raspberrypi.com/pico/pico-datasheet.pdf
"""

PIN_REQ = 17  # Pico pin 22. Driven by the Pico, read by every card's PA6.
PIN_VOTE = 21  # Pico pin 27. Open drain, 30 cards' PA3 in parallel.
PIN_SDA = 18  # Pico pin 24.
PIN_SCL = 19  # Pico pin 25.
PIN_UPDI = 20  # Pico pin 26. Card flashing only; nothing in 05/rpi drives it.

# GP18 and GP19 are the I2C1 pins on the RP2040.
I2C_ID = 1
I2C_HZ = 100_000

# One 1024-byte SSD1306 frame is 92 ms at 100 kHz, past MicroPython's 50 ms
# rp2 default. A full display init measured 114 ms.
I2C_TIMEOUT_US = 200_000

# The card firmware is specified at 100 kHz, so the OLED runs at that speed too.
OLED_ADDR = 0x3C
OLED_WIDTH = 128
OLED_HEIGHT = 64

# VOTE is read with the RP2040 pull-up off. No resistor is fitted: the line is
# pulled up by the 30 cards' internal pull-ups in parallel, about 1.2 kOhm.
VOTE_PULLUP = False

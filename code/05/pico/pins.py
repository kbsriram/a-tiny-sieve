"""Raspberry Pi Pico GPIO numbers for the log 5 REQ/VOTE test.

Same stripboard jig as log 4; see code/04/README.md and code/04/rpi/pins.py.
"""

PIN_REQ_PA6 = 17  # GP17 (Pico pin 22) -> H1 pin 2, ATtiny PA6 / REQ
PIN_VOTE_PA3 = 21  # GP21 (Pico pin 27) -> H1 pin 7, ATtiny PA3 / VOTE
PIN_SDA_PA1 = 18  # GP18 (Pico pin 24) -> H1 pin 4, ATtiny PA1 / SDA
PIN_SCL_PA2 = 19  # GP19 (Pico pin 25) -> H1 pin 5, ATtiny PA2 / SCL

# GP18 and GP19 are the I2C1 pins on the RP2040.
I2C_ID = 1
I2C_HZ = 100_000

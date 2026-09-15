"""Raspberry Pi Pico GPIO numbers for the card test jig socket.

Header H1 on the ATtiny412 card; wiring in code/04/README.md. Kept apart from
pins.py, which carries the stripboard backplane numbers and changes when the
backplane is wired.
"""

PIN_PA6_REQ = 17  # GP17 (Pico pin 22) -> H1 pin 2
PIN_PA7_LED = 16  # GP16 (Pico pin 21) -> H1 pin 3, reaches the card only via JP1
PIN_PA1_SDA = 18  # GP18 (Pico pin 24) -> H1 pin 4
PIN_PA2_SCL = 19  # GP19 (Pico pin 25) -> H1 pin 5
PIN_PA3_VOTE = 21  # GP21 (Pico pin 27) -> H1 pin 7

# GP18 and GP19 are the I2C1 pins on the RP2040.
I2C_ID = 1
I2C_HZ = 100_000

"""Pin assignments for the ATtiny412 flash-time self-test jig.

Maps Raspberry Pi Pico GPIOs to header H1 on the ATtiny412 card socket.
"""

PIN_H1_2_PA6 = 17  # GP17 (Pico pin 22) -> H1 pin 2 (PA6 / REQ)
PIN_H1_3_PA7 = 16  # GP16 (Pico pin 21) -> H1 pin 3 (PA7 / TEST / JP1)
PIN_H1_4_PA1 = 18  # GP18 (Pico pin 24) -> H1 pin 4 (PA1 / SDA)
PIN_H1_5_PA2 = 19  # GP19 (Pico pin 25) -> H1 pin 5 (PA2 / SCL)
PIN_H1_7_PA3 = 21  # GP21 (Pico pin 27) -> H1 pin 7 (PA3 / VOTE)

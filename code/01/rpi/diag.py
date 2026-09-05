"""Log every GP16 level change while the OLED is running.

Copy over code.py. Each line is one level change: the level that just ended
and how long it lasted. A "closed" line of a few ms or less is a noise spike,
not a press; that is what makes the counter step more than once.
"""

import time

import board
import count_display
import digitalio

count_display.CountDisplay()  # same I2C traffic as the real program

pin = digitalio.DigitalInOut(board.GP16)
pin.direction = digitalio.Direction.INPUT
pin.pull = digitalio.Pull.UP

last = pin.value
since = time.monotonic_ns()

while True:
    now = pin.value
    if now != last:
        t = time.monotonic_ns()
        print("{:>6} for {:9.3f} ms".format("open" if last else "closed",
                                            (t - since) / 1e6))
        last = now
        since = t

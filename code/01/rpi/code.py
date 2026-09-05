"""Blank screen at startup; each button key-down adds one to the count shown."""

import button
import count_display

display = count_display.CountDisplay()
btn = button.Button()

while True:
    btn.wait_for_press()
    display.increment()

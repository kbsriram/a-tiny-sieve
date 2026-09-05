"""Debounced push button on a Raspberry Pi Pico.

GP16 with the internal pull-up on; the other side of the switch goes to
ground, so the pin sits at 0V while pressed (active low) and is pulled to
3.3V when released.
"""

import time

import board
import digitalio

# The pin must hold one level with no opposite sample for this long before
# that level is accepted. Matches the ATtiny412 in ../../avr: it samples the
# button 31.25-46.875 ms after the last edge, which is 2 to 3 ticks of its
# 15.625 ms RTC period (task/task_button.c, hal/hal_rtc.c).
SETTLE_MS = 47


class Button:
    def __init__(self, pin=board.GP16, settle_ms=SETTLE_MS):
        self._settle_ns = settle_ms * 1_000_000
        self._pin = digitalio.DigitalInOut(pin)
        self._pin.direction = digitalio.Direction.INPUT
        self._pin.pull = digitalio.Pull.UP

    def wait_for_press(self):
        """Block until the button is pressed, and return SETTLE_MS after it is.

        The wait for a steady 3.3V happens first, so a button still held down
        from the previous call cannot report a second key-down.
        """
        self._wait_steady(True)   # released: pin at 3.3V
        self._wait_steady(False)  # pressed: pin at 0V

    def _wait_steady(self, level):
        # No sleep in this loop: it reads the pin every few microseconds, so a
        # spike far shorter than 1ms still restarts the window. The return
        # happens only on an iteration that just read `level`.
        since = time.monotonic_ns()
        while True:
            if self._pin.value != level:
                since = time.monotonic_ns()
            elif (time.monotonic_ns() - since) >= self._settle_ns:
                return

    def deinit(self):
        self._pin.deinit()

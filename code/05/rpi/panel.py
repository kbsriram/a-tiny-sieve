"""SSD1306 output for the stripboard panel.

128x64 at 0x3C on the same I2C bus as the cards. The 8x8 font gives 16
characters across and 8 lines down.

A full redraw sends 1024 bytes, 92 ms at 100 kHz; the init measured 114 ms, so
pins.I2C_TIMEOUT_US must stay above that. Cards take no I2C traffic while armed,
so a redraw belongs where they are disarmed or the REQ generator is stopped.

A missing display is not an error. Panel.present is False and every call does
nothing, so the same code runs with the OLED unfitted.
"""

import ssd1306
import pins

LINE_HEIGHT = 8
MAX_LINES = pins.OLED_HEIGHT // LINE_HEIGHT
MAX_CHARS = pins.OLED_WIDTH // 8


def _recover(i2c):
    """Finishes a display transfer that timed out part-way through.

    Measured on the stripboard: after the SSD1306 init raises ETIMEDOUT, the
    next bus scan leaves the first card command after it reading 0xff, three
    times out of three. One discarded read from the display address clears it.
    """
    try:
        i2c.readfrom(pins.OLED_ADDR, 1)
    except OSError:
        pass


class Panel:
    """The OLED, or a stand-in that discards everything written to it."""

    def __init__(self, i2c):
        self.oled = None
        try:
            if pins.OLED_ADDR in i2c.scan():
                self.oled = ssd1306.SSD1306_I2C(
                    pins.OLED_WIDTH, pins.OLED_HEIGHT, i2c, addr=pins.OLED_ADDR
                )
                self.clear()
        except OSError:
            self.oled = None
            _recover(i2c)

    @property
    def present(self):
        return self.oled is not None

    def clear(self):
        if self.oled is None:
            return
        self.oled.fill(0)
        self.oled.show()

    def show(self, *lines):
        """Redraws the panel, one line per argument. Extra lines and characters
        past the edge are dropped rather than wrapped."""
        if self.oled is None:
            return
        self.oled.fill(0)
        for row, line in enumerate(lines[:MAX_LINES]):
            self.oled.text(str(line)[:MAX_CHARS], 0, row * LINE_HEIGHT)
        self.oled.show()

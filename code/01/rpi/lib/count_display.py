"""Single-number SSD1306 readout for a Raspberry Pi Pico."""

from adafruit_display_text import bitmap_label
import adafruit_displayio_ssd1306
import board
import displayio
import i2cdisplaybus
import terminalio

_WHITE = 0xFFFFFF


class CountDisplay:
    """Owns the OLED and the count shown on it. Starts blank."""

    def __init__(self, i2c=None, address=0x3C, width=128, height=64):
        if i2c is None:
            # Pico board definition: SDA=GP4, SCL=GP5 on I2C0.
            i2c = board.STEMMA_I2C()

        displayio.release_displays()
        bus = i2cdisplaybus.I2CDisplayBus(i2c, device_address=address)
        self._display = adafruit_displayio_ssd1306.SSD1306(
            bus, width=width, height=height
        )

        self._count = None

        self._label = bitmap_label.Label(
            terminalio.FONT, text="", color=_WHITE, scale=5
        )
        # (0.5, 0.5) centres the text on the given position.
        self._label.anchor_point = (0.5, 0.5)
        self._label.anchored_position = (width // 2, height // 2)

        group = displayio.Group()
        group.append(self._label)
        self._display.root_group = group

    @property
    def count(self):
        """Current count, or None while the screen is still blank."""
        return self._count

    def increment(self):
        self._count = 0 if self._count is None else self._count + 1
        self._label.text = str(self._count)

    def clear(self):
        """Return to the blank screen it starts with."""
        self._count = None
        self._label.text = ""

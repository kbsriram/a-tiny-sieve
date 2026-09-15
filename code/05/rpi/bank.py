"""The fitted cards as one set: the I2C bus, REQ stepping, and the VOTE line.

REQ, VOTE, SDA and SCL are wired to every slot in parallel, so one REQ rising
edge steps every armed card at once and VOTE reads low if any armed card is
sinking it. Pin numbers come from pins.py; the card protocol from card.py.

REQ is driven low whenever a command goes out: the card firmware takes no I2C
traffic while armed, and an edge during a transaction would step the phase.
"""

import time

from machine import I2C, Pin

import pins
from card import ADDR_FIRST, ADDR_LAST, Card

# REQ high time and low time when stepping by hand. The card's interrupt handler
# takes 1.6 us from the edge to RETI at 10 MHz, so 50 us leaves VOTE settled
# long before it is read.
SETTLE_US = 50


def addresses(count):
    """The first `count` card addresses, 0x10 upwards, in slot order."""
    if not 1 <= count <= ADDR_LAST - ADDR_FIRST + 1:
        raise ValueError("count must be 1 to %d" % (ADDR_LAST - ADDR_FIRST + 1))
    return [ADDR_FIRST + i for i in range(count)]


class Bank:
    """Every fitted card, plus the REQ and VOTE lines they share."""

    def __init__(self, addrs):
        self.addrs = list(addrs)
        self.req = Pin(pins.PIN_REQ, Pin.OUT, value=0)
        if pins.VOTE_PULLUP:
            self.vote_pin = Pin(pins.PIN_VOTE, Pin.IN, Pin.PULL_UP)
        else:
            self.vote_pin = Pin(pins.PIN_VOTE, Pin.IN)
        self.i2c = I2C(
            pins.I2C_ID,
            sda=Pin(pins.PIN_SDA),
            scl=Pin(pins.PIN_SCL),
            freq=pins.I2C_HZ,
            timeout=pins.I2C_TIMEOUT_US,
        )
        self.cards = {addr: Card(self.i2c, addr) for addr in self.addrs}

    def slot(self, addr):
        """Slot number of a card, counting from 1 in address order."""
        return self.addrs.index(addr) + 1

    def scan(self):
        """Addresses answering on the bus, the OLED included."""
        return sorted(self.i2c.scan())

    def vote(self):
        """VOTE now. 1 means every armed card released it, 0 means one sinks it."""
        return self.vote_pin.value()

    def step(self, edges):
        """Sends `edges` REQ rising edges, returning the VOTE bit read after each.

        The string reads left to right in edge order, '1' released, '0' driven low.
        """
        self.req.value(0)
        time.sleep_us(SETTLE_US)  # REQ starts low, so the first change is a rise.

        seen = []
        for _ in range(edges):
            self.req.value(1)
            time.sleep_us(SETTLE_US)
            seen.append(self.vote_pin.value())
            self.req.value(0)
            time.sleep_us(SETTLE_US)
        return "".join(str(bit) for bit in seen)

    def req_low(self):
        """Holds REQ low, the state every I2C transaction needs."""
        self.req.value(0)
        time.sleep_us(SETTLE_US)

    def req_high(self):
        """Holds REQ high. Only for the roll call that looks for a REQ bridge."""
        self.req.value(1)
        time.sleep_us(SETTLE_US)

    def reset_all(self):
        """RESET every card. Returns the addresses that did not take it."""
        self.req_low()
        refused = []
        for addr in self.addrs:
            try:
                if not self.cards[addr].reset():
                    refused.append(addr)
            except OSError:
                refused.append(addr)
        return refused

    def states(self):
        """Status of every card, addr -> dict, or None where the read failed."""
        self.req_low()
        out = {}
        for addr in self.addrs:
            try:
                out[addr] = self.cards[addr].state()
            except OSError:
                out[addr] = None
        return out

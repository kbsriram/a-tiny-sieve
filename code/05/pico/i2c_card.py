"""Writes commands to a card over I2C and reads its status, for task 6 of log 5.

MicroPython on a Raspberry Pi Pico, wired as code/04/README.md describes. The
card must be running the task 6 build of code/05/avr/src.

Every command is opcode, payload, then a CRC-8 check byte over the address byte
(addr << 1), the opcode and the payload. The card acknowledges every byte and
answers with a response code the host reads next: 0x00 taken, 0xff failed. A
STATUS command is answered by that code and 5 status bytes, the last a CRC over
addr << 1 | 1 and the four before it.

Pull-ups: the RP2040's internal ones, which machine.I2C enables, in parallel
with the card's own on PA1 and PA2.
"""

import time

from machine import I2C, Pin

import pins

OP_SET_RING = 0x01
OP_RESET = 0x02
OP_ARM = 0x03
OP_LED = 0x04
OP_STATUS = 0x05

TAKEN = 0x00
FAILED = 0xFF

FLAG_ARMED = 0x40
FW_VERSION = 0x01

RING_BYTES = 16
STATUS_READ = 6


def crc8(data, crc=0x00):
    """CRC-8 PEC: polynomial 0x07, init 0x00, no bit reversal, no final xor."""
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def ring_bytes(phases):
    """Ring with bit `phase` set for each phase in `phases`: release VOTE there."""
    ring = bytearray(RING_BYTES)
    for phase in phases:
        ring[phase // 8] |= 1 << (phase % 8)
    return bytes(ring)


class Card:
    """One card on the bus, addressed by its build-time I2C address."""

    def __init__(self, i2c, addr):
        self.i2c = i2c
        self.addr = addr

    def frame(self, opcode, payload=b""):
        body = bytes([opcode]) + bytes(payload)
        return body + bytes([crc8(bytes([self.addr << 1]) + body)])

    def write(self, frame):
        """Sends the bytes. Raises OSError if the card does not answer at all."""
        self.i2c.writeto(self.addr, frame)

    def command(self, opcode, payload=b""):
        """Runs one command; True when the card reports it took it."""
        self.write(self.frame(opcode, payload))
        return self.i2c.readfrom(self.addr, 1)[0] == TAKEN

    def read_status(self):
        """STATUS, then the 6 bytes it makes available. None if the CRC fails."""
        self.write(self.frame(OP_STATUS))
        data = self.i2c.readfrom(self.addr, STATUS_READ)
        if data[0] != TAKEN:
            return None
        if crc8(bytes([(self.addr << 1) | 1]) + data[1:5]) != data[5]:
            return None
        return data

    def state(self):
        """Status as a dict: phase, reset flags, armed, modulus, version."""
        data = self.read_status()
        if data is None:
            return None
        return {
            "phase": data[1],
            "rstfr": data[2] & 0x3F,
            "armed": bool(data[2] & FLAG_ARMED),
            "modulus": data[3],
            "version": data[4],
        }


def bus():
    """The I2C bus, with REQ held low so no read lands on a REQ edge."""
    Pin(pins.PIN_REQ_PA6, Pin.OUT, value=0)
    return I2C(
        pins.I2C_ID,
        sda=Pin(pins.PIN_SDA_PA1),
        scl=Pin(pins.PIN_SCL_PA2),
        freq=pins.I2C_HZ,
    )


def _report(name, ok):
    print("%s: %s" % ("PASS" if ok else "FAIL", name))
    return bool(ok)


def check_commands(card):
    """Each command, and the state it must leave behind."""
    ok = _report("RESET taken", card.command(OP_RESET))
    state = card.state()
    ok &= _report(
        "after RESET: disarmed, modulus 0, phase 0",
        state is not None
        and state["modulus"] == 0
        and state["phase"] == 0
        and not state["armed"],
    )
    ok &= _report(
        "firmware version %d" % FW_VERSION,
        state is not None and state["version"] == FW_VERSION,
    )

    # Modulus 7, VOTE released at phases 0, 3 and 6.
    ring = ring_bytes([0, 3, 6])
    ok &= _report("SET_RING taken", card.command(OP_SET_RING, bytes([7]) + ring))
    state = card.state()
    ok &= _report(
        "after SET_RING: modulus 7, disarmed",
        state is not None and state["modulus"] == 7 and not state["armed"],
    )

    ok &= _report("LED on taken while disarmed", card.command(OP_LED, b"\x01"))
    ok &= _report("LED off taken while disarmed", card.command(OP_LED, b"\x00"))

    ok &= _report("ARM at phase 7 failed", not card.command(OP_ARM, b"\x07"))
    ok &= _report("ARM at phase 5 taken", card.command(OP_ARM, b"\x05"))
    state = card.state()
    ok &= _report(
        "after ARM: armed, phase 5",
        state is not None and state["armed"] and state["phase"] == 5,
    )

    ok &= _report("LED failed while armed", not card.command(OP_LED, b"\x01"))
    ok &= _report("RESET taken while armed", card.command(OP_RESET))
    state = card.state()
    ok &= _report(
        "after RESET: disarmed, modulus 0",
        state is not None and not state["armed"] and state["modulus"] == 0,
    )
    return ok


def check_read_crc(card):
    """A flipped bit in a status byte must fail the host's CRC check."""
    card.write(card.frame(OP_STATUS))
    data = card.i2c.readfrom(card.addr, STATUS_READ)
    good = crc8(bytes([(card.addr << 1) | 1]) + data[1:5]) == data[5]

    bad = bytearray(data)
    bad[1] ^= 0x01
    rejected = crc8(bytes([(card.addr << 1) | 1]) + bad[1:5]) != bad[5]
    return _report("read CRC checks out, and rejects a flipped bit", good and rejected)


def check_corrupt_command(card):
    """A flipped bit in a command: response code 0xff, state unchanged."""
    card.command(OP_RESET)
    card.command(OP_SET_RING, bytes([7]) + ring_bytes([0, 3, 6]))
    before = card.state()

    frame = bytearray(card.frame(OP_SET_RING, bytes([30]) + ring_bytes([1])))
    frame[1] ^= 0x01  # Flips the modulus from 30 to 31.
    card.write(frame)
    failed = card.i2c.readfrom(card.addr, 1)[0] == FAILED

    after = card.state()
    return _report(
        "corrupt command reads 0xff, state unchanged",
        failed and before is not None and after == before,
    )


def check_alternating(card, rounds=10):
    """Corrupt and legal commands in turn; every legal one must be taken.

    An earlier build acknowledged a corrupt frame and then held SCL low through
    the next transaction, on every second attempt.
    """
    card.command(OP_RESET)
    card.command(OP_SET_RING, bytes([7]) + ring_bytes([0, 3, 6]))

    corrupt = bytearray(card.frame(OP_LED, b"\x00"))
    corrupt[2] ^= 0x01
    ok = True
    for i in range(rounds):
        card.write(corrupt)
        if card.i2c.readfrom(card.addr, 1)[0] != FAILED:
            ok = False
            print("  round %d: corrupt command was not refused" % i)
        if not card.command(OP_LED, b"\x00"):
            ok = False
            print("  round %d: legal command was refused" % i)
    return _report("%d corrupt commands alternating with legal ones" % rounds, ok)


def check_two_cards(i2c, addr_a, addr_b):
    """Each card answers only its own address."""
    a, b = Card(i2c, addr_a), Card(i2c, addr_b)
    a.command(OP_RESET)
    b.command(OP_RESET)

    a.command(OP_SET_RING, bytes([7]) + ring_bytes([0]))
    b.command(OP_SET_RING, bytes([11]) + ring_bytes([0]))

    sa, sb = a.state(), b.state()
    return _report(
        "two cards: 0x%02x reads 7, 0x%02x reads 11" % (addr_a, addr_b),
        sa is not None and sb is not None and sa["modulus"] == 7 and sb["modulus"] == 11,
    )


def check_after_stuck_sda(card):
    """Run after holding SDA low by hand mid-transaction and releasing it.

    Pulling SDA low aborts whatever byte was in flight. The card's TWI client
    waits for the next Start condition, so the next transaction must work with
    no reset and no power cycle.
    """
    time.sleep_ms(10)
    return _report("card answers the transaction after a stuck SDA", card.state() is not None)


def main(addr=0x10, addr_b=None):
    i2c = bus()
    print("addresses on the bus: %s" % [hex(a) for a in i2c.scan()])

    card = Card(i2c, addr)
    ok = check_commands(card)
    ok &= check_read_crc(card)
    ok &= check_corrupt_command(card)
    ok &= check_alternating(card)
    if addr_b is not None:
        ok &= check_two_cards(i2c, addr, addr_b)

    card.command(OP_RESET)
    print("PASS" if ok else "FAILED")
    return ok


if __name__ == "__main__":
    main()

"""One ATtiny412 card over I2C: framing, the five commands, status decode.

Protocol: code/05/avr/src/task/task_cmd.c and docs 05_avr_design.md. Every
command is an opcode, its payload, then a CRC-8 check byte over the address
byte (addr << 1), the opcode and the payload. The card acknowledges every byte
and answers with a response code the host reads next: 0x00 taken, 0xff failed.
A STATUS command is answered by that code and 5 status bytes, the last a CRC
over addr << 1 | 1 and the four before it.

No pin or bus setup here: the caller supplies a machine.I2C, so the same module
serves the test jig and the stripboard backplane.
"""

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

ADDR_FIRST = 0x10
ADDR_LAST = 0x2D

# RSTCTRL.RSTFR bits, snapshotted by the card at boot (05_avr_design.md).
RSTFR_PORF = 0x01  # Power-on.
RSTFR_BORF = 0x02  # Brown-out.
RSTFR_EXTRF = 0x04  # External reset pin.
RSTFR_WDRF = 0x08  # Watchdog.
RSTFR_SWRF = 0x10  # Software.
RSTFR_UPDIRF = 0x20  # UPDI, which is what flashing leaves behind.


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

    def reset(self):
        """Disarm, phase 0, ring cleared, VOTE released, LED dark."""
        return self.command(OP_RESET)

    def set_ring(self, modulus, phases):
        """Loads the modulus and the phases that release VOTE. Disarms."""
        return self.command(OP_SET_RING, bytes([modulus]) + ring_bytes(phases))

    def arm(self, phase):
        """Enables the REQ edge, starting at `phase`. Refused at or above the
        modulus."""
        return self.command(OP_ARM, bytes([phase]))

    def led(self, on):
        """Lights the LED or darkens it. Refused while armed."""
        return self.command(OP_LED, b"\x01" if on else b"\x00")

#!/usr/bin/env python3
"""Reference model for the card, written from 05_avr_design.md.

The card holds a 128-bit ring and a phase counter. On each REQ rising edge it
reports the ring bit at the current phase (1 releases VOTE, 0 drives VOTE low),
then advances the phase, wrapping at the modulus rather than at 128. Over I2C
it takes four commands, each ending in a CRC-8 check byte computed over the
address byte, the opcode, and the payload.

Running this file rewrites vectors_sieve.txt and vectors_cmd.txt. The host
tests read those files, so `make test` never needs Python.
"""

import pathlib

RING_BYTES = 16
MODULUS_MIN = 2
MODULUS_MAX = 128
MODULI = [2, 3, 7, 30, 127, 128]
STEPS = 400


def ring_bit(ring, phase):
    """Bit `phase` of the ring: bit (phase % 8) of byte (phase // 8), LSB first."""
    return (ring[phase // 8] >> (phase % 8)) & 1


def step_case(modulus, ring, arm_phase, steps):
    """Decisions for `steps` REQ edges, starting armed at `arm_phase`."""
    out = []
    phase = arm_phase
    for _ in range(steps):
        out.append(ring_bit(ring, phase))
        phase = (phase + 1) % modulus
    return out


def set_bits(indices):
    ring = bytearray(RING_BYTES)
    for i in indices:
        ring[i // 8] |= 1 << (i % 8)
    return bytes(ring)


def lcg_ring(seed):
    """Deterministic pseudo-random ring, so vectors do not depend on Python."""
    x = seed
    out = bytearray()
    for _ in range(RING_BYTES):
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        out.append((x >> 16) & 0xFF)
    return bytes(out)


def cases():
    for modulus in MODULI:
        rings = [
            ("all clear", bytes(RING_BYTES)),
            ("all set", b"\xff" * RING_BYTES),
            ("only phase 0", set_bits([0])),
            ("only phase modulus-1", set_bits([modulus - 1])),
            ("pseudo-random", lcg_ring(modulus)),
        ]
        for index, (_, ring) in enumerate(rings):
            arm_phase = (index * 3) % modulus
            yield modulus, ring, arm_phase


CRC_POLY = 0x07

OP_SET_RING = 0x01
OP_RESET = 0x02
OP_ARM = 0x03
OP_LED = 0x04


def crc8(data, crc=0x00):
    """CRC-8 PEC: polynomial 0x07, init 0x00, no bit reversal, no final xor."""
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ CRC_POLY) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


class Card:
    """Command state of one card: ring, phase, armed flag, LED."""

    def __init__(self, addr):
        self.addr = addr
        self.reset()

    def reset(self):
        self.modulus = 0
        self.phase = 0
        self.armed = False
        self.led = False

    def frame(self, opcode, payload):
        """The bytes a host writes: opcode, payload, then the CRC check byte."""
        body = bytes([opcode]) + bytes(payload)
        return body + bytes([crc8(bytes([self.addr << 1]) + body)])

    def apply(self, opcode, payload):
        """Runs one command. False means the card NACKs the CRC byte."""
        if opcode == OP_SET_RING:
            modulus = payload[0]
            if not MODULUS_MIN <= modulus <= MODULUS_MAX:
                return False
            self.modulus = modulus
            self.phase = 0
            self.armed = False
            return True
        if opcode == OP_RESET:
            self.reset()
            return True
        if opcode == OP_ARM:
            if self.modulus == 0 or payload[0] >= self.modulus:
                return False
            self.phase = payload[0]
            self.armed = True
            return True
        if opcode == OP_LED:
            if self.armed:
                return False
            self.led = payload[0] != 0
            return True
        return False


def crc_cases():
    """60 byte strings of 1 to 20 bytes, from the same LCG as the rings."""
    x = 2024
    for length in range(1, 21):
        for _ in range(3):
            data = bytearray()
            for _ in range(length):
                x = (x * 1103515245 + 12345) & 0x7FFFFFFF
                data.append((x >> 16) & 0xFF)
            yield bytes(data)


def scenarios():
    """Command sequences per address; the address changes every CRC."""
    ring7 = lcg_ring(7)
    yield 0x10, [
        (OP_SET_RING, bytes([7]) + ring7),
        (OP_ARM, [3]),
        (OP_LED, [1]),  # Rejected: LED is accepted only while disarmed.
        (OP_RESET, []),
        (OP_LED, [1]),
        (OP_LED, [0]),
    ]
    yield 0x2D, [
        (OP_ARM, [0]),  # Rejected: no ring loaded.
        (OP_SET_RING, bytes([MODULUS_MIN - 1]) + bytes(RING_BYTES)),
        (OP_SET_RING, bytes([MODULUS_MAX + 1]) + bytes(RING_BYTES)),
        (OP_SET_RING, bytes([MODULUS_MAX]) + b"\xff" * RING_BYTES),
        (OP_ARM, [MODULUS_MAX]),  # Rejected: phase is not below the modulus.
        (OP_ARM, [MODULUS_MAX - 1]),
    ]
    yield 0x11, [
        (OP_SET_RING, bytes([2]) + set_bits([0])),
        (OP_ARM, [1]),
        (OP_SET_RING, bytes([3]) + set_bits([2])),  # Accepted, and disarms.
        (OP_LED, [0x80]),  # Any non-zero state lights the LED.
    ]


def write_cmd_vectors(path):
    lines = [
        "# Generated by model.py. Do not edit.",
        "# crc <data bytes, hex> <expected CRC-8 PEC, hex>",
        "# scenario <client address, hex>: a card in its boot state.",
        "# frame <bytes written, hex, CRC byte last> <accepted 0|1>"
        " <modulus> <phase> <armed 0|1> <led 0|1>",
        "# The four state fields are the card state after that frame.",
    ]
    for data in crc_cases():
        lines.append(f"crc {data.hex()} {crc8(data):02x}")
    for addr, commands in scenarios():
        lines.append(f"scenario {addr:02x}")
        card = Card(addr)
        for opcode, payload in commands:
            frame = card.frame(opcode, payload)
            ok = card.apply(opcode, payload)
            lines.append(
                f"frame {frame.hex()} {int(ok)} {card.modulus} {card.phase}"
                f" {int(card.armed)} {int(card.led)}"
            )
    path.write_text("\n".join(lines) + "\n")
    print(f"wrote {path}")


def main():
    write_cmd_vectors(pathlib.Path(__file__).with_name("vectors_cmd.txt"))
    path = pathlib.Path(__file__).with_name("vectors_sieve.txt")
    lines = [
        "# Generated by model.py. Do not edit.",
        "# case <modulus> <16 ring bytes, hex, byte 0 first> <arm phase> <steps>",
        "# then one line of that many decisions, 1 release VOTE, 0 drive VOTE low.",
    ]
    for modulus, ring, arm_phase in cases():
        lines.append(f"case {modulus} {ring.hex()} {arm_phase} {STEPS}")
        lines.append("".join(str(b) for b in step_case(modulus, ring, arm_phase, STEPS)))
    path.write_text("\n".join(lines) + "\n")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()

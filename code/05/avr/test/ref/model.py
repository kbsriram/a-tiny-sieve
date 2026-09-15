#!/usr/bin/env python3
"""Reference model for the card, written from 05_avr_design.md.

The card holds a 128-bit ring and a phase counter. On each REQ rising edge it
reports the ring bit at the current phase (1 releases VOTE, 0 drives VOTE low),
then advances the phase, wrapping at the modulus rather than at 128. Over I2C
it takes four commands, each ending in a CRC-8 check byte computed over the
address byte, the opcode, and the payload. It answers every command with a
one-byte response code the host reads back, and a read after an accepted STATUS
command carries 5 status bytes after that code.

Running this file rewrites vectors_sieve.txt and vectors_cmd.txt. The host
tests read those files, so `make test` never needs Python.
"""

import pathlib

RING_BYTES = 16
MODULUS_MIN = 2
MODULUS_MAX = 128
MODULI = [2, 3, 7, 30, 127, 128]
STEPS = 400

# The ring src/main.c compiles in for task 5, and the number of REQ edges
# code/05/pico/req_walk.py sends: two full wraps plus one edge.
REQ_MODULUS = 7
REQ_RING = bytes([0x49] + [0] * (RING_BYTES - 1))
REQ_ARM_PHASE = 0
REQ_EDGES = REQ_MODULUS * 2 + 1


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

FW_VERSION = 0x01
FLAG_ARMED = 0x40
TAKEN = 0x00
FAILED = 0xFF

# RSTCTRL.RSTFR snapshots and phases the status vectors step through. Neither
# comes from a command, so the model just cycles fixed values through them.
RESET_FLAGS = [0x01, 0x02, 0x20, 0x3F, 0x00, 0x09]
STATUS_PHASES = [0, 1, 5, 42, 126, 127]

OP_SET_RING = 0x01
OP_RESET = 0x02
OP_ARM = 0x03
OP_LED = 0x04
OP_STATUS = 0x05


def crc8(data, crc=0x00):
    """CRC-8 PEC: polynomial 0x07, init 0x00, no bit reversal, no final xor."""
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ CRC_POLY) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


class Card:
    """Command state of one card: modulus, armed flag, LED.

    No phase: the card keeps it in the REQ handler's pointer register, not in
    the command decoder, so no host test can read it back. vectors_req.txt
    covers the phase, through VOTE on real hardware.
    """

    def __init__(self, addr):
        self.addr = addr
        self.response = FAILED
        self.last_op = 0
        self.reset()

    def reset(self):
        self.modulus = 0
        self.armed = False
        self.led = False

    def frame(self, opcode, payload):
        """The bytes a host writes: opcode, payload, then the CRC check byte."""
        body = bytes([opcode]) + bytes(payload)
        return body + bytes([crc8(bytes([self.addr << 1]) + body)])

    def read(self, phase, reset_flags):
        """What the next I2C read returns: the response code, then any status."""
        if self.response != TAKEN or self.last_op != OP_STATUS:
            return bytes([self.response])
        body = bytes(
            [
                phase,
                (reset_flags & 0x3F) | (FLAG_ARMED if self.armed else 0),
                self.modulus,
                FW_VERSION,
            ]
        )
        return (
            bytes([self.response])
            + body
            + bytes([crc8(bytes([(self.addr << 1) | 1]) + body)])
        )

    def run(self, opcode, payload):
        """One command frame: applies it and latches the response code."""
        ok = self.apply(opcode, payload)
        self.response = TAKEN if ok else FAILED
        if ok:
            self.last_op = opcode
        return ok

    def apply(self, opcode, payload):
        """Runs one command. False means the card NACKs the CRC byte."""
        if opcode == OP_SET_RING:
            modulus = payload[0]
            if not MODULUS_MIN <= modulus <= MODULUS_MAX:
                return False
            self.modulus = modulus
            self.armed = False
            return True
        if opcode == OP_RESET:
            self.reset()
            return True
        if opcode == OP_ARM:
            if self.modulus == 0 or payload[0] >= self.modulus:
                return False
            self.armed = True
            return True
        if opcode == OP_LED:
            if self.armed:
                return False
            self.led = payload[0] != 0
            return True
        if opcode == OP_STATUS:
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
        (OP_STATUS, []),
        (OP_ARM, [3]),
        (OP_STATUS, []),
        (OP_LED, [1]),  # Fails: LED is taken only while disarmed.
        (OP_STATUS, []),
        (OP_RESET, []),
        (OP_LED, [1]),
        (OP_LED, [0]),
    ]
    yield 0x2D, [
        (OP_ARM, [0]),  # Fails: no ring loaded.
        (OP_SET_RING, bytes([MODULUS_MIN - 1]) + bytes(RING_BYTES)),
        (OP_SET_RING, bytes([MODULUS_MAX + 1]) + bytes(RING_BYTES)),
        (OP_SET_RING, bytes([MODULUS_MAX]) + b"\xff" * RING_BYTES),
        (OP_ARM, [MODULUS_MAX]),  # Fails: phase is not below the modulus.
        (OP_STATUS, []),
        (OP_ARM, [MODULUS_MAX - 1]),
        (OP_STATUS, []),
    ]
    yield 0x11, [
        (OP_SET_RING, bytes([2]) + set_bits([0])),
        (OP_ARM, [1]),
        (OP_SET_RING, bytes([3]) + set_bits([2])),  # Taken, and disarms.
        (OP_STATUS, []),
        (OP_LED, [0x80]),  # Any non-zero state lights the LED.
        (OP_STATUS, []),
        (OP_ARM, [3]),  # Fails: a read after it returns the code alone.
    ]


def write_cmd_vectors(path):
    lines = [
        "# Generated by model.py. Do not edit.",
        "# crc <data bytes, hex> <expected CRC-8 PEC, hex>",
        "# scenario <client address, hex>: a card in its boot state.",
        "# frame <bytes written, hex, CRC byte last> <accepted 0|1>"
        " <modulus> <armed 0|1> <led 0|1>",
        "# The three state fields are the card state after that frame.",
        "# read <phase> <RSTFR snapshot, hex> <bytes the next I2C read returns, hex>",
        "# One read line follows each frame line, for the state it left.",
    ]
    for data in crc_cases():
        lines.append(f"crc {data.hex()} {crc8(data):02x}")
    for addr, commands in scenarios():
        lines.append(f"scenario {addr:02x}")
        card = Card(addr)
        for index, (opcode, payload) in enumerate(commands):
            frame = card.frame(opcode, payload)
            ok = card.run(opcode, payload)
            lines.append(
                f"frame {frame.hex()} {int(ok)} {card.modulus}"
                f" {int(card.armed)} {int(card.led)}"
            )
            phase = STATUS_PHASES[index % len(STATUS_PHASES)]
            flags = RESET_FLAGS[index % len(RESET_FLAGS)]
            read = card.read(phase, flags)
            lines.append(f"read {phase} {flags:02x} {read.hex()}")
    path.write_text("\n".join(lines) + "\n")
    print(f"wrote {path}")


def write_req_vectors(path):
    """Expected VOTE level after each REQ edge, for the task 5 hardcoded ring.

    code/05/pico/req_walk.py holds a copy of the `expect` line below and
    compares it against what it reads on PA3.
    """
    bits = step_case(REQ_MODULUS, REQ_RING, REQ_ARM_PHASE, REQ_EDGES)
    path.write_text(
        "\n".join(
            [
                "# Generated by model.py. Do not edit.",
                "# The ring src/main.c compiles in for task 5.",
                f"modulus {REQ_MODULUS}",
                f"ring {REQ_RING.hex()}",
                f"arm {REQ_ARM_PHASE}",
                f"edges {REQ_EDGES}",
                "# VOTE after each edge: 1 released (pulled high), 0 driven low.",
                "expect " + "".join(str(b) for b in bits),
            ]
        )
        + "\n"
    )
    print(f"wrote {path}")


def main():
    write_req_vectors(pathlib.Path(__file__).with_name("vectors_req.txt"))
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

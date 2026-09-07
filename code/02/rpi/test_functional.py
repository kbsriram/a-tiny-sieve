"""Degenerate ring patterns on one ATtiny, driven by the PIO runner.

check_16.py only loads the three real quadratic-residue rings and only sees
the wired-AND of VOTE, so all-reject, all-accept, alternating and single-bit
rings are not covered there. Every other chip on the bus is left disarmed.
"""

import time

import machine

import pins
import sieve
import sieve_runner

MODULUS = 11
NUM_CANDIDATES = 1000


def run_case(runner, name, modulus, ring_bits, num_candidates=NUM_CANDIDATES):
    accepts = [(ring_bits[i // 8] >> (i % 8)) & 1 for i in range(modulus)]
    expected = [k for k in range(num_candidates) if accepts[k % modulus]]

    runner.configure_array([(modulus, ring_bits)], start_candidate=0)

    if not expected:
        ok = runner.quiet_for(num_candidates)
        runner.pause()
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: 0 survivors expected in "
              f"{num_candidates} candidates")
        return ok

    t0 = time.ticks_us()
    got = [runner.next_survivor() for _ in range(len(expected))]
    elapsed_us = time.ticks_diff(time.ticks_us(), t0)
    runner.pause()

    ok = got == expected
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {len(expected)} survivors in "
          f"{num_candidates} candidates ({elapsed_us / 1000:.1f} ms)")
    if not ok:
        for i, (exp, act) in enumerate(zip(expected, got)):
            if exp != act:
                print(f"       first mismatch at survivor #{i}: "
                      f"expected {exp}, got {act}")
                break
    return ok


def main():
    i2c = machine.I2C(0, scl=machine.Pin(pins.PIN_SCL),
                      sda=machine.Pin(pins.PIN_SDA), freq=400000)
    req = machine.Pin(pins.PIN_REQ, machine.Pin.OUT)
    vote = machine.Pin(pins.PIN_VOTE, machine.Pin.IN, machine.Pin.PULL_UP)

    devices = [d for d in i2c.scan() if d != 0x3C]
    if not devices:
        print("No ATtiny sieves found.")
        return

    nodes = [sieve.Sieve(i2c, addr) for addr in devices]
    # Disarm every chip so only the one under test can pull VOTE low.
    for node in nodes:
        node.reset()
        time.sleep_ms(2)

    runner = sieve_runner.SieveRunner(req, vote, sieves=nodes[:1], sm_id=0,
                                      freq=5000000)
    print(f"Testing {hex(devices[0])} at modulus {MODULUS}, "
          f"{NUM_CANDIDATES} candidates per case at 50 kHz "
          f"({len(nodes) - 1} other chip(s) disarmed)...")

    single_bit = bytearray(16)
    single_bit[0] = 0x04  # accept only phase 2

    cases = [
        ("All-accept", bytearray([0xFF] * 16)),
        ("All-reject", bytearray(16)),
        ("Alternating", bytearray([0xAA] * 16)),
        ("Single set bit", single_bit),
    ]

    all_pass = True
    for name, ring_bits in cases:
        all_pass &= run_case(runner, name, MODULUS, ring_bits)

    print("\nALL TESTS PASSED." if all_pass else "\nSOME TESTS FAILED.")


if __name__ == "__main__":
    main()

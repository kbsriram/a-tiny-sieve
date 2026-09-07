"""Progressive activation: arm 1, then 2, ... N chips and re-check survivors.

Confirms the chips left disarmed never pull VOTE low, which is the only
coverage of the disarmed path in task_sieve_step(). check_16.py always runs
all three chips armed.
"""

import random
import time

import machine

import pins
import sieve
import sieve_runner

PRIME_MODULI = [5, 7, 11, 13, 17, 19, 23, 29, 31]
NUM_CANDIDATES = 10000


def generate_ring(modulus, accept_rate=0.5):
    """Random ring, forced to hold at least one accept and one reject bit."""
    bits = bytearray(16)
    votes = [0] * modulus
    for i in range(modulus):
        if random.random() < accept_rate:
            bits[i // 8] |= 1 << (i % 8)
            votes[i] = 1
    if sum(votes) == 0:
        bits[0] |= 1
        votes[0] = 1
    elif sum(votes) == modulus:
        bits[0] &= ~1
        votes[0] = 0
    return bits, votes


def run_stage(runner, nodes, configs, k, num_candidates=NUM_CANDIDATES):
    """Arms the first k chips, leaves the rest disarmed, compares survivors."""
    for node in nodes:
        node.reset()
        time.sleep_ms(2)

    active = configs[:k]
    runner.sieves = nodes[:k]

    expected = [
        c for c in range(num_candidates)
        if all(votes[c % modulus] for modulus, _, votes in active)
    ]

    runner.configure_array([(m, bits) for m, bits, _ in active],
                           start_candidate=0)

    moduli = [m for m, _, _ in active]
    theo_rate = 100.0
    for modulus, _, votes in active:
        theo_rate *= sum(votes) / modulus

    if not expected:
        ok = runner.quiet_for(num_candidates)
        runner.pause()
        print(f"[{'PASS' if ok else 'FAIL'}] {k}/{len(nodes)} armed "
              f"(moduli {moduli}): 0 survivors expected")
        return ok, 0, 0.0, theo_rate

    t0 = time.ticks_us()
    got = [runner.next_survivor() for _ in range(len(expected))]
    elapsed_us = time.ticks_diff(time.ticks_us(), t0)
    runner.pause()

    ok = got == expected
    reached = expected[-1] + 1
    obs_rate = 100.0 * len(expected) / reached
    rate_khz = (reached * 1000) / elapsed_us if elapsed_us > 0 else 0.0

    print(f"[{'PASS' if ok else 'FAIL'}] {k}/{len(nodes)} armed "
          f"(moduli {moduli}):")
    print(f"       {len(got)} survivors in {reached} candidates "
          f"({obs_rate:.2f}% observed, {theo_rate:.2f}% theoretical)")
    print(f"       {elapsed_us / 1000:.1f} ms ({rate_khz:.2f} kHz)")
    if not ok:
        for i, (exp, act) in enumerate(zip(expected, got)):
            if exp != act:
                print(f"       first mismatch at survivor #{i}: "
                      f"expected {exp}, got {act}")
                break
    return ok, len(got), obs_rate, theo_rate


def main():
    random.seed(42)
    i2c = machine.I2C(0, scl=machine.Pin(pins.PIN_SCL),
                      sda=machine.Pin(pins.PIN_SDA), freq=400000)
    req = machine.Pin(pins.PIN_REQ, machine.Pin.OUT)
    vote = machine.Pin(pins.PIN_VOTE, machine.Pin.IN, machine.Pin.PULL_UP)

    devices = [d for d in i2c.scan() if d != 0x3C]
    if not devices:
        print("No ATtiny sieves found.")
        return

    nodes = [sieve.Sieve(i2c, addr) for addr in devices]
    print(f"I2C scan found {len(nodes)} ATtiny sieve(s): "
          f"{[hex(d) for d in devices]}")

    configs = []
    for i, addr in enumerate(devices):
        modulus = PRIME_MODULI[i % len(PRIME_MODULI)]
        bits, votes = generate_ring(modulus)
        configs.append((modulus, bits, votes))
        print(f"  {hex(addr)}: mod {modulus:2d}, {sum(votes)}/{modulus} accept "
              f"({100.0 * sum(votes) / modulus:.1f}%)")

    runner = sieve_runner.SieveRunner(req, vote, sieves=nodes, sm_id=0,
                                      freq=5000000)

    print(f"\nRunning {NUM_CANDIDATES} candidates per stage at 50 kHz...")
    results = []
    all_pass = True
    for k in range(1, len(nodes) + 1):
        ok, count, obs_rate, theo_rate = run_stage(runner, nodes, configs, k)
        all_pass &= ok
        results.append((k, [m for m, _, _ in configs[:k]], count, obs_rate,
                        theo_rate, ok))

    print("\n" + "=" * 65)
    print(f"{'Armed':<8}{'Moduli':<20}{'Observed':<20}{'Theoretical':<14}Status")
    print("-" * 65)
    for k, moduli, count, obs_rate, theo_rate, ok in results:
        print(f"{k:<8}{str(moduli):<20}{f'{obs_rate:.2f}% ({count})':<20}"
              f"{f'{theo_rate:.2f}%':<14}{'PASS' if ok else 'FAIL'}")
    print("=" * 65)

    print("\nALL TESTS PASSED." if all_pass else "\nSOME TESTS FAILED.")


if __name__ == "__main__":
    main()

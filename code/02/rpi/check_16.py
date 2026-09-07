"""Factors 16-digit M = 5283065753709209 = x^2 + 7y^2.
Prunes y = 4k (since M = 1 mod 8). Steps k at 50 kHz across
moduli [5, 11, 23], verifying (M - 7*(4k)^2) mod p in squares(p).
Survivors are tested for exact squares to find Lehmer's factors.
"""

import time
from machine import I2C, Pin
import pins
from sieve import Sieve
from sieve_runner import SieveRunner

# Modes to execute (flip as needed)
RUN_VERIFY = True  # Mode A: 10,000 candidate lint check
RUN_FULL = True  # Mode B: Full streaming hunt to completion

M = 5283065753709209
MODULI = [5, 11, 23]
MAX_K = 6868058  # y = 4k <= isqrt(M // 7) = 27472234

# Fast modulo 64 quadratic residue filter
SQ64 = bytearray(64)
for i in range(64):
    SQ64[(i * i) & 63] = 1


def isqrt(n):
    """Integer square root via Newton's method."""
    if n < 2:
        return n
    x = n
    y = (x + 1) // 2
    while y < x:
        x = y
        y = (x + n // x) // 2
    return x


def check_square(n):
    """Returns (root, True) if n is an exact integer square, else (0, False)."""
    # First run another fast modulus check to reject candidates quickly
    if n < 0 or not SQ64[n & 63]:
        return 0, False
    # Calculate the actual square root now
    r = isqrt(n)
    return r, (r * r == n)


def gcd(a, b):
    while b:
        a, b = b, a % b
    return a


def make_ring(p, m_val=M):
    """Builds 16-byte truth table for modulus p with candidate k where y = 4k."""
    squares = {(r * r) % p for r in range(p)}
    bits = bytearray(16)
    expected_phases = []
    for k in range(p):
        y = (4 * k) % p
        if (m_val - 7 * y * y) % p in squares:
            bits[k // 8] |= 1 << (k % 8)
            expected_phases.append(k)
    return bits, expected_phases


def setup_hardware():
    i2c = I2C(0, scl=Pin(pins.PIN_SCL), sda=Pin(pins.PIN_SDA), freq=400000)
    req = Pin(pins.PIN_REQ, Pin.OUT)
    vote = Pin(pins.PIN_VOTE, Pin.IN, Pin.PULL_UP)

    # Dynamically discover the number of connected tinys with a scan on the i2c bus.
    # 0x3C is a display, which we skip.
    devices = [d for d in i2c.scan() if d != 0x3C]
    if len(devices) < len(MODULI):
        raise RuntimeError(
            f"Found {len(devices)} ATtinys ({[hex(d) for d in devices]}), need {len(MODULI)}"
        )

    sieves = [Sieve(i2c, addr) for addr in devices[: len(MODULI)]]
    runner = SieveRunner(req, vote, sieves=sieves, sm_id=0, freq=5000000)

    configs = []
    oracle_accepts = {}
    for p in MODULI:
        bits, exp_phases = make_ring(p)
        configs.append((p, bits))
        oracle_accepts[p] = set(exp_phases)

    return runner, configs, oracle_accepts


def verify_sample(runner, configs, oracle_accepts, num_candidates=10000):
    """Mode A: Verifies hardware survivors strictly match mathematical expectation."""
    print(f"\n--- Mode A: Lint & Verification (first {num_candidates} candidates) ---")
    expected = [
        k
        for k in range(num_candidates)
        if all((k % p) in oracle_accepts[p] for p in MODULI)
    ]
    print(
        f"Expecting {len(expected)} survivors ({100.0 * len(expected) / num_candidates:.2f}% pass rate)..."
    )

    runner.configure_array(configs, start_candidate=0)
    t0 = time.ticks_us()
    hw_survivors = [runner.next_survivor() for _ in range(len(expected))]
    elapsed_us = time.ticks_diff(time.ticks_us(), t0)
    runner.pause()

    passed = hw_survivors == expected
    rate_khz = (num_candidates * 1000) / elapsed_us if elapsed_us > 0 else 0

    if passed:
        print(
            f"PASS: 100% agreement over {num_candidates} candidates ({elapsed_us/1000:.1f} ms, {rate_khz:.2f} kHz)."
        )
    else:
        print("FAIL: Discrepancy detected between hardware and expected survivors.")
        for i, (exp, got) in enumerate(zip(expected, hw_survivors)):
            if exp != got:
                print(f"  First mismatch at survivor #{i}: expected {exp}, got {got}")
                break
    return passed


def run_full(runner, configs, max_k=MAX_K):
    """Mode B: Streams survivors at 50 kHz to find representations x^2 + 7y^2 = M."""
    print(f"\n--- Mode B: Full-Speed Sieve Hunt (k = 0 .. {max_k}) ---")
    print(f"Target: M = {M}")
    print(f"Range: y = 4k <= {4 * max_k}")

    runner.configure_array(configs, start_candidate=0)
    solutions = []
    survivors_tested = 0
    t_start = time.ticks_ms()
    last_report = t_start
    total_sieve_us = 0
    total_check_us = 0
    last_k = 0

    def print_stats(header="CURRENT RUN STATS"):
        nonlocal survivors_tested, total_sieve_us, total_check_us, last_k
        t_wall_ms = time.ticks_diff(time.ticks_ms(), t_start)
        t_wall_s = t_wall_ms / 1000.0
        t_sieve_s = total_sieve_us / 1_000_000.0
        t_check_s = total_check_us / 1_000_000.0
        cands = last_k + 1 if last_k > 0 else 1
        obs_rate = (survivors_tested / cands) * 100.0
        theo_rate = (3.0 / 23.0) * 100.0
        avg_check_us = (
            (total_check_us / survivors_tested) if survivors_tested > 0 else 0.0
        )

        print("\n" + "=" * 60)
        print(header)
        print("=" * 60)
        print(
            f"Candidates reached:     {last_k:,} / {max_k:,} ({(last_k / max_k) * 100.0:.2f}%)"
        )
        print(f"Survivors tested:       {survivors_tested:,}")
        print(
            f"Observed survivor rate: {obs_rate:.3f}% ({100.0 - obs_rate:.3f}% rejected)"
        )
        print(f"Theoretical rate:       {theo_rate:.3f}% (3/23 = ~13.04%)")
        print("-" * 60)
        print(f"Wall clock total:       {t_wall_s:.2f} s")
        print(
            f"  PIO / Sieve wait time: {t_sieve_s:.2f} s ({100.0 * t_sieve_s / t_wall_s if t_wall_s > 0 else 0:.1f}%)"
        )
        print(
            f"  CPU Filtering time:    {t_check_s:.2f} s ({100.0 * t_check_s / t_wall_s if t_wall_s > 0 else 0:.1f}%)"
        )
        print(f"Average CPU check cost: {avg_check_us:.2f} us / survivor")
        if avg_check_us > 0:
            proj_total_survivors = round(max_k * (3.0 / 23.0))
            proj_full_check_s = (proj_total_survivors * avg_check_us) / 1_000_000.0
            print("-" * 60)
            print("EXTRAPOLATED WALL CLOCK SPLIT (for all 6,868,058 candidates):")
            print(f"  Hardware scan time (at 50 kHz): 137.4 s")
            print(
                f"  Pico check time ({proj_total_survivors:,} survivors): {proj_full_check_s:.1f} s"
            )
            print(f"  Check / Scan ratio: {proj_full_check_s / 137.4:.2f}x slower")
        print("=" * 60)

    try:
        while True:
            t0_sieve = time.ticks_us()
            k = runner.next_survivor()
            total_sieve_us += time.ticks_diff(time.ticks_us(), t0_sieve)
            last_k = k

            if k > max_k:
                print(f"\nSearch space exhausted at candidate k = {k}.")
                print_stats("SEARCH EXHAUSTED STATS")
                break

            survivors_tested += 1

            t0_check = time.ticks_us()
            y = 4 * k
            diff = M - 7 * y * y
            x, is_sq = check_square(diff)
            total_check_us += time.ticks_diff(time.ticks_us(), t0_check)

            if is_sq:
                t_found = time.ticks_diff(time.ticks_ms(), t_start)
                print(
                    f"\n>>> FOUND REPRESENTATION: M = {x}^2 + 7 * {y}^2 (k = {k}, {t_found/1000:.2f}s) <<<"
                )
                solutions.append((x, y))

                if len(solutions) == 2:
                    # Euler two-squares factorization: gcd(M, x1*y2 + x2*y1)
                    x1, y1 = solutions[0]
                    x2, y2 = solutions[1]
                    cross = x1 * y2 + x2 * y1
                    f1 = gcd(M, cross)
                    f2 = M // f1
                    t_total = time.ticks_diff(time.ticks_ms(), t_start)
                    print("\n" + "=" * 60)
                    print(f"FACTORIZATION COMPLETE in {t_total/1000:.2f}s!")
                    print(f"Factors of {M}:")
                    print(f"  Factor 1: {f1}")
                    print(f"  Factor 2: {f2}")
                    print(f"Verification: {f1} * {f2} == {f1 * f2} ({f1 * f2 == M})")
                    print("=" * 60)
                    print_stats("FINAL TIMING & BENCHMARK SUMMARY")
                    break

            now = time.ticks_ms()
            if time.ticks_diff(now, last_report) >= 2000:
                elapsed_s = time.ticks_diff(now, t_start) / 1000.0
                progress_pct = (k / max_k) * 100.0
                obs_rate = (survivors_tested / (k + 1)) * 100.0
                avg_chk_us = (
                    (total_check_us / survivors_tested) if survivors_tested > 0 else 0
                )
                print(
                    f"  k = {k:,} / {max_k:,} ({progress_pct:.1f}%) | "
                    f"{survivors_tested:,} survivors ({obs_rate:.2f}%) | "
                    f"chk: {avg_chk_us:.1f}us/cand | "
                    f"sieve: {total_sieve_us/1000:.0f}ms, filter: {total_check_us/1000:.0f}ms | {elapsed_s:.1f}s"
                )
                last_report = now

    except KeyboardInterrupt:
        print("\n[Interrupted by user]")
        print_stats("INTERRUPTED RUN TIMING SUMMARY")
    finally:
        runner.pause()


def main():
    runner, configs, oracle_accepts = setup_hardware()

    if RUN_VERIFY:
        ok = verify_sample(runner, configs, oracle_accepts, num_candidates=10000)
        if not ok and RUN_FULL:
            print("Aborting full run due to lint failure.")
            return

    if RUN_FULL:
        run_full(runner, configs, max_k=MAX_K)


if __name__ == "__main__":
    main()

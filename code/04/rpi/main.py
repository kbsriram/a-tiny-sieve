"""CLI test runner for the ATtiny412 flash self-test jig.

Runs the four hardware sanity checks sequentially:
1. Shorts to GND
2. Solder bridges & VCC shorts
3. Open circuits / broken pull-ups
4. JP1 jumper & PA7 cross-talk isolation (3 seconds)

Stops immediately on the first detected failure.
"""

import sys
from checker import JigChecker


def run_card_test():
    """Runs the full test suite on the currently seated card.

    Returns: True if all checks passed, False otherwise.
    """
    checker = JigChecker()
    print("\n" + "=" * 50)
    print(" ATtiny412 Flash-Time Self-Test Jig")
    print("=" * 50)

    checks = [
        ("Check 1: Shorts to GND", checker.check_shorts_to_gnd),
        ("Check 2: Pin Bridges & VCC Shorts", checker.check_bridges_and_vcc),
        ("Check 3: Open Circuits", checker.check_opens),
        (
            "Check 4: JP1 & PA7 Isolation (3.0s)",
            checker.check_jp1_and_pa7_isolation,
        ),
    ]

    for index, (title, func) in enumerate(checks, start=1):
        print(f"[{index}/4] {title} ... ", end="")
        passed, msg = func()
        if passed:
            print("[PASS]")
        else:
            print("[FAIL]")
            print(f"  -> ERROR: {msg}")
            print("\n" + "-" * 50)
            print("RESULT: FAILED. Do NOT flash final image.")
            print("-" * 50 + "\n")
            return False

    print("\n" + "=" * 50)
    print("RESULT: ALL CHECKS PASSED.")
    print("Card is verified. Ready for final shipping image.")
    print("=" * 50 + "\n")
    return True


def batch_mode():
    """Interactive loop for testing a batch of cards sequentially."""
    card_number = 1
    passed_count = 0
    failed_count = 0

    print("Batch test mode activated. Press Ctrl+C at any time to exit.")
    while True:
        try:
            print(f"\nReady for Card #{card_number}.")
            input("Insert card into socket and press ENTER to test... ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting batch mode.")
            break

        passed = run_card_test()
        if passed:
            passed_count += 1
        else:
            failed_count += 1

        print(
            f"Batch stats so far: {passed_count} PASSED, {failed_count} FAILED (Total tested: {card_number})"
        )
        card_number += 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--batch":
        batch_mode()
    else:
        run_card_test()

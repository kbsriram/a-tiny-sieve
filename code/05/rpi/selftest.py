"""Checks the fitted cards before a run.

One open-drain VOTE line carries 30 drivers and has no error detection: a card
stuck low rejects valid candidates, the run finishes, and nothing is reported.
That is indistinguishable from a correct run over a range holding no solution.
These five checks are what tells the two apart.

  1 roll call      every expected address answers, and nothing else does
  2 REQ bridge     the bus scan is the same with REQ high and with REQ low
  3 idle VOTE      with every card disarmed, VOTE stays high over 10 REQ edges
  4 LED walk       each LED lights alone, in slot order, for 200 ms
  5 one-card vote  each card alone steps its own ring correctly

Check 5 gives every slot a different modulus, so two cards swapped between slots
read back different VOTE patterns and the swap shows up.

Run over mpremote with code/05/rpi mounted:
  mpremote connect PORT mount . exec "import selftest; selftest.main(10)"
"""

import time

from bank import Bank, addresses
from panel import Panel
import pins

# One modulus per slot: the 30 primes from 3 to 127, in slot order.
SLOT_MODULI = [
    3, 5, 7, 11, 13, 17, 19, 23, 29, 31,
    37, 41, 43, 47, 53, 59, 61, 67, 71, 73,
    79, 83, 89, 97, 101, 103, 107, 109, 113, 127,
]

LED_ON_MS = 200
IDLE_EDGES = 10


def test_ring(modulus):
    """Phases that release VOTE: those that are squares mod `modulus`.

    Not the factoring ring. It is deterministic, it releases roughly half the
    phases, and it differs between moduli, which is all check 5 needs.
    """
    squares = set()
    for root in range(modulus):
        squares.add((root * root) % modulus)
    return sorted(squares)


def expected_walk(modulus, released, arm_phase, edges):
    """VOTE after each of `edges` REQ rising edges, armed at `arm_phase`."""
    released = set(released)
    return "".join(
        "1" if (arm_phase + step) % modulus in released else "0"
        for step in range(edges)
    )


def _report(name, passed, detail=""):
    print("%s: %s%s" % ("PASS" if passed else "FAIL", name, detail and "\n  " + detail))
    return passed


def check_roll_call(bank):
    """Every expected address answers, and nothing unexpected does."""
    bank.req_low()
    found = bank.scan()
    expected = set(bank.addrs)
    seen = set(found)

    missing = sorted(expected - seen)
    strangers = sorted(seen - expected - {pins.OLED_ADDR})

    detail = "found %s" % [hex(a) for a in found]
    if missing:
        detail += "\n  missing: %s" % [hex(a) for a in missing]
    if strangers:
        detail += "\n  unexpected: %s" % [hex(a) for a in strangers]
    if pins.OLED_ADDR not in seen:
        detail += "\n  no display at 0x%02x" % pins.OLED_ADDR

    return _report("roll call, %d cards" % len(bank.addrs),
                   not missing and not strangers, detail)


def check_req_bridge(bank):
    """The same addresses must answer with REQ high and with REQ low.

    A solder bridge from a card's REQ to SDA or SCL drags the bus when REQ
    changes, so that card, or its neighbours, drop out of one of the two scans.
    """
    bank.req_high()
    high = bank.scan()
    bank.req_low()
    low = bank.scan()

    detail = "REQ high: %s\n  REQ low:  %s" % (
        [hex(a) for a in high],
        [hex(a) for a in low],
    )
    return _report("bus scan unchanged by REQ", high == low, detail)


def check_idle_vote(bank):
    """Every card disarmed, so VOTE must stay released over 10 REQ edges.

    A card whose PA3 is shorted to GND, or which is armed when it should not be,
    reads as a 0 here.
    """
    refused = bank.reset_all()
    if refused:
        return _report("idle VOTE", False,
                       "RESET refused by %s" % [hex(a) for a in refused])

    seen = bank.step(IDLE_EDGES)
    return _report("VOTE high over %d edges, all cards disarmed" % IDLE_EDGES,
                   seen == "1" * IDLE_EDGES, "VOTE %s" % seen)


def check_led_walk(bank, panel):
    """Each LED on for 200 ms, alone, in slot order.

    The Pico can only confirm each card took the command. Whether the light that
    came on is in the right slot is what you watch for.
    """
    bank.reset_all()
    print("  watch the panel: one LED at a time, left to right")

    refused = []
    for addr in bank.addrs:
        slot = bank.slot(addr)
        panel.show("self-test", "", "slot %d of %d" % (slot, len(bank.addrs)),
                   "addr 0x%02x" % addr)
        bank.req_low()
        try:
            if not bank.cards[addr].led(True):
                refused.append(addr)
            time.sleep_ms(LED_ON_MS)
            bank.cards[addr].led(False)
        except OSError:
            refused.append(addr)

    detail = "command refused by %s" % [hex(a) for a in refused] if refused else ""
    return _report("LED walk over %d slots" % len(bank.addrs), not refused, detail)


def check_one_card_vote(bank):
    """Each card alone, armed on its own modulus, stepped over two full wraps.

    Every other card is disarmed, so VOTE carries this card's ring and nothing
    else. A wrong pattern means the card in that slot is not the card the bus
    address says it is, or its ring did not load.
    """
    failures = []
    for addr in bank.addrs:
        slot = bank.slot(addr)
        modulus = SLOT_MODULI[slot - 1]
        released = test_ring(modulus)
        arm_phase = slot % modulus
        edges = 2 * modulus

        bank.reset_all()
        one = bank.cards[addr]
        bank.req_low()
        try:
            if not one.set_ring(modulus, released):
                failures.append("0x%02x SET_RING refused" % addr)
                continue
            if not one.arm(arm_phase):
                failures.append("0x%02x ARM refused" % addr)
                continue
        except OSError as exc:
            failures.append("0x%02x no answer: %s" % (addr, exc))
            continue

        want = expected_walk(modulus, released, arm_phase, edges)
        seen = bank.step(edges)
        if seen == want:
            print("  slot %2d 0x%02x modulus %3d: %s" % (slot, addr, modulus, seen))
        else:
            wrong = [i for i in range(edges) if seen[i] != want[i]]
            failures.append(
                "0x%02x modulus %d: VOTE %s, expected %s, differs at edges %s"
                % (addr, modulus, seen, want, wrong[:8])
            )

    bank.reset_all()
    return _report("one-card vote over %d slots" % len(bank.addrs), not failures,
                   "\n  ".join(failures))


def main(count=10):
    """Runs all five checks over the first `count` slots. True if all passed."""
    bank = Bank(addresses(count))
    panel = Panel(bank.i2c)

    print("\nlog 5 self-test, %d cards, 0x%02x to 0x%02x"
          % (count, bank.addrs[0], bank.addrs[-1]))
    if not panel.present:
        print("no display at 0x%02x; results are on this terminal only"
              % pins.OLED_ADDR)

    checks = [
        ("roll call", lambda: check_roll_call(bank)),
        ("REQ bridge", lambda: check_req_bridge(bank)),
        ("idle VOTE", lambda: check_idle_vote(bank)),
        ("LED walk", lambda: check_led_walk(bank, panel)),
        ("one-card vote", lambda: check_one_card_vote(bank)),
    ]

    results = []
    for index, (name, check) in enumerate(checks, start=1):
        print("\n[%d/%d] %s" % (index, len(checks), name))
        panel.show("self-test", "", "%d/%d %s" % (index, len(checks), name),
                   "%d cards" % count)
        results.append((name, check()))

    passed = [name for name, ok in results if ok]
    failed = [name for name, ok in results if not ok]

    print("\n%d of %d checks passed" % (len(passed), len(results)))
    if failed:
        print("failed: %s" % ", ".join(failed))

    panel.show(
        "self-test done",
        "",
        "%d cards" % count,
        "%d/%d passed" % (len(passed), len(results)),
        "",
        failed[0] if failed else "all checks pass",
    )
    return not failed


if __name__ == "__main__":
    main()

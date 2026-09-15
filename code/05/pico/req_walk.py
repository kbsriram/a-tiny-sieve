"""Boot state, the REQ walk, and RESET while armed, for task 7 of log 5.

MicroPython on a Raspberry Pi Pico, wired as code/04/README.md describes. The
card must be running the task 7 build of code/05/avr/src, which loads no ring
and arms nothing at boot: every ring here is sent over I2C by i2c_card.Card.

Each REQ edge is one loop pass: drive REQ high, wait, read PA3, drive REQ low.
PA3 is open drain with only the ATtiny's internal pull-up, so 1 means the card
released it and 0 means the card is sinking it.

PA7 drives the LED and, while armed, carries the same level as PA3. It is not
read here: it reaches the jig through H1 pin 3 only when JP1 is closed, and JP1
is open on these cards, so the LED checks ask the user to look at it.

CARD and EXPECT are copies of code/05/avr/test/ref/vectors_req.txt, which
model.py writes. Copy them again whenever the ring there changes.
"""

import time

from machine import Pin

import i2c_card
import pins

# (I2C address, modulus, phases that release VOTE, phase to arm at).
CARD = (0x10, 7, [0, 3, 6], 5)

EXPECT = "01100100110010"

# The handler takes 1.6 us from the REQ edge to RETI at CLK_PER 10 MHz, so 50 us
# is two orders of magnitude of margin and still finishes the 14 edges in under
# 2 ms.
SETTLE_US = 50


def walk(edges):
    """Sends `edges` REQ rising edges, returning the VOTE bit read after each."""
    req = Pin(pins.PIN_REQ_PA6, Pin.OUT, value=0)
    vote = Pin(pins.PIN_VOTE_PA3, Pin.IN)

    # REQ starts low, so the first transition below is a rising edge.
    time.sleep_us(SETTLE_US)

    seen = []
    for _ in range(edges):
        req.value(1)
        time.sleep_us(SETTLE_US)
        seen.append(vote.value())
        req.value(0)
        time.sleep_us(SETTLE_US)

    req.value(0)
    return "".join(str(b) for b in seen)


def _compare(name, expect, seen):
    print("expect %s" % expect)
    print("vote   %s" % seen)
    if seen != expect:
        wrong = [i for i in range(len(expect)) if seen[i] != expect[i]]
        print("  VOTE differs at edges %s" % wrong[:16])
    return i2c_card._report(name, seen == expect)


def check_boot_state():
    """VOTE high and the LED dark, before any command since power-on.

    Read before the I2C bus is touched, so nothing the host sends can have
    changed the pins. REQ is left as an input: driving it is what arms nothing
    here, and a card at boot has the PA6 edge disabled anyway.
    """
    vote = Pin(pins.PIN_VOTE_PA3, Pin.IN)
    time.sleep_ms(1)
    ok = i2c_card._report("at boot, before any command: VOTE reads high", vote.value())
    print("  look at the LED now: it must be dark")
    return ok


def load(card):
    """SET_RING then ARM from the CARD tuple. True when both were taken."""
    _, modulus, released, arm_phase = CARD
    ok = card.command(
        i2c_card.OP_SET_RING, bytes([modulus]) + i2c_card.ring_bytes(released)
    )
    ok &= card.command(i2c_card.OP_ARM, bytes([arm_phase]))
    return ok


def check_walk(card):
    """Two full wraps of modulus 7, armed part-way round at phase 5."""
    card.command(i2c_card.OP_RESET)
    if not i2c_card._report("SET_RING and ARM taken", load(card)):
        return False
    return _compare("VOTE over two wraps of modulus 7", EXPECT, walk(len(EXPECT)))


def check_reset_while_armed(card):
    """RESET while armed: phase back to 0, VOTE released, modulus cleared."""
    card.command(i2c_card.OP_RESET)
    ok = load(card)
    walk(3)  # Moves the phase off the one ARM set, so phase 0 is a real change.

    state = card.state()
    ok &= i2c_card._report(
        "armed and stepped: phase is not 0",
        state is not None and state["armed"] and state["phase"] != 0,
    )

    ok &= i2c_card._report("RESET taken while armed", card.command(i2c_card.OP_RESET))
    state = card.state()
    ok &= i2c_card._report(
        "after RESET: disarmed, phase 0, modulus 0",
        state is not None
        and not state["armed"]
        and state["phase"] == 0
        and state["modulus"] == 0,
    )

    vote = Pin(pins.PIN_VOTE_PA3, Pin.IN)
    time.sleep_ms(1)
    ok &= i2c_card._report("after RESET: VOTE released", vote.value())
    return ok


def main():
    ok = check_boot_state()

    i2c = i2c_card.bus()
    print("addresses on the bus: %s" % [hex(x) for x in i2c.scan()])

    card = i2c_card.Card(i2c, CARD[0])
    ok &= check_walk(card)
    ok &= check_reset_while_armed(card)

    card.command(i2c_card.OP_RESET)
    print("PASS" if ok else "FAILED")
    return ok


if __name__ == "__main__":
    main()

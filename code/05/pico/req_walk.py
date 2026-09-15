"""Drives REQ and reads VOTE on one armed card, for task 5 of log 5.

MicroPython on a Raspberry Pi Pico, wired as code/04/README.md describes.
The card must be running the task 5 build of code/05/avr/src, which compiles
in modulus 7 with ring byte 0x49 and arms at phase 0 before enabling
interrupts.

Each edge is one loop pass: drive REQ low, drive it high, wait, read PA3.
PA3 is open drain with only the ATtiny's internal pull-up, so 1 means the card
released it and 0 means the card is sinking it.

PA7 drives the LED and, while armed, carries the same level as PA3. It is not
read here: it reaches the jig through H1 pin 3 only when JP1 is closed, and
JP1 is open on these cards.

EXPECT below is the `expect` line of code/05/avr/test/ref/vectors_req.txt,
which model.py writes. Copy it again whenever the ring in main.c changes.
"""

import time

from machine import Pin

import pins

EXPECT = "100100110010011"

# The handler takes 1.6 us from the REQ edge to RETI at CLK_PER 10 MHz, so
# 50 us is two orders of magnitude of margin and still finishes the 15 edges
# in under 2 ms.
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

    req.init(Pin.IN)
    return "".join(str(b) for b in seen)


def main():
    print("REQ walk: %d edges, modulus 7, ring 0x49" % len(EXPECT))
    seen = walk(len(EXPECT))

    print("expect %s" % EXPECT)
    print("vote   %s" % seen)

    ok = seen == EXPECT
    if not ok:
        wrong = [i for i in range(len(EXPECT)) if seen[i] != EXPECT[i]]
        print("FAIL: VOTE differs at edges %s" % wrong)

    print("PASS" if ok else "FAILED")
    return ok


if __name__ == "__main__":
    main()

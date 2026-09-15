"""Scope stimulus for the VOTE timing measurements.

Every fitted card gets the same ring: modulus 20, VOTE driven low for phases 0
to 9 and released for phases 10 to 19. All of them are armed at phase 0 while
REQ is held low, so they step together from the first edge and switch as one.

REQ is then a hardware PWM square wave, so its period does not depend on how
fast MicroPython runs. At 100 kHz REQ one turn of the ring is 200 us, so VOTE is
a 5 kHz square wave with 10 REQ edges in each half.

Two numbers come off the same trace pair:

  VOTE falling edge   REQ crossing its input-high threshold to VOTE crossing its
                      input-low threshold. This is the interrupt response of the
                      quickest card, since any one card pulls the line down.
  VOTE rising edge    VOTE leaving its driven-low level to crossing 0.7 x VDD.
                      This is the slowest card letting go, plus the line
                      charging. No resistor is fitted: the pull-up is the
                      internal one inside every fitted ATtiny, in parallel.

Nothing here measures anything; the scope reads both intervals off the
backplane REQ and VOTE strips.

Run over mpremote with code/05/rpi mounted:
  mpremote connect PORT mount . exec "import timing; timing.burst(30, 10)"
"""

import time

from machine import PWM, Pin

import pins
from bank import Bank, addresses

MODULUS = 20
RELEASE = list(range(10, MODULUS))  # Phases 10 to 19 release VOTE.
REQ_HZ = 100_000
CHECK_WRAPS = 2  # Turns of the ring stepped by hand before the PWM starts.

# The running PWM. Held here so it is not collected while REQ is wanted.
_pwm = None


def expected(wraps=CHECK_WRAPS):
    """VOTE after each REQ edge over `wraps` turns, armed at phase 0."""
    turn = "".join("1" if phase in RELEASE else "0" for phase in range(MODULUS))
    return turn * wraps


def load(bank):
    """Loads and arms every card. Returns the addresses that did not take it.

    REQ is held low for the whole loop, so no card steps while the rest are
    still being loaded and all of them act on the same first edge.
    """
    bank.req_low()
    refused = []
    for addr in bank.addrs:
        card = bank.cards[addr]
        try:
            taken = card.reset() and card.set_ring(MODULUS, RELEASE) and card.arm(0)
        except OSError:
            taken = False
        if not taken:
            refused.append(addr)
    return refused


def check(bank):
    """Steps REQ by hand over whole turns and compares VOTE against the ring.

    Catches a card that did not load before the scope run starts. Whole turns
    leave the phase back at 0, so the PWM run begins where the arm did.
    """
    want = expected()
    seen = bank.step(len(want))
    if seen == want:
        return True
    print("  VOTE   %s" % seen)
    print("  expect %s" % want)
    return False


def run(count=30, req_hz=REQ_HZ):
    """Loads every card, verifies the ring, then starts REQ. Returns the PWM.

    Pass the PWM back to stop() when the captures are done.
    """
    bank = Bank(addresses(count))

    refused = load(bank)
    if refused:
        print("cards refused the ring: %s" % [hex(a) for a in refused])
        return None
    if not check(bank):
        print("VOTE does not match the ring; not starting REQ")
        return None

    global _pwm
    pwm = PWM(Pin(pins.PIN_REQ))
    _pwm = pwm
    pwm.freq(req_hz)
    pwm.duty_u16(32768)  # 50% duty.

    period_us = 1_000_000 // req_hz
    print("%d cards armed, modulus %d, released for phases %d to %d"
          % (count, MODULUS, RELEASE[0], RELEASE[-1]))
    print("REQ %d Hz, %d us period; VOTE square wave %d Hz"
          % (req_hz, period_us, req_hz // MODULUS))
    print("probe REQ and VOTE on the backplane strips, infinite persistence")
    print("falling edge: REQ input-high threshold to VOTE input-low threshold")
    print("rising edge:  VOTE leaving its low level to 0.7 x VDD")
    return pwm


def stop(pwm=None, count=30):
    """Stops REQ, leaves it low, and resets every card.

    With no argument it stops whatever run() last started.
    """
    global _pwm
    pwm = _pwm if pwm is None else pwm
    _pwm = None
    if pwm is not None:
        pwm.deinit()
    Pin(pins.PIN_REQ, Pin.OUT, value=0)
    time.sleep_ms(1)
    Bank(addresses(count)).reset_all()


def burst(count=30, seconds=10, req_hz=REQ_HZ):
    """Runs REQ for a fixed time, then stops. Needs no input from the terminal."""
    pwm = run(count, req_hz)
    if pwm is None:
        return False
    print("REQ running for %d s" % seconds)
    time.sleep(seconds)
    stop(pwm, count)
    print("REQ stopped, cards reset")
    return True

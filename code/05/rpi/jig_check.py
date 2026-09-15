"""Card checks run on the Pico from the test jig, for code/05/jig/flash_batch.py.

Each stage ends in one sentinel line the PC script parses: `RESULT PASS`, or
`RESULT FAIL <stage> <message>`. Nothing here exits or raises; mpremote's exit
code carries no verdict.

  electrical  The four checks of code/04/README.md, unchanged. They need the
              log 4 diagnostic image on the card: PA6, PA1, PA2 and PA3 are
              inputs with pull-ups and PA7 toggles every 1 s.
  functional  The card answers at its flashed I2C address and steps the ring
              correctly on REQ edges. Needs the log 5 image.
  verify      The same, minus the UPDI reset check, for a card that has been
              powered down since it was flashed.

Run over mpremote with code/05/rpi mounted:
  mpremote connect PORT mount . exec "import jig_check; jig_check.main('electrical')"
"""

import time

from machine import I2C, Pin

import card as card_mod
import jig_pins
from card import Card

# Modulus 7 releasing phases 0, 3 and 6, armed at phase 5. Phases visited are
# 5 6 0 1 2 3 4 5 6 0 1 2 3 4, so VOTE reads:
WALK_MODULUS = 7
WALK_RELEASE = [0, 3, 6]
WALK_ARM_PHASE = 5
WALK_EXPECT = "01100100110010"

# REQ high and low time during the walk. The card's handler takes 1.6 us from
# the edge to RETI, so 50 us leaves the level settled long before it is read.
SETTLE_US = 50


class JigChecker:
    """The four electrical checks, moved from code/04/rpi/checker.py."""

    def __init__(self):
        # Every pin the jig can see on the card.
        self.pin_defs = [
            ("PA6 (H1-2)", jig_pins.PIN_PA6_REQ),
            ("PA7 (H1-3)", jig_pins.PIN_PA7_LED),
            ("PA1 (H1-4)", jig_pins.PIN_PA1_SDA),
            ("PA2 (H1-5)", jig_pins.PIN_PA2_SCL),
            ("PA3 (H1-7)", jig_pins.PIN_PA3_VOTE),
        ]
        # Driven low one at a time during the bridge check. PA7 is left out: it
        # is a push-pull output on the diagnostic image.
        self.drive_pins = [
            ("PA6 (H1-2)", jig_pins.PIN_PA6_REQ),
            ("PA1 (H1-4)", jig_pins.PIN_PA1_SDA),
            ("PA2 (H1-5)", jig_pins.PIN_PA2_SCL),
            ("PA3 (H1-7)", jig_pins.PIN_PA3_VOTE),
        ]
        self.pins = {}

    def _setup_idle_state(self):
        """All monitored pins floating, on the card's own pull-ups. PA7 gets the
        Pico's pull-up: JP1 is open, so nothing else holds H1 pin 3."""
        for name, gpio in self.pin_defs:
            if gpio == jig_pins.PIN_PA7_LED:
                self.pins[name] = Pin(gpio, Pin.IN, Pin.PULL_UP)
            else:
                self.pins[name] = Pin(gpio, Pin.IN)
        time.sleep_ms(2)

    def check_shorts_to_gnd(self):
        """Check 1: all five pins read high. Catches shorts to GND and a card
        that is not powered."""
        self._setup_idle_state()
        failed = [name for name, _ in self.pin_defs if self.pins[name].value() != 1]
        if failed:
            return False, "short to GND or unpowered on: %s" % ", ".join(failed)
        return True, "all five pins read high"

    def check_bridges_and_vcc(self):
        """Check 2: drive each line low in turn. The driven pin must read low,
        and every other pin must stay high."""
        self._setup_idle_state()

        for d_name, d_gpio in self.drive_pins:
            driven = Pin(d_gpio, Pin.OUT)
            driven.value(0)
            time.sleep_ms(1)

            if driven.value() != 0:
                self._setup_idle_state()
                return False, "%s would not pull low: shorted to VCC" % d_name

            bridges = [
                name
                for name, gpio in self.pin_defs
                if gpio != d_gpio and self.pins[name].value() != 1
            ]
            self._setup_idle_state()

            if bridges:
                return False, "bridge: driving %s pulled down %s" % (
                    d_name,
                    ", ".join(bridges),
                )

        return True, "no pin bridges and no shorts to VCC"

    def check_opens(self):
        """Check 3: release every line; all five must read high again. Catches
        an open circuit, a bad socket contact or a missing pull-up."""
        self._setup_idle_state()
        time.sleep_ms(2)
        failed = [name for name, _ in self.pin_defs if self.pins[name].value() != 1]
        if failed:
            return False, "open circuit or missing pull-up on: %s" % ", ".join(failed)
        return True, "all five pins read high after release"

    def check_jp1_and_pa7_isolation(self, duration_s=3.0, sample_interval_ms=50):
        """Check 4: hold H1 pin 3 down with the Pico's pull-down and watch every
        pin for 3 s. H1 pin 3 toggling means JP1 is closed; any other pin
        toggling means a solder bridge to PA7, which is the only line moving."""
        for name, gpio in self.pin_defs:
            if gpio == jig_pins.PIN_PA7_LED:
                self.pins[name] = Pin(gpio, Pin.IN, Pin.PULL_DOWN)
            else:
                self.pins[name] = Pin(gpio, Pin.IN)
        time.sleep_ms(5)

        samples = int((duration_s * 1000) // sample_interval_ms)
        last = {name: self.pins[name].value() for name, _ in self.pin_defs}
        toggles = {name: 0 for name, _ in self.pin_defs}
        highs = {name: 0 for name, _ in self.pin_defs}

        for _ in range(samples):
            time.sleep_ms(sample_interval_ms)
            for name, _ in self.pin_defs:
                value = self.pins[name].value()
                highs[name] += value
                if value != last[name]:
                    toggles[name] += 1
                    last[name] = value

        self._setup_idle_state()

        pa7 = "PA7 (H1-3)"
        if toggles[pa7] > 0:
            return False, "JP1 is closed: H1 pin 3 toggled %d times with PA7" % (
                toggles[pa7]
            )
        if highs[pa7] == samples:
            return False, "H1 pin 3 stuck high: shorted to VCC or to a high line"

        bridged = [
            "%s (%d toggles)" % (name, toggles[name])
            for name, _ in self.drive_pins
            if toggles[name] > 0
        ]
        if bridged:
            return False, "bridge to PA7 on: %s" % ", ".join(bridged)

        return True, "JP1 open, PA7 isolated from every other pin"


def electrical():
    """The four checks in order. Stops at the first failure."""
    checker = JigChecker()
    checks = [
        ("shorts to GND", checker.check_shorts_to_gnd),
        ("bridges and VCC shorts", checker.check_bridges_and_vcc),
        ("open circuits", checker.check_opens),
        ("JP1 and PA7 isolation", checker.check_jp1_and_pa7_isolation),
    ]
    for index, (title, check) in enumerate(checks, start=1):
        print("[%d/%d] %s ... " % (index, len(checks), title), end="")
        passed, message = check()
        print("pass" if passed else "FAIL")
        if not passed:
            return False, "%s: %s" % (title, message)
        print("      %s" % message)
    return True, "four electrical checks passed"


def _bus():
    """The I2C bus, with REQ held low so no read lands on a REQ edge."""
    Pin(jig_pins.PIN_PA6_REQ, Pin.OUT, value=0)
    return I2C(
        jig_pins.I2C_ID,
        sda=Pin(jig_pins.PIN_PA1_SDA),
        scl=Pin(jig_pins.PIN_PA2_SCL),
        freq=jig_pins.I2C_HZ,
    )


def walk(edges):
    """Sends `edges` REQ rising edges, returning the VOTE bit read after each.

    VOTE is open drain: 1 means the card released it, 0 means it is sinking.
    """
    req = Pin(jig_pins.PIN_PA6_REQ, Pin.OUT, value=0)
    vote = Pin(jig_pins.PIN_PA3_VOTE, Pin.IN)
    time.sleep_us(SETTLE_US)  # REQ starts low, so the first change is a rise.

    seen = []
    for _ in range(edges):
        req.value(1)
        time.sleep_us(SETTLE_US)
        seen.append(vote.value())
        req.value(0)
        time.sleep_us(SETTLE_US)

    req.value(0)
    return "".join(str(bit) for bit in seen)


def functional(addr, expect_updi=True):
    """The card answers at `addr` and steps its ring on REQ edges.

    `expect_updi` requires the boot-time RSTFR snapshot to name a UPDI reset,
    which holds only until the card next loses power. A card taken out of the
    sieve reads a power-on reset instead, so the verify stage clears it.
    """
    # Before any I2C: a disarmed card leaves VOTE to its internal pull-up.
    vote = Pin(jig_pins.PIN_PA3_VOTE, Pin.IN)
    time.sleep_ms(1)
    if vote.value() != 1:
        return False, "VOTE reads low at boot"
    print("      VOTE high at boot")

    i2c = _bus()
    found = i2c.scan()
    if found != [addr]:
        return False, "bus scan found %s, expected [0x%02x]" % (
            [hex(a) for a in found],
            addr,
        )
    print("      answers at 0x%02x and nowhere else" % addr)

    the_card = Card(i2c, addr)
    state = the_card.state()
    if state is None:
        return False, "STATUS did not read back, or its CRC did not match"
    if state["version"] != card_mod.FW_VERSION:
        return False, "firmware version %d, expected %d" % (
            state["version"],
            card_mod.FW_VERSION,
        )
    if state["modulus"] != 0 or state["phase"] != 0 or state["armed"]:
        return False, "boot state wrong: modulus %d, phase %d, armed %s" % (
            state["modulus"],
            state["phase"],
            state["armed"],
        )
    if state["rstfr"] & card_mod.RSTFR_BORF:
        return False, "brown-out reset flagged: RSTFR 0x%02x" % state["rstfr"]
    if expect_updi and not state["rstfr"] & card_mod.RSTFR_UPDIRF:
        return False, "no UPDI reset flagged after flashing: RSTFR 0x%02x" % (
            state["rstfr"]
        )
    print("      version %d, disarmed, RSTFR 0x%02x" % (state["version"], state["rstfr"]))

    if not the_card.set_ring(WALK_MODULUS, WALK_RELEASE):
        return False, "SET_RING refused"
    if not the_card.arm(WALK_ARM_PHASE):
        return False, "ARM refused"

    seen = walk(len(WALK_EXPECT))
    if seen != WALK_EXPECT:
        return False, "VOTE read %s over %d REQ edges, expected %s" % (
            seen,
            len(WALK_EXPECT),
            WALK_EXPECT,
        )
    print("      VOTE %s over %d REQ edges" % (seen, len(WALK_EXPECT)))

    if not the_card.reset():
        return False, "RESET refused after the walk"
    return True, "answers at 0x%02x and steps modulus %d correctly" % (
        addr,
        WALK_MODULUS,
    )


def main(stage, addr=None):
    """Runs one stage and prints the sentinel line flash_batch.py reads.

    Returns rather than raising SystemExit, and catches everything: an exception
    leaving the raw REPL soft-resets the board, which clears the globals
    `mpremote mount` needs to unmount /remote afterwards.
    """
    try:
        if stage == "electrical":
            passed, message = electrical()
        elif stage == "functional":
            passed, message = functional(addr)
        elif stage == "verify":
            passed, message = functional(addr, expect_updi=False)
        else:
            passed, message = False, "unknown stage"
    except Exception as exc:  # A card that does not answer raises OSError.
        passed, message = False, "%s: %s" % (type(exc).__name__, exc)

    print("RESULT PASS" if passed else "RESULT FAIL %s %s" % (stage, message))

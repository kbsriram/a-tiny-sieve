#!/usr/bin/env python3
"""Tests, flashes and addresses ATtiny412 cards one at a time on the jig.

Per card: build both images from source, flash the log 4 diagnostic image, run
the four electrical checks on the Pico, flash the log 5 image built for the next
free I2C address, then check over I2C that the card answers there and steps its
ring. A card that fails any step does not consume an address.

Both builds happen before the card is touched, so a broken toolchain or a source
error stops the run rather than leaving a half-programmed card in the socket.

Jig wiring: code/04/README.md.

  python3 flash_batch.py                  # batch loop over 30 addresses
  python3 flash_batch.py --addr 0x17      # one card at a fixed address
  python3 flash_batch.py --verify 0x17    # functional check only, no flashing

--verify skips the UPDI reset check: a card that has been powered down since it
was flashed reports a power-on reset instead.
"""

import argparse
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
CODE = HERE.parent.parent  # public/code
DIAG_SRC = CODE / "04" / "avr" / "src"  # Diagnostic image: PA7 toggles at 1 s.
CARD_SRC = CODE / "05" / "avr" / "src"  # Shipping image, one build per address.
RPI_DIR = CODE / "05" / "rpi"

sys.path.insert(0, str(RPI_DIR))
from card import ADDR_FIRST, ADDR_LAST  # noqa: E402  Pure Python, no machine module.

TOTAL_CARDS = ADDR_LAST - ADDR_FIRST + 1

MCU = "attiny412"
UPDI_BAUD = "115200"
SENTINEL = "RESULT "


def _run(cmd, cwd=None):
    """Runs a command, echoing its output. Returns True on exit code 0."""
    print("  $ %s" % " ".join(str(part) for part in cmd))
    done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    output = done.stdout + done.stderr
    if output.strip():
        print("".join("    %s\n" % line for line in output.splitlines()), end="")
    return done.returncode == 0, output


def build(src, extra=()):
    """`make clean all` in one AVR source tree. Aborts the run if it fails.

    A clean build every time: nothing downstream has to reason about whether a
    stale object file matches the source the card is about to be given.
    """
    ok, _ = _run(["make", "-C", str(src), "clean", "all"] + list(extra))
    if not ok:
        raise SystemExit("build failed in %s" % src)


def flash(flash_hex, fuse_hex, updi):
    """Writes flash and fuses over UPDI. False if avrdude reports a failure."""
    ok, _ = _run(
        [
            "avrdude",
            "-c", "serialupdi",
            "-p", MCU,
            "-P", updi,
            "-b", UPDI_BAUD,
            "-U", "flash:w:%s:i" % flash_hex,
            "-U", "fuses:w:%s:i" % fuse_hex,
        ]
    )
    return ok


def run_check(stage, serial, addr=None):
    """Runs one jig_check stage on the Pico. Returns (passed, message).

    The sentinel line is the only verdict: jig_check never exits or raises, so
    mpremote's exit code says nothing about the card. A stage that printed no
    sentinel counts as a failure.
    """
    call = "import jig_check; jig_check.main(%r%s)" % (
        stage,
        "" if addr is None else ", 0x%02x" % addr,
    )
    _, output = _run(
        ["mpremote", "connect", serial, "mount", str(RPI_DIR), "exec", call]
    )

    for line in reversed(output.splitlines()):
        line = line.strip()
        if line.startswith(SENTINEL):
            verdict = line[len(SENTINEL):]
            if verdict == "PASS":
                return True, "passed"
            return False, verdict[len("FAIL "):] if verdict.startswith("FAIL ") else verdict
    return False, "no RESULT line from the Pico; check --serial and the mount"


def card_cycle(addr, args):
    """Build both images, then diagnostic flash, electrical checks, card flash,
    functional check. ADDR is a compile-time define, so the card image is built
    for this address alone.

    The two source trees are separate directories, so both main.hex files exist
    at once and neither build overwrites the other.
    """
    print("\n-- building the diagnostic image")
    build(DIAG_SRC)
    print("-- building the card image for 0x%02x" % addr)
    build(CARD_SRC, ["ADDR=0x%02x" % addr])

    print("-- flashing the diagnostic image")
    if not flash(DIAG_SRC / "main.hex", DIAG_SRC / "fuses.hex", args.updi):
        return False, "avrdude could not write the diagnostic image"

    print("-- electrical checks")
    passed, message = run_check("electrical", args.serial)
    if not passed:
        return False, message

    print("-- flashing the card image for 0x%02x" % addr)
    if not flash(CARD_SRC / "main.hex", CARD_SRC / "fuses.hex", args.updi):
        return False, "avrdude could not write the card image"

    print("-- functional check at 0x%02x" % addr)
    return run_check("functional", args.serial, addr)


def report(passed, addr, message):
    """One line per finished card: the slot to put it in, or why it failed."""
    if passed:
        slot = addr - ADDR_FIRST + 1
        print(
            "\ncard %d of %d flashed at 0x%02x - insert in slot %d"
            % (slot, TOTAL_CARDS, addr, slot)
        )
    else:
        print("\nFAILED: %s" % message)
        print("address 0x%02x is still free; set it aside and try the next card" % addr)


def batch(args):
    """Loops until every address is used or the user stops."""
    addr = args.start
    while addr <= ADDR_LAST:
        try:
            input(
                "\ninsert the card for 0x%02x (slot %d of %d) and press Enter, "
                "or Ctrl+C to stop: " % (addr, addr - ADDR_FIRST + 1, TOTAL_CARDS)
            )
        except (EOFError, KeyboardInterrupt):
            print("\nstopped at 0x%02x; resume with --start 0x%02x" % (addr, addr))
            return 0

        passed, message = card_cycle(addr, args)
        report(passed, addr, message)
        if passed:
            addr += 1

    print("\nall %d addresses used, 0x%02x to 0x%02x" % (TOTAL_CARDS, ADDR_FIRST, ADDR_LAST))
    return 0


def hex_addr(text):
    value = int(text, 0)
    if not ADDR_FIRST <= value <= ADDR_LAST:
        raise argparse.ArgumentTypeError(
            "address must be 0x%02x to 0x%02x" % (ADDR_FIRST, ADDR_LAST)
        )
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=hex_addr, default=ADDR_FIRST,
                        help="first address of the batch")
    parser.add_argument("--addr", type=hex_addr, help="test and flash one card here")
    parser.add_argument("--verify", type=hex_addr,
                        help="functional check on an already flashed card")
    parser.add_argument("--updi", default="/dev/ttyUSB0",
                        help="serial port of the UPDI adapter on H1 pin 6")
    parser.add_argument("--serial", default="/dev/ttyACM0", help="serial port of the Pico")
    args = parser.parse_args()

    if args.verify is not None:
        passed, message = run_check("verify", args.serial, args.verify)
        print("\n0x%02x: %s" % (args.verify, "PASS" if passed else "FAIL - " + message))
        return 0 if passed else 1

    if args.addr is not None:
        passed, message = card_cycle(args.addr, args)
        report(passed, args.addr, message)
        return 0 if passed else 1

    return batch(args)


if __name__ == "__main__":
    sys.exit(main())

# 02 — sieving versus checking

Log: [Sieving versus checking](https://hackaday.io/project/206556-a-tiny-sieve-lehmers-math-machine-in-attinys/log/250562-sieving-versus-checking)

Factors 5,283,065,753,709,209 by searching for `a^2 + 7*(4k)^2 = N`. Three
ATtiny412s reject candidate values of `k`; a Pico steps them and tests what
survives for a perfect square.

## Signals

- **REQ** — Pico output (GP14) to every ATtiny (PA6). Each rising edge makes
  every chip read one bit of its ring and advance its counter by one.
- **VOTE** — one wire shared by all three chips (PA7) and read by the Pico
  (GP15). A chip that rejects drives it low; a chip that accepts leaves the pin
  as a high-impedance input. So VOTE is high only if no chip rejected.
- **I2C** — Pico (GP16 SDA, GP17 SCL) to each chip (PA1, PA2), used before the
  run to load each chip's modulus and ring.

A chip's *ring* is its modulus `p` plus 16 bytes = 128 bits, one bit per
residue: bit `r` is 1 if `N - 7*(4r)^2` is a quadratic residue mod `p`, meaning
candidates with `k = r mod p` can still be solutions. 128 bits caps the modulus
at 128.

## ATtiny412 firmware — `avr/`

`src/task/task_sieve.c` is the whole rejecter: modulus, ring, phase counter, and
three I2C commands — `0x01` set ring, `0x02` reset and disarm, `0x03` arm.
`src/hal/hal_gpio.c` does the open-drain VOTE with `PORTA.DIRSET`/`DIRCLR`.
`main.c` never sleeps while armed, because waking from sleep costs microseconds
that would push the REQ-to-VOTE delay past the 20 us step period.

Build and flash over serial UPDI, once per chip with a distinct I2C address:

    cd avr/src
    make ADDR=0x20 flash
    make ADDR=0x21 flash
    make ADDR=0x22 flash

Set `BASE` and `PORT` in `src/Makefile` for your toolchain and UPDI adapter.
Host-side unit tests of `task_sieve.c` (no hardware needed): `cd avr/test/host
&& make test`.

## Pico host — `rpi/` (MicroPython)

`sieve_runner.py` holds the PIO program: it drives REQ at 50 kHz (10 us high,
10 us low), samples VOTE near the end of the low phase, and pushes a 64-bit
candidate index into the FIFO only when VOTE was high. `sieve.py` is the I2C
driver for one chip. `check_16.py` builds the rings from quadratic residues,
verifies the first 10,000 candidates against a Python oracle, then runs to
completion and recovers the factors with `gcd`.

Run anything with the directory mounted, no copying to flash:

    cd rpi
    mpremote mount . run check_16.py

## Tests

All four need the hardware attached, and are run the same way.

- `test_functional.py` — one chip, degenerate rings (all-accept, all-reject,
  alternating, single bit); the other chips left disarmed.
- `test_survivors.py` — arms 1, then 2, then 3 chips and re-checks survivors,
  confirming disarmed chips never pull VOTE low.
- `test_differential.py` — random rings across moduli up to 127, checking the
  ring wraps correctly at byte boundaries.
- `test_overflow.py` — the PIO's 64-bit candidate counter across 0xFFFFFFFF.

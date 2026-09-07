# A tiny sieve

Code for [A Tiny Sieve: Lehmer's math machine in ATtinys](https://hackaday.io/project/206556-a-tiny-sieve-lehmers-math-machine-in-attinys).

A number sieve rejects candidate integers that cannot solve a quadratic
equation, using arithmetic modulo small primes. One ATtiny412 holds one
modulus. They share one open-drain line: any chip that rejects pulls it low, so
the line stays high only when no chip rejected. A Raspberry Pi Pico clocks them
and checks whatever survives.

One directory per build log, each with its own README:

- [code/01](code/01) — [The sound of sieving](https://hackaday.io/project/206556-a-tiny-sieve-lehmers-math-machine-in-attinys/log/250443-the-sound-of-sieving).
  Three moduli hardcoded, stepped by a button, a buzzer on the shared line.
  Solves `y^2 - 2x^2 = 4001`.
- [code/02](code/02) — [Sieving versus checking](https://hackaday.io/project/206556-a-tiny-sieve-lehmers-math-machine-in-attinys/log/250562-sieving-versus-checking).
  Rings loaded over I2C, clocked at 50 kHz by the Pico's PIO, survivors tested
  on the Pico. Factors 5,283,065,753,709,209.

Every build has an `avr/` half (ATtiny412 firmware in C, avr-gcc) and an `rpi/`
half (Pico host code). The Pico runtime differs per build — build 01 is
CircuitPython, build 02 is MicroPython — so check the build's README before
copying files to a board.

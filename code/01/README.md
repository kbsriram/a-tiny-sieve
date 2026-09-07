# 01 — the sound of sieving

Log: [The sound of sieving](https://hackaday.io/project/206556-a-tiny-sieve-lehmers-math-machine-in-attinys/log/250443-the-sound-of-sieving)

Sieves `y^2 - 2x^2 = 4001`. Three ATtiny412s each hold one modulus, a push
button steps all of them together, and a piezo buzzer sounds on every rejection.

## Wiring

One switch goes to PA1 on every chip, with the internal pull-up on and the other
side to ground, so a press advances every chip's counter by one. PA2 on every
chip is tied to one line, pulled high, with the buzzer across it: a chip that
rejects drives its pin to 0V for about 62 ms, a chip that accepts leaves the pin
as a high-impedance input.

## ATtiny412 firmware — `avr/`

`src/task/task_check.c` holds the accept/reject pattern as a `bool` array, one
entry per residue. Patterns for mod 3, 5, 7 and 11 are all in the file, with one
active and the rest commented out, so you edit and reflash per chip.
`src/task/task_button.c` debounces the press over 3 ticks of the 15.625 ms RTC;
`src/task/task_beep.c` holds the buzzer down for 4 ticks; `src/hal/hal_gpio.c`
drives PA2 with `PORTA.DIRSET`/`DIRCLR`.

    cd avr/src
    make flash            # serial UPDI; set BASE and PORT in the Makefile
    cd ../test/host && make test   # task unit tests, no hardware needed

## Pico — `rpi/` (CircuitPython)

Counts and displays how many candidates have been stepped through. Copy
`code.py` and `lib/` to the CIRCUITPY drive. `lib/button.py` debounces the
switch with a 47 ms settle window; `lib/count_display.py` drives a 128x64
SSD1306 OLED over I2C.

`diag.py` prints how long the switch stayed at each level. Copy it over
`code.py` to measure the contact bounce that made the count jump by more than
one per press.

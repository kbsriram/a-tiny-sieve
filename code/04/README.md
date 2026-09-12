# Card test jig

Tests one ATtiny412 modulus card before it gets the shipping firmware.
Card schematic: [hardware/modulus](../../hardware/modulus).

`test_and_flash.sh` flashes a diagnostic image over UPDI (a UPDI
Friend on H1 pin 6, PA0), then runs the Pico checks. `PORT=` sets the UPDI
serial port; `--batch` loops over a tray of cards.

Diagnostic image: PA6, PA1, PA2, PA3 are inputs with pull-ups; PA7 is a
push-pull output toggling every 1 s.

Checks, in order:

1. All five pins read high. Finds shorts to GND.
2. Drive each of PA6, PA1, PA2, PA3 low in turn; the rest stay high.
   Finds bridges. A pin that will not read low is shorted to VCC.
3. Release all; all read high. Finds opens.
4. Hold pin 3 low for 3 s; no pin follows PA7. Finds a closed JP1
   and any bridge to PA7.

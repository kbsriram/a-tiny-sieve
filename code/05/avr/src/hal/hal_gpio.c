#include "hal_gpio.h"

#include <avr/io.h>

void hal_gpio_init(void) {
  // PA0 is UPDI programming pin; do not touch.
  // PA1, PA2, PA3, PA6: Inputs with pull-ups enabled.
  PORTA.DIRCLR = PIN1_bm | PIN2_bm | PIN3_bm | PIN6_bm;
  PORTA.PIN1CTRL = PORT_PULLUPEN_bm;
  PORTA.PIN2CTRL = PORT_PULLUPEN_bm;
  PORTA.PIN3CTRL = PORT_PULLUPEN_bm;
  PORTA.PIN6CTRL = PORT_PULLUPEN_bm;

  // PA7: Push-pull output, initially low.
  PORTA.DIRSET = PIN7_bm;
  PORTA.OUTCLR = PIN7_bm;
}

void hal_gpio_toggle_pa7(void) { PORTA.OUTTGL = PIN7_bm; }

#include "hal_gpio.h"

#include <avr/io.h>

void hal_gpio_init(void) {
  // Park unused pins to save power.
  // Protect PA0 which is UPDI.
  PORTA.PIN1CTRL = PORT_ISC_INPUT_DISABLE_gc;
  PORTA.PIN2CTRL = PORT_ISC_INPUT_DISABLE_gc;
  // PA3 is LED output
  PORTA.DIRSET = PIN3_bm;
  PORTA.PIN6CTRL = PORT_ISC_INPUT_DISABLE_gc;
  PORTA.PIN7CTRL = PORT_ISC_INPUT_DISABLE_gc;
}

void hal_gpio_led_toggle(void) {
  PORTA.OUTTGL = PIN3_bm;
}

#include "hal_gpio.h"

#include <avr/interrupt.h>
#include <avr/io.h>

#include "flags.h"

void hal_gpio_init(void) {
  PORTA.PIN2CTRL = PORT_ISC_INPUT_DISABLE_gc;
  PORTA.PIN3CTRL = PORT_ISC_INPUT_DISABLE_gc;
  PORTA.PIN6CTRL = PORT_ISC_INPUT_DISABLE_gc;
  PORTA.PIN7CTRL = PORT_ISC_INPUT_DISABLE_gc;

  PORTA.DIRCLR = PIN1_bm;
  PORTA.PIN1CTRL = PORT_PULLUPEN_bm | PORT_ISC_BOTHEDGES_gc;
}

bool hal_gpio_read_button(void) { return (PORTA.IN & PIN1_bm) == 0; }

ISR(PORTA_PORT_vect) {
  PORTA.INTFLAGS = PIN1_bm;
  sys_flags.btn_edge = true;
}

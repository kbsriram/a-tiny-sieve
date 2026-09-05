#include "hal_gpio.h"

#include <avr/interrupt.h>
#include <avr/io.h>

static volatile bool req_event = false;

void hal_gpio_init(void) {
  // Park unused pins to save power.
  // Protect PA0 which is UPDI.
  // PA1 and PA2 are used for I2C (SDA, SCL), do not disable their inputs.
  // PA3 is LED output
  PORTA.DIRSET = PIN3_bm;
  PORTA.OUTCLR = PIN3_bm;

  // PA6 is REQ input with rising-edge interrupt and pull-up enabled
  PORTA.DIRCLR = PIN6_bm;
  PORTA.PIN6CTRL = PORT_ISC_RISING_gc | PORT_PULLUPEN_bm;

  // PA7 is VOTE open-drain (input for released, output-low for veto)
  PORTA.DIRCLR = PIN7_bm;
  PORTA.OUTCLR = PIN7_bm;
}



void hal_gpio_set_veto(bool veto) {
  if (veto) {
    // Veto: drive VOTE low (output mode), turn LED on
    PORTA.DIRSET = PIN7_bm;
    PORTA.OUTSET = PIN3_bm;
  } else {
    // Release: VOTE high-Z (input mode), turn LED off
    PORTA.DIRCLR = PIN7_bm;
    PORTA.OUTCLR = PIN3_bm;
  }
}

bool hal_gpio_req_take_event(void) {
  if (req_event) {
    req_event = false;
    return true;
  }
  return false;
}

ISR(PORTA_PORT_vect) {
  if (PORTA.INTFLAGS & PIN6_bm) {
    req_event = true;
    PORTA.INTFLAGS = PIN6_bm;
  }
}

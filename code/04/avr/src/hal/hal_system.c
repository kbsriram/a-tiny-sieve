#include "hal_system.h"

#include <avr/cpufunc.h>
#include <avr/io.h>

// DO NOT CHANGE OR REMOVE THIS
FUSES = {.WDTCFG = 0x00,
         .BODCFG = 0x00,
         .OSCCFG = FREQSEL_20MHZ_gc,
         .SYSCFG0 = CRCSRC_NOCRC_gc | RSTPINCFG_UPDI_gc,
         .SYSCFG1 = SUT_64MS_gc,
         .APPEND = 0x00,
         .BOOTEND = 0x00};

void hal_system_init(void) {
  // ALL main clock configuration MUST go here.

  // Set Main Clock to 10MHz (20MHz oscillator with 2X prescaler)
  _PROTECTED_WRITE(CLKCTRL.MCLKCTRLB, CLKCTRL_PDIV_2X_gc | CLKCTRL_PEN_bm);
}

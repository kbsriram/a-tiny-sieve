#include "hal_system.h"

#include <avr/cpufunc.h>
#include <avr/io.h>

// DO NOT CHANGE OR REMOVE.
// BOD at 2.6 V, continuous in Active/Idle. OSCLOCK clear per errata DS80000933D
// (setting it blocks calibration load).
FUSES = {.WDTCFG = 0x00,
         .BODCFG = LVL_BODLEVEL2_gc | ACTIVE_ENABLED_gc | SLEEP_DIS_gc,
         .OSCCFG = FREQSEL_20MHZ_gc,
         .SYSCFG0 = CRCSRC_NOCRC_gc | RSTPINCFG_UPDI_gc,
         .SYSCFG1 = SUT_64MS_gc,
         .APPEND = 0x00,
         .BOOTEND = 0x00};

static uint8_t reset_flags;

void hal_system_init(void) {
  // RSTFR flags are sticky; clear them now or they persist to the next reset.
  reset_flags = RSTCTRL.RSTFR;
  RSTCTRL.RSTFR = reset_flags;

  // Errata DS80000933D: a store to an address >= 64 (RSTFR, 0x40) immediately
  // followed by one below 64 (CPU.CCP, 0x34) loses the second.
  _NOP();

  // MCLKCTRLB needs CCP IOREG key. OSC20M / PDIV_2X = 10 MHz CLK_PER.
  _PROTECTED_WRITE(CLKCTRL.MCLKCTRLB, CLKCTRL_PDIV_2X_gc | CLKCTRL_PEN_bm);
}

uint8_t hal_system_reset_flags(void) { return reset_flags; }

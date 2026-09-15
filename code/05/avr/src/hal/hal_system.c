#include "hal_system.h"

#include <avr/cpufunc.h>
#include <avr/io.h>

// DO NOT CHANGE OR REMOVE THIS
// Datasheet ch04: BODCFG is LVL[7:5], SAMPFREQ[4], ACTIVE[3:2], SLEEP[1:0].
// BOD runs continuously in Active and Idle at 2.6 V, off in Standby/Power-Down.
// OSCCFG.OSCLOCK stays clear: errata DS80000933D, it blocks calibration load.
FUSES = {.WDTCFG = 0x00,
         .BODCFG = LVL_BODLEVEL2_gc | ACTIVE_ENABLED_gc | SLEEP_DIS_gc,
         .OSCCFG = FREQSEL_20MHZ_gc,
         .SYSCFG0 = CRCSRC_NOCRC_gc | RSTPINCFG_UPDI_gc,
         .SYSCFG1 = SUT_64MS_gc,
         .APPEND = 0x00,
         .BOOTEND = 0x00};

static uint8_t reset_flags;

void hal_system_init(void) {
  // Datasheet ch10: RSTFR flags stay set until a 1 is written back, so an
  // uncleared flag would be blamed on the next reset.
  reset_flags = RSTCTRL.RSTFR;
  RSTCTRL.RSTFR = reset_flags;

  // Errata DS80000933D: a store to an address >= 64 immediately followed by a
  // store below 64 loses the second store. RSTFR is at 0x40, CPU.CCP at 0x34.
  _NOP();

  // ALL main clock configuration MUST go here.
  // Datasheet ch08: MCLKCTRLB needs the CCP IOREG key. OSC20M is 20 MHz from
  // FUSE.OSCCFG; PDIV_2X with PEN set makes CLK_PER 10 MHz.
  _PROTECTED_WRITE(CLKCTRL.MCLKCTRLB, CLKCTRL_PDIV_2X_gc | CLKCTRL_PEN_bm);
}

// cppcheck-suppress unusedFunction  ; used from hal_twi.c in task 6.
uint8_t hal_system_reset_flags(void) { return reset_flags; }

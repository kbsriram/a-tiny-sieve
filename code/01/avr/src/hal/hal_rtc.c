#include "hal_rtc.h"

#include <avr/interrupt.h>
#include <avr/io.h>

#include "flags.h"

void hal_rtc_init(void) {
  RTC.CLKSEL = RTC_CLKSEL_INT32K_gc;
  while (RTC.PITSTATUS > 0) {
  }
  RTC.PITINTCTRL = RTC_PI_bm;
  RTC.PITCTRLA = RTC_PERIOD_CYC512_gc | RTC_PITEN_bm;
}

ISR(RTC_PIT_vect) {
  RTC.PITINTFLAGS = RTC_PI_bm;
  sys_flags.rtc_tick = true;
}

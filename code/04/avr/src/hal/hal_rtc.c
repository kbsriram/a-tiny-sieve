#include "hal_rtc.h"

#include <avr/interrupt.h>
#include <avr/io.h>
#include <stdint.h>

static volatile uint8_t rtc_tick_flag = 0;

void hal_rtc_init(void) {
  // Use internal 1.024 kHz oscillator for 1-second PIT interval
  RTC.CLKSEL = RTC_CLKSEL_INT1K_gc;
  RTC.PITINTCTRL = RTC_PI_bm;
  RTC.PITCTRLA = RTC_PERIOD_CYC1024_gc | RTC_PITEN_bm;
}

// cppcheck-suppress unusedFunction
ISR(RTC_PIT_vect) {
  RTC.PITINTFLAGS = RTC_PI_bm;
  rtc_tick_flag = 1;
}

bool hal_rtc_take_tick_event(void) {
  if (rtc_tick_flag) {
    rtc_tick_flag = 0;
    return true;
  }
  return false;
}

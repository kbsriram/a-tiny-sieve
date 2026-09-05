#include "hal_rtc.h"

#include <avr/interrupt.h>
#include <avr/io.h>
#include <stdint.h>

static volatile uint8_t rtc_tick_flag = 0;

void hal_rtc_init(void) {
  // 1kHz clock source for lower power, ~4 second interrupt
  // Just to demonstrate how to handle interrupts.
  RTC.CLKSEL = RTC_CLKSEL_INT1K_gc;
  RTC.PITINTCTRL = RTC_PI_bm;
  RTC.PITCTRLA = RTC_PERIOD_CYC4096_gc | RTC_PITEN_bm;
}

// cppcheck-suppress unusedFunction
ISR(RTC_PIT_vect) {
  RTC.PITINTFLAGS = RTC_PI_bm;  // Clear hardware flag
  rtc_tick_flag = 1;            // Set software flag for tasks
}

// Tasks can check (and clear) the flag to kick off
// their work.
bool hal_rtc_take_tick_event(void) {
  if (rtc_tick_flag) {
    rtc_tick_flag = 0;
    return true;
  }
  return false;
}

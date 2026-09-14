#include <stdint.h>

#include "hal/hal_gpio.h"
#include "hal/hal_system.h"
#include "task/task_reset.h"

// Cycle-counted busy wait. avr-gcc turns the builtin into an exact loop at
// compile time, so 1 ms is F_CPU/1000 cycles: 10000 cycles at CLK_PER 10 MHz.
static void delay_ms(void) { __builtin_avr_delay_cycles(F_CPU / 1000UL); }

// Task 2 firmware only. Task 5 replaces this loop with the REQ interrupt path,
// so there is no sleep here: the delay loop itself is what the scope measures.
//
// PA7 is driven high for 1 ms then low for 1 ms, repeated
// task_reset_pulse_count times, then held low for 100 ms. Measuring 1 ms high
// confirms CLK_PER is 10 MHz; the divide-by-6 prescaler left in place after
// reset would stretch it to 3 ms. Counting pulses per burst reports which
// RSTCTRL.RSTFR bit was set at boot.
int main(void) {
  hal_system_init();
  hal_gpio_init();

  const uint8_t pulses = task_reset_pulse_count(hal_system_reset_flags());

  while (1) {
    for (uint8_t i = 0; i < pulses; i++) {
      hal_gpio_toggle_pa7();
      delay_ms();
      hal_gpio_toggle_pa7();
      delay_ms();
    }
    for (uint8_t i = 0; i < 100; i++) {
      delay_ms();
    }
  }
}

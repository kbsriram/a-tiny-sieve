#include <avr/interrupt.h>
#include <avr/sleep.h>

#include "hal/hal_gpio.h"
#include "hal/hal_system.h"
#include "hal/hal_rtc.h"

// Include your tasks here
// #include "task/task_example.h"

int main(void) {
  // --- Hardware Initialization ---
  hal_system_init();
  hal_gpio_init();
  hal_rtc_init();

  // --- Task Initialization ---
  // task_example_init();

  // --- Sleep Configuration MUST only go here---
  set_sleep_mode(SLEEP_MODE_STANDBY);
  sleep_enable();

  // -- enable interrupts
  sei();

  // --- The dispatch loop ---
  while (1) {
    // 1. Task processing
    if (hal_rtc_take_tick_event()) {
      hal_gpio_led_toggle();
    }

    // 2. Sleep until next interrupt
    sleep_cpu();
  }
}

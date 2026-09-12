#include <avr/interrupt.h>
#include <avr/sleep.h>

#include "hal/hal_gpio.h"
#include "hal/hal_rtc.h"
#include "hal/hal_system.h"
#include "task/task_square_wave.h"

int main(void) {
  // --- Hardware Initialization ---
  hal_system_init();
  hal_gpio_init();
  hal_rtc_init();

  // --- Sleep Configuration ---
  set_sleep_mode(SLEEP_MODE_PWR_DOWN);
  sleep_enable();

  // --- Enable interrupts ---
  sei();

  // --- The dispatch loop ---
  while (1) {
    if (hal_rtc_take_tick_event()) {
      task_square_wave_tick();
    }

    sleep_cpu();
  }
}

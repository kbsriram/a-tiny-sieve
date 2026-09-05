#include <avr/interrupt.h>
#include <avr/sleep.h>

#include "hal/hal_gpio.h"
#include "hal/hal_rtc.h"
#include "hal/hal_system.h"
#include "task/task_sieve.h"

int main(void) {
  // --- Hardware Initialization ---
  hal_system_init();
  hal_gpio_init();
  hal_rtc_init();

  // --- Task Initialization ---
  task_sieve_reset();

  // Hardcode a ring and arm at boot for this task.
  // E.g., alternating bits: 10101010... -> 0xAA. Modulus 2.
  uint8_t ring[16] = {0};
  ring[0] = 0xAA;  // 10101010 in binary (accept odd, reject even, or whatever)
  task_sieve_set_ring(2, ring);
  task_sieve_arm();

  // --- Sleep Configuration MUST only go here---
  set_sleep_mode(SLEEP_MODE_PWR_DOWN);
  sleep_enable();

  // -- enable interrupts
  sei();

  // --- The dispatch loop ---
  while (1) {
    // 1. Task processing
    if (hal_rtc_take_tick_event()) {
      // hal_gpio_led_toggle(); // Removed: LED now mirrors VOTE
    }

    if (hal_gpio_req_take_event()) {
      bool veto = task_sieve_step();
      hal_gpio_set_veto(veto);
    }

    // 2. Sleep until next interrupt
    // We cannot route the ring lookup through EVSYS/CCL, and power-down wake
    // adds microseconds of latency. Power down ONLY when disarmed to meet
    // timing.
    if (!task_sieve_is_armed()) {
      sleep_cpu();
    }
  }
}

#include <avr/interrupt.h>
#include <avr/sleep.h>

#include "hal/hal_gpio.h"
#include "hal/hal_rtc.h"
#include "hal/hal_system.h"
#include "hal/hal_twi.h"
#include "task/task_sieve.h"

int main(void) {
  // --- Hardware Initialization ---
  hal_system_init();
  hal_gpio_init();
  hal_rtc_init();

  // --- Task Initialization ---
  task_sieve_reset();
  hal_twi_init(I2C_ADDR);

  // --- Sleep Configuration MUST only go here---
  set_sleep_mode(SLEEP_MODE_IDLE);
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

    uint8_t cmd_buf[18];
    uint8_t cmd_len;
    if (hal_twi_take_command(cmd_buf, &cmd_len)) {
      task_sieve_control(cmd_buf, cmd_len);
    }

    // 2. Sleep until next interrupt
    // We cannot route the ring lookup through EVSYS/CCL, and sleep wake
    // adds microseconds of latency. Sleep in IDLE ONLY when disarmed to meet
    // timing and allow synchronous I2C data interrupts to fire.
    if (!task_sieve_is_armed()) {
      sleep_cpu();
    }
  }
}

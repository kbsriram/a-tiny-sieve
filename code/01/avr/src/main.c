#include <avr/interrupt.h>
#include <avr/sleep.h>

#include "flags.h"
#include "hal/hal_gpio.h"
#include "hal/hal_rtc.h"
#include "hal/hal_system.h"
#include "task/task_button.h"

volatile system_flags_t sys_flags = {0};
int main(void) {
  hal_system_init();
  hal_gpio_init();
  hal_rtc_init();

  set_sleep_mode(SLEEP_MODE_PWR_DOWN);
  sleep_enable();

  sei();

  while (1) {
    if (sys_flags.btn_edge) {
      task_button_process_edge();
    }

    if (sys_flags.rtc_tick) {
      task_button_process_tick();
      sys_flags.rtc_tick = false;
    }

    sleep_cpu();
  }
}

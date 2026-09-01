#include "task_button.h"

#include <stdint.h>

#include "flags.h"
#include "hal/hal_gpio.h"

// Ticks the pin must be quiet before the level is trusted (3 x 15.6ms).
#define DEBOUNCE_TICKS 3

static uint8_t debounce_timer = 0;
static bool last_btn_state = false;

void task_button_process_edge(void) {
  sys_flags.btn_edge = false;
  debounce_timer = DEBOUNCE_TICKS;
}

void task_button_process_tick(void) {
  if (debounce_timer == 0 || --debounce_timer > 0) {
    return;
  }

  bool current_state = hal_gpio_read_button();
  if (current_state == last_btn_state) {
    return;
  }
  last_btn_state = current_state;
  if (current_state) {
    sys_flags.btn_clicked = true;
  }
}

#include "task_beep.h"

#include <stdint.h>

#include "flags.h"
#include "hal/hal_gpio.h"

// Ticks PA2 is held at 0V per beep (4 x 15.6ms).
#define BEEP_TICKS 4

static uint8_t beep_timer = 0;

void task_beep_process_tick(void) {
  if (beep_timer > 0) {
    if (--beep_timer == 0) {
      hal_gpio_od_release();
    }
    // A request arriving mid-beep stays set and starts the next beep.
    return;
  }

  if (sys_flags.beep_request) {
    sys_flags.beep_request = false;
    hal_gpio_od_assert();
    beep_timer = BEEP_TICKS;
  }
}

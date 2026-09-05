#include "task_check.h"

#include <stdbool.h>
#include <stdint.h>

#include "flags.h"

// mod 3
// static const bool click_beeps[] = {true, false, false};

// mod 5
// static const bool click_beeps[] = {false, true, false, false, true};

// mod 7
static const bool click_beeps[] = {false, true, false, true, true, false, true};

// mod 11
// static const bool click_beeps[] = {true, true, false, false, true, false,
// false, true, false, false, true};

#define CLICK_BEEPS_LEN (sizeof(click_beeps) / sizeof(click_beeps[0]))

// Index of the entry the next click will use.
static uint8_t click_index = 0;

void task_check_process_click(void) {
  sys_flags.btn_clicked = false;

  if (click_beeps[click_index]) {
    sys_flags.beep_request = true;
  }

  click_index++;
  if (click_index >= CLICK_BEEPS_LEN) {
    click_index = 0;
  }
}

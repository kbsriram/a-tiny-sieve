#include "test_task_check.h"

#include <assert.h>
#include <stdbool.h>
#include <stdio.h>

#include "flags.h"
#include "task/task_check.h"

// This runs on the host machine, and has no AVR dependencies.

// Must match click_beeps[] in task_check.c.
static const bool expected[] = {false, false, true, true, false};
#define EXPECTED_LEN 5

// Returns true if the click asked for a beep.
static bool click(void) {
  sys_flags.btn_clicked = true;
  sys_flags.beep_request = false;

  task_check_process_click();

  assert(sys_flags.btn_clicked == false);
  bool requested = sys_flags.beep_request;
  sys_flags.beep_request = false;
  return requested;
}

static void test_pattern_and_wraparound(void) {
  printf("  [TEST] Clicks follow the pattern and wrap at 5... ");

  // Two full passes: the counter must return to entry 0 after 5 clicks.
  for (int pass = 0; pass < 2; pass++) {
    for (int i = 0; i < EXPECTED_LEN; i++) {
      assert(click() == expected[i]);
    }
  }

  printf("PASS\n");
}

void test_task_check(void) { test_pattern_and_wraparound(); }

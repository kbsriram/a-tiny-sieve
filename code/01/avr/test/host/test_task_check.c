#include "test_task_check.h"

#include <assert.h>
#include <stdio.h>

#include "flags.h"
#include "task/task_check.h"

// This runs on the host machine, and has no AVR dependencies.

static void test_click_requests_a_beep(void) {
  printf("  [TEST] Click requests a beep... ");

  sys_flags.btn_clicked = true;
  sys_flags.beep_request = false;

  task_check_process_click();

  assert(sys_flags.btn_clicked == false);
  assert(sys_flags.beep_request == true);

  sys_flags.beep_request = false;
  printf("PASS\n");
}

void test_task_check(void) { test_click_requests_a_beep(); }

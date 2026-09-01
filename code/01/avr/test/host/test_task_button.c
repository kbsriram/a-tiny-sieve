#include "test_task_button.h"

#include <assert.h>
#include <stdbool.h>
#include <stdio.h>

#include "flags.h"
#include "task/task_button.h"

// This runs on the host machine, and has no AVR dependencies.

// Flags the task shares with main.c and the ISRs on target.
volatile system_flags_t sys_flags = {0};

// Mock HAL dependencies for the task ----

// true means the contact is closed (pin pulled low).
static bool sim_button_pressed = false;

bool hal_gpio_read_button(void) { return sim_button_pressed; }

// Helpers ----

static void ticks(int n) {
  for (int i = 0; i < n; i++) {
    task_button_process_tick();
  }
}

// Test the task ----

static void test_press_clicks_after_three_ticks(void) {
  printf("  [TEST] Press reports a click after 3 ticks... ");

  sim_button_pressed = true;
  sys_flags.btn_edge = true;
  task_button_process_edge();
  assert(sys_flags.btn_edge == false);

  ticks(2);
  assert(sys_flags.btn_clicked == false);

  ticks(1);
  assert(sys_flags.btn_clicked == true);

  sys_flags.btn_clicked = false;
  printf("PASS\n");
}

static void test_release_reports_no_click(void) {
  printf("  [TEST] Release reports no click... ");

  sim_button_pressed = false;
  task_button_process_edge();
  ticks(3);
  assert(sys_flags.btn_clicked == false);

  printf("PASS\n");
}

static void test_bounce_restarts_the_count(void) {
  printf("  [TEST] Each edge restarts the debounce count... ");

  sim_button_pressed = true;
  task_button_process_edge();
  ticks(2);
  assert(sys_flags.btn_clicked == false);

  // A late bounce edge: the previous 2 ticks must not count.
  task_button_process_edge();
  ticks(2);
  assert(sys_flags.btn_clicked == false);

  ticks(1);
  assert(sys_flags.btn_clicked == true);

  sys_flags.btn_clicked = false;
  printf("PASS\n");
}

static void test_ticks_without_an_edge_do_nothing(void) {
  printf("  [TEST] Ticks without an edge report nothing... ");

  sim_button_pressed = false;
  ticks(10);
  assert(sys_flags.btn_clicked == false);

  printf("PASS\n");
}

void test_task_button(void) {
  test_press_clicks_after_three_ticks();
  test_release_reports_no_click();
  test_bounce_restarts_the_count();
  test_ticks_without_an_edge_do_nothing();
}

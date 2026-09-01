#include "test_task_beep.h"

#include <assert.h>
#include <stdbool.h>
#include <stdio.h>

#include "flags.h"
#include "mock_hal_gpio.h"
#include "task/task_beep.h"

// This runs on the host machine, and has no AVR dependencies.

static void ticks(int n) {
  for (int i = 0; i < n; i++) {
    task_beep_process_tick();
  }
}

static void test_request_holds_pa2_low_for_four_ticks(void) {
  printf("  [TEST] Request holds PA2 at 0V for 4 ticks... ");

  mock_hal_gpio_reset();
  sys_flags.beep_request = true;

  ticks(1);
  assert(sys_flags.beep_request == false);
  assert(sim_od_asserted == true);

  ticks(3);
  assert(sim_od_asserted == true);

  ticks(1);
  assert(sim_od_asserted == false);

  printf("PASS\n");
}

static void test_idle_ticks_leave_pa2_released(void) {
  printf("  [TEST] Ticks without a request leave PA2 high-impedance... ");

  mock_hal_gpio_reset();
  ticks(10);
  assert(sim_od_asserted == false);
  assert(sim_od_assert_count == 0);

  printf("PASS\n");
}

static void test_request_during_a_beep_starts_the_next_one(void) {
  printf("  [TEST] Request during a beep starts the next beep... ");

  mock_hal_gpio_reset();
  sys_flags.beep_request = true;
  ticks(1);
  assert(sim_od_assert_count == 1);

  // Mid-pulse request: must not extend or restart the beep in progress.
  sys_flags.beep_request = true;
  ticks(3);
  assert(sim_od_assert_count == 1);
  assert(sim_od_asserted == true);

  // Tick 5 releases PA2; the pending request runs on tick 6.
  ticks(1);
  assert(sim_od_asserted == false);
  ticks(1);
  assert(sim_od_assert_count == 2);
  assert(sim_od_asserted == true);

  ticks(4);
  assert(sim_od_asserted == false);

  printf("PASS\n");
}

void test_task_beep(void) {
  test_request_holds_pa2_low_for_four_ticks();
  test_idle_ticks_leave_pa2_released();
  test_request_during_a_beep_starts_the_next_one();
}

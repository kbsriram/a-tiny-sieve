#include <assert.h>
#include <stdio.h>

#include "task/task_reset.h"
#include "test_cmd.h"
#include "test_sieve.h"

// RSTCTRL.RSTFR bit masks, datasheet ch10.
#define PORF 0x01
#define BORF 0x02
#define EXTRF 0x04
#define WDRF 0x08
#define SWRF 0x10
#define UPDIRF 0x20

static void test_reset_pulse_count(void) {
  assert(task_reset_pulse_count(0x00) == 0);
  assert(task_reset_pulse_count(PORF) == 1);
  assert(task_reset_pulse_count(BORF) == 2);
  assert(task_reset_pulse_count(EXTRF) == 3);
  assert(task_reset_pulse_count(WDRF) == 4);
  assert(task_reset_pulse_count(SWRF) == 5);
  assert(task_reset_pulse_count(UPDIRF) == 6);

  // A power-on sets PORF and BORF together; the lowest set bit is reported.
  assert(task_reset_pulse_count(PORF | BORF) == 1);
  assert(task_reset_pulse_count(UPDIRF | WDRF) == 4);

  // Bits 6 and 7 are reserved and must not produce a count.
  assert(task_reset_pulse_count(0xC0) == 0);
}

int main(void) {
  printf("\nRunning Host Unit Tests (build 05)\n");
  printf("--------------------------------------\n");

  test_reset_pulse_count();
  test_sieve();
  test_cmd();

  printf("--------------------------------------\n");
  printf("SUCCESS: All tests passed.\n\n");
  return 0;
}

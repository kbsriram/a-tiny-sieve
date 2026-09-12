#include <assert.h>
#include <stdio.h>

#include "mock_hal_gpio.h"
#include "task/task_square_wave.h"

static void test_toggle_invocations(void) {
  mock_hal_gpio_reset();
  assert(mock_hal_gpio_get_toggle_count() == 0);

  task_square_wave_tick();
  assert(mock_hal_gpio_get_toggle_count() == 1);

  task_square_wave_tick();
  assert(mock_hal_gpio_get_toggle_count() == 2);

  task_square_wave_tick();
  assert(mock_hal_gpio_get_toggle_count() == 3);
}

int main(void) {
  printf("\nRunning Host Unit Tests (build 04)\n");
  printf("--------------------------------------\n");

  test_toggle_invocations();

  printf("--------------------------------------\n");
  printf("SUCCESS: All tests passed.\n\n");
  return 0;
}

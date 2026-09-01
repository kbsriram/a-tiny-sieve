#include "mock_hal_gpio.h"

#include "flags.h"

// Flags the tasks share with main.c and the ISRs on target.
volatile system_flags_t sys_flags = {0};

bool sim_button_pressed = false;
bool sim_od_asserted = false;
int sim_od_assert_count = 0;

void mock_hal_gpio_reset(void) {
  sim_button_pressed = false;
  sim_od_asserted = false;
  sim_od_assert_count = 0;
}

bool hal_gpio_read_button(void) { return sim_button_pressed; }

void hal_gpio_od_assert(void) {
  sim_od_asserted = true;
  sim_od_assert_count++;
}

void hal_gpio_od_release(void) { sim_od_asserted = false; }

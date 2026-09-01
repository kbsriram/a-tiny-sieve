#pragma once
#include <stdbool.h>

// true means the button contact is closed (pin pulled low).
extern bool sim_button_pressed;

// true means PA2 is driven to 0V; false means high-impedance.
extern bool sim_od_asserted;

// Counts hal_gpio_od_assert() calls since the last reset.
extern int sim_od_assert_count;

void mock_hal_gpio_reset(void);

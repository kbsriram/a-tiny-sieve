#pragma once
#include <stdbool.h>

void hal_gpio_init(void);
bool hal_gpio_read_button(void);

// PA2 open-drain output: drive the pin to 0V.
void hal_gpio_od_assert(void);

// PA2 open-drain output: release the pin to high-impedance.
void hal_gpio_od_release(void);

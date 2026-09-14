#include "mock_hal_gpio.h"

#include "hal/hal_gpio.h"

static int s_mock_toggle_count = 0;

void mock_hal_gpio_reset(void) { s_mock_toggle_count = 0; }

int mock_hal_gpio_get_toggle_count(void) { return s_mock_toggle_count; }

void hal_gpio_init(void) {}

void hal_gpio_toggle_pa7(void) { s_mock_toggle_count++; }

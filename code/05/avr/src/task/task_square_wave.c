#include "task_square_wave.h"

#include "hal/hal_gpio.h"

void task_square_wave_tick(void) { hal_gpio_toggle_pa7(); }

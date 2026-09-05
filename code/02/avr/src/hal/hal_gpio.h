#pragma once

// Configures all pins (parks unused, sets up I/O)
void hal_gpio_init(void);

// Toggles the LED on PA3
void hal_gpio_led_toggle(void);

#pragma once

#include <stdbool.h>

// Configures all pins (parks unused, sets up I/O)
void hal_gpio_init(void);



// Drives VOTE line (PA7) and LED (PA3).
// True for veto (low VOTE, LED on), false for release (high-Z VOTE, LED off).
void hal_gpio_set_veto(bool veto);

// Returns true if a REQ rising edge occurred and clears the flag.
bool hal_gpio_req_take_event(void);

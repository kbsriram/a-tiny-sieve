#pragma once
#include <stdbool.h>

void hal_rtc_init(void);

// Task logic calls this to see if the tick happened
bool hal_rtc_take_tick_event(void);

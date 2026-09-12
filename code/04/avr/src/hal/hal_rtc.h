#ifndef HAL_RTC_H
#define HAL_RTC_H

#include <stdbool.h>

void hal_rtc_init(void);
bool hal_rtc_take_tick_event(void);

#endif  // HAL_RTC_H

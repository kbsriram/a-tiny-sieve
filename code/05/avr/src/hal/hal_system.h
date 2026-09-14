#ifndef HAL_SYSTEM_H
#define HAL_SYSTEM_H

#include <stdint.h>

void hal_system_init(void);

// RSTCTRL.RSTFR as read at boot, before hal_system_init() cleared it.
// Bit 0 PORF, 1 BORF, 2 EXTRF, 3 WDRF, 4 SWRF, 5 UPDIRF. Datasheet ch10.
uint8_t hal_system_reset_flags(void);

#endif  // HAL_SYSTEM_H

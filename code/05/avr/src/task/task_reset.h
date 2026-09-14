#ifndef TASK_RESET_H
#define TASK_RESET_H

#include <stdint.h>

// LED pulses that report the reset cause, from an RSTCTRL.RSTFR snapshot.
// 1 PORF, 2 BORF, 3 EXTRF, 4 WDRF, 5 SWRF, 6 UPDIRF, 0 if no flag is set.
// Several flags can be set at once, so the lowest set bit is reported.
uint8_t task_reset_pulse_count(uint8_t rstfr);

#endif  // TASK_RESET_H

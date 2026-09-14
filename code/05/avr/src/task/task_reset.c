#include "task_reset.h"

// RSTFR bits 6 and 7 are reserved; datasheet ch10.
#define RSTFR_FLAG_COUNT 6

uint8_t task_reset_pulse_count(uint8_t rstfr) {
  for (uint8_t bit = 0; bit < RSTFR_FLAG_COUNT; bit++) {
    if (rstfr & (uint8_t)(1u << bit)) {
      return (uint8_t)(bit + 1u);
    }
  }
  return 0;
}

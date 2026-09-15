#ifndef TEST_UTIL_H
#define TEST_UTIL_H

#include <stdint.h>

#include "task/task_sieve.h"

// A ring with every bit clear: no phase releases VOTE.
extern const uint8_t k_ring_clear[TASK_SIEVE_RING_BYTES];

// Parses hex text into at most `cap` bytes, byte 0 first. Returns the count.
uint8_t test_parse_hex(const char *hex, uint8_t *out, uint8_t cap);

#endif  // TEST_UTIL_H

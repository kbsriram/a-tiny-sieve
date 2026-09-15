#include "test_util.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

const uint8_t k_ring_clear[TASK_SIEVE_RING_BYTES] = {0};

uint8_t test_parse_hex(const char *hex, uint8_t *out, uint8_t cap) {
  const size_t chars = strlen(hex);
  assert(chars % 2 == 0);
  assert(chars / 2 <= cap);
  for (size_t i = 0; i < chars / 2; i++) {
    unsigned byte = 0;
    const int fields = sscanf(hex + i * 2, "%2x", &byte);
    assert(fields == 1);
    out[i] = (uint8_t)byte;
  }
  return (uint8_t)(chars / 2);
}

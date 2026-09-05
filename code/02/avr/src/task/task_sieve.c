#include "task_sieve.h"

static uint8_t s_modulus = 1;
static uint8_t s_bits[16] = {0};
static uint8_t s_phase = 0;
static bool s_armed = false;

void task_sieve_reset(void) {
  s_phase = 0;
  s_armed = false;
}

void task_sieve_set_ring(uint8_t modulus, const uint8_t* bits) {
  if (modulus == 0) {
    s_modulus = 1;
  } else if (modulus > 128) {
    s_modulus = 128;
  } else {
    s_modulus = modulus;
  }

  for (int i = 0; i < 16; i++) {
    s_bits[i] = bits[i];
  }
}

void task_sieve_arm(void) { s_armed = true; }

bool task_sieve_step(void) {
  if (!s_armed) {
    return false;
  }

  uint8_t byte_idx = s_phase / 8;
  uint8_t bit_idx = s_phase % 8;
  bool accept = (s_bits[byte_idx] & (1 << bit_idx)) != 0;

  s_phase++;
  if (s_phase >= s_modulus) {
    s_phase = 0;
  }

  return !accept;
}

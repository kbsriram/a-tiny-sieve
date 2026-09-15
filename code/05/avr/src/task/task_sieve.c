#include "task_sieve.h"

// The modulus is 2..128, so it fits in uint8_t. There is no phase here: the
// REQ handler in hal_gpio.c holds it in a register and advances it.
static uint8_t s_ring[TASK_SIEVE_RING_BYTES];
static uint8_t s_modulus;
static bool s_armed;

void task_sieve_reset(void) {
  for (uint8_t i = 0; i < TASK_SIEVE_RING_BYTES; i++) {
    s_ring[i] = 0;
  }
  s_modulus = 0;
  s_armed = false;
}

bool task_sieve_set_ring(uint8_t modulus, const uint8_t *ring) {
  if (modulus < TASK_SIEVE_MODULUS_MIN || modulus > TASK_SIEVE_MODULUS_MAX) {
    return false;
  }
  for (uint8_t i = 0; i < TASK_SIEVE_RING_BYTES; i++) {
    s_ring[i] = ring[i];
  }
  s_modulus = modulus;
  s_armed = false;
  return true;
}

bool task_sieve_arm(uint8_t phase) {
  if (s_modulus == 0 || phase >= s_modulus) {
    return false;
  }
  s_armed = true;
  return true;
}

bool task_sieve_release(uint8_t phase) {
  return (s_ring[phase >> 3] >> (phase & 7)) & 1;
}

uint8_t task_sieve_modulus(void) { return s_modulus; }

bool task_sieve_armed(void) { return s_armed; }

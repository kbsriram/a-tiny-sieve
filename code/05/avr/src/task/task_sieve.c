#include "task_sieve.h"

// Phase is 0..127 and the modulus is 2..128, so both fit in uint8_t.
static uint8_t s_ring[TASK_SIEVE_RING_BYTES];
static uint8_t s_modulus;
static uint8_t s_phase;
static bool s_armed;

void task_sieve_reset(void) {
  for (uint8_t i = 0; i < TASK_SIEVE_RING_BYTES; i++) {
    s_ring[i] = 0;
  }
  s_modulus = 0;
  s_phase = 0;
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
  s_phase = 0;
  s_armed = false;
  return true;
}

bool task_sieve_arm(uint8_t phase) {
  if (s_modulus == 0 || phase >= s_modulus) {
    return false;
  }
  s_phase = phase;
  s_armed = true;
  return true;
}

// cppcheck-suppress unusedFunction  ; used from main.c in task 5.
bool task_sieve_step(void) {
  if (!s_armed) {
    return true;
  }
  const bool release = (s_ring[s_phase >> 3] >> (s_phase & 7)) & 1;
  s_phase++;
  if (s_phase >= s_modulus) {
    s_phase = 0;
  }
  return release;
}

// cppcheck-suppress unusedFunction  ; used from main.c in task 5.
uint8_t task_sieve_phase(void) { return s_phase; }

// cppcheck-suppress unusedFunction  ; used from main.c in task 5.
uint8_t task_sieve_modulus(void) { return s_modulus; }

bool task_sieve_armed(void) { return s_armed; }

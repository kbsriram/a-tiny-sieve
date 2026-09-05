#include "task_sieve.h"
#include "hal/hal_gpio.h"

static uint8_t s_modulus = 1;
static uint8_t s_bits[16] = {0};
static uint8_t s_phase = 0;
static bool s_armed = false;

void task_sieve_reset(void) {
  s_phase = 0;
  s_armed = false;
  hal_gpio_set_veto(false);
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

void task_sieve_arm(void) {
  s_armed = true;
  hal_gpio_set_veto(false);
}

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

bool task_sieve_is_armed(void) { return s_armed; }

void task_sieve_control(const uint8_t* buffer, uint8_t len) {
  if (len == 0) return;

  uint8_t cmd = buffer[0];
  if (cmd == 0x01 && len >= 18) {
    task_sieve_set_ring(buffer[1], &buffer[2]);
  } else if (cmd == 0x02) {
    task_sieve_reset();
  } else if (cmd == 0x03) {
    task_sieve_arm();
  }
}


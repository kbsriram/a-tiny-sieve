#include "test_sieve.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "task/task_sieve.h"

#ifndef VECTORS_PATH
#define VECTORS_PATH "../ref/vectors_sieve.txt"
#endif

#define MAX_STEPS 1024

static const uint8_t k_ring_all_clear[TASK_SIEVE_RING_BYTES] = {0};

// Parses "<32 hex chars>" into 16 bytes, byte 0 first.
static void parse_ring(const char *hex, uint8_t *ring) {
  assert(strlen(hex) == TASK_SIEVE_RING_BYTES * 2);
  for (int i = 0; i < TASK_SIEVE_RING_BYTES; i++) {
    unsigned byte = 0;
    const int fields = sscanf(hex + i * 2, "%2x", &byte);
    assert(fields == 1);
    ring[i] = (uint8_t)byte;
  }
}

// Replays every case in the committed vectors file from the Python model.
static void test_vectors(void) {
  FILE *f = fopen(VECTORS_PATH, "r");
  if (f == NULL) {
    printf("FAIL: cannot open %s\n", VECTORS_PATH);
    assert(f != NULL);
  }

  char line[MAX_STEPS + 64];
  char hex[TASK_SIEVE_RING_BYTES * 2 + 1];
  int cases = 0;

  while (fgets(line, sizeof(line), f) != NULL) {
    unsigned modulus = 0;
    unsigned arm_phase = 0;
    unsigned steps = 0;
    if (sscanf(line, "case %u %32s %u %u", &modulus, hex, &arm_phase, &steps) !=
        4) {
      continue;  // Comment or blank line.
    }
    assert(steps > 0 && steps <= MAX_STEPS);

    uint8_t ring[TASK_SIEVE_RING_BYTES];
    parse_ring(hex, ring);

    const char *decisions = fgets(line, sizeof(line), f);
    assert(decisions != NULL);
    assert(strlen(decisions) > steps);

    task_sieve_reset();
    assert(task_sieve_set_ring((uint8_t)modulus, ring));
    assert(task_sieve_arm((uint8_t)arm_phase));

    for (unsigned i = 0; i < steps; i++) {
      const bool got = task_sieve_step();
      const bool want = (decisions[i] == '1');
      if (got != want) {
        printf("FAIL: modulus %u arm %u step %u: got %d want %d\n", modulus,
               arm_phase, i, (int)got, (int)want);
        assert(got == want);
      }
    }
    cases++;
  }
  fclose(f);
  assert(cases >= 30);
  printf("  %d ring vector cases\n", cases);
}

// Modulus and phase limits, and the disarmed path.
static void test_limits(void) {
  task_sieve_reset();
  assert(task_sieve_modulus() == 0);
  assert(task_sieve_phase() == 0);
  assert(!task_sieve_armed());

  // No ring loaded: ARM is rejected.
  assert(!task_sieve_arm(0));

  assert(!task_sieve_set_ring(0, k_ring_all_clear));
  assert(!task_sieve_set_ring(1, k_ring_all_clear));
  assert(!task_sieve_set_ring(129, k_ring_all_clear));
  assert(!task_sieve_set_ring(255, k_ring_all_clear));
  assert(task_sieve_modulus() == 0);

  assert(task_sieve_set_ring(2, k_ring_all_clear));
  assert(task_sieve_set_ring(128, k_ring_all_clear));
  assert(task_sieve_modulus() == 128);

  // ARM is rejected at or above the modulus.
  assert(task_sieve_set_ring(30, k_ring_all_clear));
  assert(!task_sieve_arm(30));
  assert(!task_sieve_arm(255));
  assert(!task_sieve_armed());
  assert(task_sieve_arm(29));
  assert(task_sieve_armed());
  assert(task_sieve_phase() == 29);

  // SET_RING disarms and zeroes the phase.
  assert(task_sieve_set_ring(30, k_ring_all_clear));
  assert(!task_sieve_armed());
  assert(task_sieve_phase() == 0);

  // RESET clears the ring as well.
  assert(task_sieve_arm(5));
  task_sieve_reset();
  assert(task_sieve_modulus() == 0);
  assert(task_sieve_phase() == 0);
  assert(!task_sieve_armed());
}

// Disarmed: VOTE released, phase frozen, for a whole ring of clear bits.
static void test_disarmed(void) {
  task_sieve_reset();
  assert(task_sieve_set_ring(7, k_ring_all_clear));
  for (int i = 0; i < 50; i++) {
    assert(task_sieve_step());
    assert(task_sieve_phase() == 0);
  }
  assert(task_sieve_arm(3));
  assert(task_sieve_phase() == 3);
}

// One set bit at phase p releases VOTE on step p and nowhere else, which
// fails if the ring index is off by one.
static void test_single_bit(void) {
  const uint8_t modulus = 30;
  for (uint8_t p = 0; p < modulus; p++) {
    uint8_t ring[TASK_SIEVE_RING_BYTES] = {0};
    ring[p >> 3] = (uint8_t)(1u << (p & 7));

    task_sieve_reset();
    assert(task_sieve_set_ring(modulus, ring));
    assert(task_sieve_arm(0));
    for (uint8_t i = 0; i < modulus * 2; i++) {
      assert(task_sieve_step() == ((i % modulus) == p));
    }
  }
}

// The phase wraps at the modulus, not at 128.
static void test_wrap(void) {
  uint8_t ring[TASK_SIEVE_RING_BYTES];
  memset(ring, 0xFF, sizeof(ring));

  task_sieve_reset();
  assert(task_sieve_set_ring(7, ring));
  assert(task_sieve_arm(6));
  assert(task_sieve_step());
  assert(task_sieve_phase() == 0);

  assert(task_sieve_set_ring(128, ring));
  assert(task_sieve_arm(127));
  assert(task_sieve_step());
  assert(task_sieve_phase() == 0);
}

void test_sieve(void) {
  test_vectors();
  test_limits();
  test_disarmed();
  test_single_bit();
  test_wrap();
}

#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "task/task_sieve.h"

static void test_all_accept(void) {
  uint8_t bits[16];
  memset(bits, 0xFF, sizeof(bits));
  task_sieve_reset();
  task_sieve_set_ring(5, bits);
  task_sieve_arm();
  for (int i = 0; i < 15; i++) {
    assert(task_sieve_step() == false);
  }
}

static void test_all_reject(void) {
  uint8_t bits[16];
  memset(bits, 0x00, sizeof(bits));
  task_sieve_reset();
  task_sieve_set_ring(5, bits);
  task_sieve_arm();
  for (int i = 0; i < 15; i++) {
    assert(task_sieve_step() == true);
  }
}

static void test_alternating(void) {
  uint8_t bits[16];
  memset(bits, 0xAA, sizeof(bits));  // 10101010
  task_sieve_reset();
  task_sieve_set_ring(12, bits);
  task_sieve_arm();
  for (int i = 0; i < 24; i++) {
    bool expected_veto = (i % 2) == 0;  // bit 0 is 0 -> veto
    assert(task_sieve_step() == expected_veto);
  }
}

static void test_single_set_bit(void) {
  uint8_t bits[16] = {0};
  bits[0] = 0x08;  // bit 3 is set (accept), others are 0 (veto)
  task_sieve_reset();
  task_sieve_set_ring(8, bits);
  task_sieve_arm();
  for (int i = 0; i < 24; i++) {
    bool expected_veto = (i % 8) != 3;
    assert(task_sieve_step() == expected_veto);
  }
}

static void test_no_veto_disarmed(void) {
  uint8_t bits[16] = {0};  // All reject (would normally veto)
  task_sieve_reset();
  task_sieve_set_ring(5, bits);
  // Do not arm
  for (int i = 0; i < 10; i++) {
    assert(task_sieve_step() == false);
  }
}

static void test_modulus_bounds(void) {
  uint8_t bits[16] = {0};
  bits[0] = 0x01;  // bit 0 is set

  // Test 0 gets bounded to 1
  task_sieve_reset();
  task_sieve_set_ring(0, bits);
  task_sieve_arm();
  assert(task_sieve_step() == false);
  assert(task_sieve_step() ==
         false);  // if mod 1, wraps to 0, which is set (no veto)

  // Test >128 gets bounded to 128
  memset(bits, 0, sizeof(bits));
  bits[15] = 0x80;  // bit 127 is set
  task_sieve_reset();
  task_sieve_set_ring(200, bits);
  task_sieve_arm();

  // step 127 times, should be veto
  for (int i = 0; i < 127; i++) {
    assert(task_sieve_step() == true);
  }
  // 127th step (bit 127) should be accept
  assert(task_sieve_step() == false);

  // 128th step (wraps to 0, bit 0 is 0) should be veto
  assert(task_sieve_step() == true);
}

int main(void) {
  printf("\nRunning Host Unit Tests\n");
  printf("-------------------------------\n");

  test_all_accept();
  test_all_reject();
  test_alternating();
  test_single_set_bit();
  test_no_veto_disarmed();
  test_modulus_bounds();

  printf("-------------------------------\n");
  printf("SUCCESS: All tests passed.\n\n");
  return 0;
}

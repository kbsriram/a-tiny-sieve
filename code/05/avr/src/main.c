#include <avr/interrupt.h>
#include <stdint.h>

#include "hal/hal_gpio.h"
#include "hal/hal_system.h"
#include "task/task_sieve.h"

// Task 5 only: there is no I2C yet, so one ring is compiled in. Task 7 deletes
// both constants and the four calls that use them, and loads the ring from a
// SET_RING command instead.
//
// Modulus 7, ring byte 0x49 = bits 0, 3 and 6 set. A set bit releases VOTE, so
// REQ edges from phase 0 give: released, low, low, released, low, low,
// released, then the same again from phase 0.
#define TEST_MODULUS 7
static const uint8_t kTestRing[TASK_SIEVE_RING_BYTES] = {0x49};

int main(void) {
  hal_system_init();

  // Pins first: VOTE and the LED are high-impedance until the first REQ edge.
  hal_gpio_init();

  task_sieve_reset();
  task_sieve_set_ring(TEST_MODULUS, kTestRing);
  hal_gpio_set_ring();
  task_sieve_arm(0);
  hal_gpio_arm(0);

  sei();

  // Every REQ edge is handled in ISR(PORTA_PORT_vect). Task 7 adds IDLE sleep
  // here and the I2C command dispatch.
  while (1) {
  }
}

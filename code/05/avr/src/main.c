#include <avr/cpufunc.h>
#include <avr/interrupt.h>
#include <avr/io.h>
#include <avr/sleep.h>
#include <stdint.h>

#include "hal/hal_gpio.h"
#include "hal/hal_system.h"
#include "hal/hal_twi.h"
#include "task/task_cmd.h"
#include "task/task_sieve.h"

// Pins for the command hal_twi just accepted. task_cmd has already changed the
// ring, the modulus and the armed flag; only the pins are left to follow.
static void apply_command(void) {
  switch (task_cmd_accepted_op()) {
    case TASK_CMD_OP_SET_RING:
      // Disarming clears the LED as well, so put it back: SET_RING changes the
      // ring and the armed state, not the LED.
      hal_gpio_disarm();
      hal_gpio_set_ring();
      hal_gpio_led(task_cmd_led());
      break;
    case TASK_CMD_OP_RESET:
      hal_gpio_disarm();
      break;
    case TASK_CMD_OP_ARM:
      hal_gpio_arm(task_cmd_accepted_phase());
      break;
    case TASK_CMD_OP_LED:
      hal_gpio_led(task_cmd_led());
      break;
    default:
      break;
  }
}

// Stops the CPU clock until the next interrupt, but only while the card is
// disarmed. IDLE leaves every peripheral clocked, so TWI0 still interrupts on
// each received byte (datasheet ch09).
//
// While armed this loop spins instead, because leaving IDLE costs 6 CLK_PER
// cycles, 0.6 us at 10 MHz (ch09), and those cycles would be added to the
// 6 cycles from the REQ rising edge to PA3 sinking current that hal_gpio.c
// counts. No command arrives while armed, so there is nothing to wait for
// anyway.
static void idle_while_disarmed(void) {
  // A command accepted between the two tests and SLEEP would sit unapplied
  // until the host sent another byte. cli() keeps the TWI0 handler out, and the
  // instruction after SEI always runs before any pending interrupt (avr-libc
  // avr/sleep.h), so SLEEP is reached with the tests still true.
  cli();
  if (task_sieve_armed() || hal_twi_command_pending()) {
    sei();
    return;
  }
  sei();
  sleep_cpu();
}

int main(void) {
  hal_system_init();

  // Pins first: VOTE and the LED are high-impedance until a command or a REQ
  // edge changes them.
  hal_gpio_init();

  // Both take the address: task_cmd folds `I2C_ADDR << 1` into every command
  // CRC, hal_twi matches on it.
  task_cmd_init(I2C_ADDR);
  hal_twi_init(I2C_ADDR);

  // Errata DS80000933D: a store to an address at or above 64 immediately
  // followed by a store to SLPCTRL.CTRLA loses the second store, and
  // hal_twi_init() ends by writing TWI0.SCTRLA at 0x0810. One write sets both
  // fields, so no second store to this register can be lost either. SMODE_IDLE
  // is 0 (ch09).
  _NOP();
  SLPCTRL.CTRLA = SLPCTRL_SMODE_IDLE_gc | SLPCTRL_SEN_bm;

  sei();

  // Boot state, unchanged until a command arrives: disarmed, phase 0, no ring,
  // VOTE high-impedance, LED dark. Every REQ edge is handled in
  // ISR(PORTA_PORT_vect) and every I2C byte in ISR(TWI0_TWIS_vect).
  while (1) {
    if (hal_twi_take_command()) {
      apply_command();
      continue;
    }
    idle_while_disarmed();
  }
}

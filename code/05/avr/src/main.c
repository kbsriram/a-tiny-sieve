#include <avr/interrupt.h>
#include <stdint.h>

#include "hal/hal_gpio.h"
#include "hal/hal_system.h"
#include "hal/hal_twi.h"
#include "task/task_cmd.h"

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

int main(void) {
  hal_system_init();

  // Pins first: VOTE and the LED are high-impedance until a command or a REQ
  // edge changes them.
  hal_gpio_init();

  // Both take the address: task_cmd folds `I2C_ADDR << 1` into every command
  // CRC, hal_twi matches on it.
  task_cmd_init(I2C_ADDR);
  hal_twi_init(I2C_ADDR);

  sei();

  // Task 7 adds IDLE sleep here; every REQ edge is handled in
  // ISR(PORTA_PORT_vect) and every I2C byte in ISR(TWI0_TWIS_vect).
  while (1) {
    if (hal_twi_take_command()) {
      apply_command();
    }
  }
}

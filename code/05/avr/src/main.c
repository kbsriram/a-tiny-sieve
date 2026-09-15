#include <avr/interrupt.h>
#include <stdint.h>

#include "hal/hal_gpio.h"
#include "hal/hal_system.h"
#include "hal/hal_twi.h"
#include "task/task_cmd.h"

// Apply pin-level effects of the command task_cmd already decoded.
static void apply_command(void) {
  switch (task_cmd_accepted_op()) {
    case TASK_CMD_OP_SET_RING:
      // SET_RING disarms (clearing the LED); restore the LED state after.
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
  // Pins first: VOTE and the LED stay high-impedance until a command or a REQ
  // edge changes them.
  hal_gpio_init();

  // Same address twice: task_cmd seeds every CRC with it, hal_twi matches it.
  task_cmd_init(I2C_ADDR);
  hal_twi_init(I2C_ADDR);

  sei();

  // Never sleeps, never disables interrupts: every REQ edge reaches the handler
  // in the cycle count hal_gpio.c guarantees.
  while (1) {
    if (hal_twi_take_command()) {
      apply_command();
    }
  }
}

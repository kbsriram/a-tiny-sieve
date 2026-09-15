#ifndef HAL_TWI_H
#define HAL_TWI_H

#include <stdbool.h>
#include <stdint.h>

// TWI0 as an I2C client at one fixed address. Every received byte is ACKed and
// handed to task_cmd; every read returns what task_cmd_read() assembled, then
// 0xFF. Nothing here decides anything about a command.

// Call before sei(), after task_cmd_init() with the same address, and after
// hal_gpio_init(): it re-enables the PA1 and PA2 input buffers that
// hal_gpio_init() switched off, and turns on their pull-ups, the only ones the
// I2C bus has.
void hal_twi_init(uint8_t addr);

// True once per accepted command, at the STOP or repeated START that ended its
// frame. Clears the flag, so a second call returns false.
bool hal_twi_take_command(void);

#endif  // HAL_TWI_H

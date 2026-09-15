#ifndef HAL_TWI_H
#define HAL_TWI_H

#include <stdbool.h>
#include <stdint.h>

// TWI0 as an I2C client at one fixed address. See 05_avr_design.md, sections
// "I2C protocol", "Commands" and "Status read".
//
// Every received byte is acknowledged and passed to the task_cmd decoder.
// Every read returns what task_cmd_read() assembles - the response code, and
// the status bytes after a STATUS the card took - then 0xFF for as long as the
// host keeps clocking. Nothing here decides anything about a command.

// Enables the client at `addr` and its interrupt. Call before sei(), after
// task_cmd_init() with the same address, and after hal_gpio_init(): it
// re-enables the PA1 and PA2 input buffers that hal_gpio_init() switched off,
// and turns on their pull-ups, the only ones the I2C bus has.
void hal_twi_init(uint8_t addr);

// True once for each command the decoder accepted, at the STOP or repeated
// START that ended its frame. The dispatch loop in main.c then applies the
// command to the pins. Clears the flag, so a second call returns false.
bool hal_twi_take_command(void);

// Same flag, left set. main.c tests it with interrupts disabled, just before
// SLEEP, so a command accepted after the last hal_twi_take_command() is applied
// now instead of waiting for the host's next byte.
bool hal_twi_command_pending(void);

#endif  // HAL_TWI_H

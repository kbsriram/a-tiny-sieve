#ifndef HAL_TWI_H
#define HAL_TWI_H

#include <stdbool.h>
#include <stdint.h>

void hal_twi_init(uint8_t addr);

// Returns true if a full I2C command was received.
// Copies up to 18 bytes into buffer_out, and sets len_out to the number of bytes received.
bool hal_twi_take_command(uint8_t* buffer_out, uint8_t* len_out);

#endif  // HAL_TWI_H

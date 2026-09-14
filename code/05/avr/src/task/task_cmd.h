#ifndef TASK_CMD_H
#define TASK_CMD_H

#include <stdbool.h>
#include <stdint.h>

// CRC-8 PEC and the I2C command decoder. See 05_avr_design.md, sections
// "I2C protocol" and "Commands". No AVR headers: this module is compiled and
// tested on the host. The I2C layer only moves bytes; every decision is here.

#define TASK_CMD_OP_SET_RING 0x01
#define TASK_CMD_OP_RESET 0x02
#define TASK_CMD_OP_ARM 0x03
#define TASK_CMD_OP_LED 0x04

// Longest payload: SET_RING sends the modulus plus 16 ring bytes.
#define TASK_CMD_MAX_PAYLOAD 17

// What the I2C layer drives on the bus for the byte just received.
typedef enum { TASK_CMD_ACK = 0, TASK_CMD_NACK = 1 } task_cmd_ack_t;

// Folds one byte into the CRC-8 PEC: polynomial 0x07, no input or output bit
// reversal, no final xor. Start from 0x00. Task 6 calls it on the status-read
// path, over `addr << 1 | 1` and the 4 status bytes.
uint8_t task_cmd_crc8_update(uint8_t crc, uint8_t data);

// Stores the client address, whose `addr << 1` form is the first byte of every
// command CRC, and puts the card in its boot state: no ring, phase 0,
// disarmed, LED dark.
void task_cmd_init(uint8_t addr);

// Address match on a write: begins a new frame and discards any partial one.
void task_cmd_start(void);

// One received byte, in order. The command takes effect on the final CRC byte,
// which is ACKed only when the CRC matches and the command is legal in the
// current state. After any NACK every later byte of the frame also NACKs.
task_cmd_ack_t task_cmd_byte(uint8_t data);

// STOP or repeated START: true when this frame held exactly one complete,
// accepted command. A frame that stops before the CRC byte changes nothing;
// there is no byte left to NACK, so it only returns false here.
bool task_cmd_end(void);

// LED state from the last accepted LED command. RESET clears it.
bool task_cmd_led(void);

#endif  // TASK_CMD_H

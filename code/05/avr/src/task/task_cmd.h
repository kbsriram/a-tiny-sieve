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
#define TASK_CMD_OP_STATUS 0x05

// Longest payload: SET_RING sends the modulus plus 16 ring bytes.
#define TASK_CMD_MAX_PAYLOAD 17

// Response code the host reads back after every command.
#define TASK_CMD_TAKEN 0x00
#define TASK_CMD_FAILED 0xFF

// Longest read: the response code, then phase, flags, modulus, firmware
// version and the CRC over them.
#define TASK_CMD_READ_MAX 6

// Status byte 3, raised when the meaning of any other status byte changes.
#define TASK_CMD_FW_VERSION 0x01

// Status byte 1, bit 6: the card is armed. Bits 0 to 5 are the RSTFR
// snapshot, bit 7 is unused and reads 0.
#define TASK_CMD_FLAG_ARMED 0x40

// The decoder's verdict on the byte just received. It never reaches the bus:
// the card acknowledges every byte and reports the frame's outcome in the
// response code the host reads next.
typedef enum { TASK_CMD_ACK = 0, TASK_CMD_NACK = 1 } task_cmd_ack_t;

// Folds one byte into the CRC-8 PEC: polynomial 0x07, no input or output bit
// reversal, no final xor. Start from 0x00. task_cmd_read() folds the status
// bytes with it, and the host checks a read the same way.
uint8_t task_cmd_crc8_update(uint8_t crc, uint8_t data);

// Stores the client address, whose `addr << 1` form is the first byte of every
// command CRC, and puts the card in its boot state: no ring, phase 0,
// disarmed, LED dark.
void task_cmd_init(uint8_t addr);

// Address match on a write: begins a new frame and discards any partial one.
void task_cmd_start(void);

// One received byte, in order. The command takes effect on the final CRC byte,
// and only when the CRC matches and the command is legal in the current state.
// After any NACK every later byte of the frame also returns NACK.
task_cmd_ack_t task_cmd_byte(uint8_t data);

// STOP or repeated START: true when this frame held exactly one complete,
// accepted command, and latches the response code the host reads next. A frame
// that stops before its CRC byte changes nothing and fails.
bool task_cmd_end(void);

// LED state from the last accepted LED command. RESET clears it.
bool task_cmd_led(void);

// Opcode of the command the last task_cmd_end() reported as accepted, and the
// phase an accepted ARM carried. Both hold until the next accepted command, so
// the dispatch loop can act on one command after the I2C frame has ended.
uint8_t task_cmd_accepted_op(void);
uint8_t task_cmd_accepted_phase(void);

// Fills the bytes the next I2C read returns and gives their number: the
// response code alone, or the response code and 5 status bytes after a STATUS
// the card took. `phase` is the phase the next REQ rising edge will act on,
// `reset_flags` the RSTCTRL.RSTFR snapshot taken at boot. The last byte is the
// CRC-8 PEC over `addr << 1 | 1` and the four status bytes before it, so the
// host checks the read the same way the card checks a command.
uint8_t task_cmd_read(uint8_t phase, uint8_t reset_flags, uint8_t *out);

#endif  // TASK_CMD_H

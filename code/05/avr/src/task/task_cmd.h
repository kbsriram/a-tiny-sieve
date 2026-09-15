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

// Longest read: response code, phase, flags, modulus, firmware version, CRC.
#define TASK_CMD_READ_MAX 6

// Status-read byte 4, raised when the meaning of any other status byte changes.
#define TASK_CMD_FW_VERSION 0x01

// Status-read byte 2, bit 6: the card is armed. Bits 0-5 are the RSTFR
// snapshot, bit 7 is spare and reads 0.
#define TASK_CMD_FLAG_ARMED 0x40

// The decoder's verdict on the byte just received. Never reaches the bus: the
// card ACKs every byte and reports the outcome in the response code.
typedef enum { TASK_CMD_ACK = 0, TASK_CMD_NACK = 1 } task_cmd_ack_t;

// CRC-8 PEC (poly 0x07, init 0x00). Feed bytes one at a time.
uint8_t task_cmd_crc8_update(uint8_t crc, uint8_t data);

// Boot state: addr stored (addr<<1 seeds every CRC), ring cleared, phase 0,
// disarmed, LED dark.
void task_cmd_init(uint8_t addr);

// Start of a write frame; discards any partial frame.
void task_cmd_start(void);

// Feed one byte. Command takes effect on the CRC byte if it matches and the
// command is legal. All subsequent bytes NACK after any NACK.
task_cmd_ack_t task_cmd_byte(uint8_t data);

// STOP or repeated START. True if the frame held one complete accepted command.
// Latches the response code; an incomplete frame fails and changes nothing.
bool task_cmd_end(void);

// LED state from the last accepted LED command. RESET clears it.
bool task_cmd_led(void);

// Opcode and phase of the last accepted command; stable until the next accept.
uint8_t task_cmd_accepted_op(void);
uint8_t task_cmd_accepted_phase(void);

// Fills `out` for the next read: response code only, or response + 5 status
// bytes after a STATUS. Returns the byte count. The last byte is the read CRC
// (seeded with addr<<1|1, so a status read cannot be replayed as a command).
uint8_t task_cmd_read(uint8_t phase, uint8_t reset_flags, uint8_t *out);

#endif  // TASK_CMD_H

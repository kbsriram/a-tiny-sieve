#include "task_cmd.h"

#include "task_sieve.h"

// Payload length returned for an opcode the card does not implement.
#define PAYLOAD_UNKNOWN 0xFF

static uint8_t s_addr_byte;  // addr << 1, the first byte of every command CRC.
static uint8_t s_crc;        // Running CRC over the bytes seen so far.
static uint8_t s_index;      // Bytes received in this frame, opcode included.
static uint8_t s_op;
static uint8_t s_payload[TASK_CMD_MAX_PAYLOAD];
static bool s_nack;      // A byte in this frame was NACKed.
static bool s_accepted;  // The CRC byte matched and the command was applied.
static bool s_led;

uint8_t task_cmd_crc8_update(uint8_t crc, uint8_t data) {
  crc ^= data;
  for (uint8_t bit = 0; bit < 8; bit++) {
    if (crc & 0x80) {
      crc = (uint8_t)((uint8_t)(crc << 1) ^ 0x07);
    } else {
      crc = (uint8_t)(crc << 1);
    }
  }
  return crc;
}

// Payload bytes between the opcode and the CRC byte, per design doc Commands.
static uint8_t payload_len(uint8_t op) {
  switch (op) {
    case TASK_CMD_OP_SET_RING:
      return 1 + TASK_SIEVE_RING_BYTES;  // Modulus, then the 16 ring bytes.
    case TASK_CMD_OP_RESET:
      return 0;
    case TASK_CMD_OP_ARM:
      return 1;  // Phase.
    case TASK_CMD_OP_LED:
      return 1;  // State, 0 dark.
    default:
      return PAYLOAD_UNKNOWN;
  }
}

// Runs the decoded command. False means NACK the CRC byte and change nothing.
static bool apply(void) {
  switch (s_op) {
    case TASK_CMD_OP_SET_RING:
      return task_sieve_set_ring(s_payload[0], &s_payload[1]);
    case TASK_CMD_OP_RESET:
      task_sieve_reset();
      s_led = false;
      return true;
    case TASK_CMD_OP_ARM:
      return task_sieve_arm(s_payload[0]);
    case TASK_CMD_OP_LED:
      if (task_sieve_armed()) {
        return false;
      }
      s_led = (s_payload[0] != 0);
      return true;
    default:
      return false;
  }
}

// cppcheck-suppress unusedFunction  ; used from main.c in task 6.
void task_cmd_init(uint8_t addr) {
  s_addr_byte = (uint8_t)(addr << 1);
  s_led = false;
  task_sieve_reset();
  task_cmd_start();
}

void task_cmd_start(void) {
  s_crc = task_cmd_crc8_update(0x00, s_addr_byte);
  s_index = 0;
  s_op = 0;
  s_nack = false;
  s_accepted = false;
}

// cppcheck-suppress unusedFunction  ; used from hal_twi.c in task 6.
task_cmd_ack_t task_cmd_byte(uint8_t data) {
  if (s_nack) {
    return TASK_CMD_NACK;
  }

  if (s_index == 0) {
    if (payload_len(data) == PAYLOAD_UNKNOWN) {
      s_nack = true;
      return TASK_CMD_NACK;
    }
    s_op = data;
    s_crc = task_cmd_crc8_update(s_crc, data);
    s_index = 1;
    return TASK_CMD_ACK;
  }

  const uint8_t len = payload_len(s_op);
  if (s_index <= len) {
    s_payload[s_index - 1] = data;
    s_crc = task_cmd_crc8_update(s_crc, data);
    s_index++;
    return TASK_CMD_ACK;
  }

  if (s_index == (uint8_t)(len + 1)) {
    s_index++;
    if (data != s_crc || !apply()) {
      s_nack = true;
      return TASK_CMD_NACK;
    }
    s_accepted = true;
    return TASK_CMD_ACK;
  }

  s_nack = true;  // A byte after the CRC byte: the frame is too long.
  return TASK_CMD_NACK;
}

// cppcheck-suppress unusedFunction  ; used from hal_twi.c in task 6.
bool task_cmd_end(void) {
  const bool ok = s_accepted && !s_nack;
  task_cmd_start();
  return ok;
}

// cppcheck-suppress unusedFunction  ; used from main.c in task 6.
bool task_cmd_led(void) { return s_led; }

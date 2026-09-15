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
static uint8_t s_done_op;     // Opcode of the last accepted command.
static uint8_t s_done_phase;  // Phase the last accepted ARM carried.
static uint8_t s_response;    // Response code for the last frame.

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
    case TASK_CMD_OP_STATUS:
      return 0;
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
    case TASK_CMD_OP_STATUS:
      // Changes nothing: it only decides what the next read returns.
      return true;
    default:
      return false;
  }
}

void task_cmd_init(uint8_t addr) {
  s_addr_byte = (uint8_t)(addr << 1);
  s_led = false;
  s_done_op = 0;
  s_done_phase = 0;
  s_response = TASK_CMD_FAILED;  // No command yet.
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
    s_done_op = s_op;
    s_done_phase = (s_op == TASK_CMD_OP_ARM) ? s_payload[0] : 0;
    return TASK_CMD_ACK;
  }

  s_nack = true;  // A byte after the CRC byte: the frame is too long.
  return TASK_CMD_NACK;
}

bool task_cmd_end(void) {
  const bool ok = s_accepted && !s_nack;
  s_response = ok ? TASK_CMD_TAKEN : TASK_CMD_FAILED;
  task_cmd_start();
  return ok;
}

bool task_cmd_led(void) { return s_led; }

uint8_t task_cmd_accepted_op(void) { return s_done_op; }

uint8_t task_cmd_accepted_phase(void) { return s_done_phase; }

// The 4 status bytes and the CRC over them, at `out`.
static void status(uint8_t phase, uint8_t reset_flags, uint8_t *out) {
  out[0] = phase;
  // RSTFR has six flags, so bits 6 and 7 of the snapshot are always 0 and bit
  // 6 is free for the armed bit. Masking keeps that true whatever is passed.
  out[1] = (uint8_t)((reset_flags & 0x3F) |
                     (task_sieve_armed() ? TASK_CMD_FLAG_ARMED : 0));
  out[2] = task_sieve_modulus();
  out[3] = TASK_CMD_FW_VERSION;

  // The CRC starts from the address byte with the read bit set, so a status
  // read can never be replayed as a command frame and pass its CRC.
  uint8_t crc = task_cmd_crc8_update(0x00, (uint8_t)(s_addr_byte | 1));
  for (uint8_t i = 0; i < 4; i++) {
    crc = task_cmd_crc8_update(crc, out[i]);
  }
  out[4] = crc;
}

uint8_t task_cmd_read(uint8_t phase, uint8_t reset_flags, uint8_t *out) {
  out[0] = s_response;
  if (s_response != TASK_CMD_TAKEN || s_done_op != TASK_CMD_OP_STATUS) {
    return 1;
  }
  status(phase, reset_flags, &out[1]);
  return TASK_CMD_READ_MAX;
}

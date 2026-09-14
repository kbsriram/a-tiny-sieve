#include "test_cmd.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "task/task_cmd.h"
#include "task/task_sieve.h"

#ifndef VECTORS_CMD_PATH
#define VECTORS_CMD_PATH "../ref/vectors_cmd.txt"
#endif

// Longest frame: SET_RING is the opcode, 17 payload bytes, and the CRC byte.
#define MAX_FRAME (1 + TASK_CMD_MAX_PAYLOAD + 1)
#define MAX_HEX (MAX_FRAME * 2 + 2)

static const uint8_t k_ring_zero[TASK_SIEVE_RING_BYTES] = {0};

// Parses hex text into bytes. Returns the byte count.
static uint8_t parse_hex(const char *hex, uint8_t *out, uint8_t cap) {
  const size_t chars = strlen(hex);
  assert(chars % 2 == 0);
  assert(chars / 2 <= cap);
  for (size_t i = 0; i < chars / 2; i++) {
    unsigned byte = 0;
    const int fields = sscanf(hex + i * 2, "%2x", &byte);
    assert(fields == 1);
    out[i] = (uint8_t)byte;
  }
  return (uint8_t)(chars / 2);
}

// Writes one frame to the decoder. Stores the ACK/NACK of the last byte in
// `last` and returns what task_cmd_end() reported.
static bool feed(const uint8_t *frame, uint8_t len, task_cmd_ack_t *last) {
  task_cmd_start();
  task_cmd_ack_t ack = TASK_CMD_ACK;
  for (uint8_t i = 0; i < len; i++) {
    ack = task_cmd_byte(frame[i]);
  }
  if (last != NULL) {
    *last = ack;
  }
  return task_cmd_end();
}

// Builds opcode, payload, and the CRC byte over `addr << 1`. Returns the
// frame length.
static uint8_t build(uint8_t addr, uint8_t op, const uint8_t *payload,
                     uint8_t payload_len, uint8_t *out) {
  uint8_t crc = task_cmd_crc8_update(0x00, (uint8_t)(addr << 1));
  out[0] = op;
  crc = task_cmd_crc8_update(crc, op);
  for (uint8_t i = 0; i < payload_len; i++) {
    out[1 + i] = payload[i];
    crc = task_cmd_crc8_update(crc, payload[i]);
  }
  out[1 + payload_len] = crc;
  return (uint8_t)(payload_len + 2);
}

// The CRC-8 PEC over byte strings the Python model also folded.
static void test_crc_vectors(int *counted) {
  FILE *f = fopen(VECTORS_CMD_PATH, "r");
  if (f == NULL) {
    printf("FAIL: cannot open %s\n", VECTORS_CMD_PATH);
    assert(f != NULL);
  }

  char line[256];
  char hex[MAX_HEX + 24];
  int cases = 0;
  while (fgets(line, sizeof(line), f) != NULL) {
    unsigned expect = 0;
    if (sscanf(line, "crc %63s %2x", hex, &expect) != 2) {
      continue;
    }
    uint8_t data[32];
    const uint8_t len = parse_hex(hex, data, (uint8_t)sizeof(data));
    uint8_t crc = 0x00;
    for (uint8_t i = 0; i < len; i++) {
      crc = task_cmd_crc8_update(crc, data[i]);
    }
    assert(crc == (uint8_t)expect);
    cases++;
  }
  fclose(f);
  assert(cases >= 50);
  *counted = cases;
}

// Replays each scenario: every frame the model built, the ACK it expects on
// the last byte, and the card state that must follow.
static void test_scenarios(int *counted) {
  FILE *f = fopen(VECTORS_CMD_PATH, "r");
  assert(f != NULL);

  char line[256];
  char hex[MAX_HEX + 24];
  int frames = 0;
  bool have_scenario = false;

  while (fgets(line, sizeof(line), f) != NULL) {
    unsigned addr = 0;
    if (sscanf(line, "scenario %2x", &addr) == 1) {
      task_cmd_init((uint8_t)addr);
      assert(task_sieve_modulus() == 0);
      assert(!task_sieve_armed());
      assert(!task_cmd_led());
      have_scenario = true;
      continue;
    }

    unsigned accepted = 0, modulus = 0, phase = 0, armed = 0, led = 0;
    if (sscanf(line, "frame %63s %u %u %u %u %u", hex, &accepted, &modulus,
               &phase, &armed, &led) != 6) {
      continue;
    }
    assert(have_scenario);

    uint8_t frame[MAX_FRAME];
    const uint8_t len = parse_hex(hex, frame, MAX_FRAME);
    task_cmd_ack_t last = TASK_CMD_ACK;
    const bool ok = feed(frame, len, &last);

    assert(ok == (accepted != 0));
    assert((last == TASK_CMD_ACK) == (accepted != 0));
    assert(task_sieve_modulus() == (uint8_t)modulus);
    assert(task_sieve_phase() == (uint8_t)phase);
    assert(task_sieve_armed() == (armed != 0));
    assert(task_cmd_led() == (led != 0));
    frames++;
  }
  fclose(f);
  assert(frames >= 12);
  *counted = frames;
}

// Total frame bytes for an opcode, CRC byte included, or 0 when the card does
// not implement it.
static uint8_t frame_len_for(uint8_t op) {
  switch (op) {
    case TASK_CMD_OP_SET_RING:
      return 1 + 1 + TASK_SIEVE_RING_BYTES + 1;
    case TASK_CMD_OP_RESET:
      return 2;
    case TASK_CMD_OP_ARM:
    case TASK_CMD_OP_LED:
      return 3;
    default:
      return 0;
  }
}

// Flipping any one bit of a valid frame must leave task_cmd_end() false. The
// last byte also NACKs, except where the flip landed on the opcode and turned
// it into a command whose frame is longer: the host then stops early and no
// byte is left to NACK.
static void test_single_bit_flips(void) {
  const uint8_t addr = 0x12;
  uint8_t ring[TASK_SIEVE_RING_BYTES];
  for (uint8_t i = 0; i < TASK_SIEVE_RING_BYTES; i++) {
    ring[i] = (uint8_t)(0x5A + i);
  }

  uint8_t set_ring_payload[1 + TASK_SIEVE_RING_BYTES];
  set_ring_payload[0] = 30;
  memcpy(&set_ring_payload[1], ring, TASK_SIEVE_RING_BYTES);

  const uint8_t arm_payload[1] = {7};
  const uint8_t led_payload[1] = {1};

  struct {
    uint8_t op;
    const uint8_t *payload;
    uint8_t len;
    bool needs_ring;
  } commands[] = {
      {TASK_CMD_OP_SET_RING, set_ring_payload, sizeof(set_ring_payload), false},
      {TASK_CMD_OP_RESET, NULL, 0, false},
      {TASK_CMD_OP_ARM, arm_payload, 1, true},
      {TASK_CMD_OP_LED, led_payload, 1, false},
  };

  for (size_t c = 0; c < sizeof(commands) / sizeof(commands[0]); c++) {
    uint8_t good[MAX_FRAME];
    const uint8_t len =
        build(addr, commands[c].op, commands[c].payload, commands[c].len, good);

    for (uint8_t byte = 0; byte < len; byte++) {
      for (uint8_t bit = 0; bit < 8; bit++) {
        task_cmd_init(addr);
        if (commands[c].needs_ring) {
          uint8_t setup[MAX_FRAME];
          const uint8_t n = build(addr, TASK_CMD_OP_SET_RING, set_ring_payload,
                                  sizeof(set_ring_payload), setup);
          assert(feed(setup, n, NULL));
        }

        uint8_t bad[MAX_FRAME];
        memcpy(bad, good, len);
        bad[byte] ^= (uint8_t)(1u << bit);

        task_cmd_ack_t last = TASK_CMD_ACK;
        assert(!feed(bad, len, &last));
        const uint8_t flipped_len = (byte == 0) ? frame_len_for(bad[0]) : len;
        if (flipped_len <= len) {
          assert(last == TASK_CMD_NACK);
        }
      }
    }

    // The unflipped frame is still accepted, so the loop tested corruption
    // and not a decoder that NACKs everything.
    task_cmd_init(addr);
    if (commands[c].needs_ring) {
      uint8_t setup[MAX_FRAME];
      const uint8_t n = build(addr, TASK_CMD_OP_SET_RING, set_ring_payload,
                              sizeof(set_ring_payload), setup);
      assert(feed(setup, n, NULL));
    }
    task_cmd_ack_t last = TASK_CMD_NACK;
    assert(feed(good, len, &last));
    assert(last == TASK_CMD_ACK);
  }
}

// Unknown opcode, a frame that stops early, and a frame with a trailing byte.
static void test_malformed_frames(void) {
  const uint8_t addr = 0x10;
  uint8_t payload[1 + TASK_SIEVE_RING_BYTES];
  payload[0] = 7;
  memcpy(&payload[1], k_ring_zero, TASK_SIEVE_RING_BYTES);

  // Unknown opcode: NACKed on the opcode byte itself, before any payload.
  for (unsigned op = 0; op < 256; op++) {
    if (op >= TASK_CMD_OP_SET_RING && op <= TASK_CMD_OP_LED) {
      continue;
    }
    task_cmd_init(addr);
    task_cmd_start();
    assert(task_cmd_byte((uint8_t)op) == TASK_CMD_NACK);
    assert(task_cmd_byte(0x00) == TASK_CMD_NACK);
    assert(!task_cmd_end());
    assert(task_sieve_modulus() == 0);
  }

  uint8_t good[MAX_FRAME];
  const uint8_t len =
      build(addr, TASK_CMD_OP_SET_RING, payload, sizeof(payload), good);

  // Short frame: every truncation stops before the CRC byte, so nothing is
  // applied. There is no byte left to NACK.
  for (uint8_t cut = 0; cut < len; cut++) {
    task_cmd_init(addr);
    assert(!feed(good, cut, NULL));
    assert(task_sieve_modulus() == 0);
    assert(!task_sieve_armed());
  }

  // Overlong frame: the byte after the CRC byte NACKs.
  uint8_t overlong[MAX_FRAME + 1];
  memcpy(overlong, good, len);
  overlong[len] = 0x00;
  task_cmd_init(addr);
  task_cmd_ack_t last = TASK_CMD_ACK;
  assert(!feed(overlong, (uint8_t)(len + 1), &last));
  assert(last == TASK_CMD_NACK);

  // A new frame after a NACKed one is decoded normally.
  task_cmd_init(addr);
  assert(!feed(overlong, (uint8_t)(len + 1), NULL));
  assert(feed(good, len, NULL));
  assert(task_sieve_modulus() == 7);
}

// A frame addressed to a different card fails the CRC, because the address
// byte is the first byte folded into it.
static void test_address_is_in_the_crc(void) {
  uint8_t frame[MAX_FRAME];
  const uint8_t phase[1] = {1};

  task_cmd_init(0x11);
  uint8_t setup[MAX_FRAME];
  uint8_t payload[1 + TASK_SIEVE_RING_BYTES];
  payload[0] = 3;
  memcpy(&payload[1], k_ring_zero, TASK_SIEVE_RING_BYTES);
  const uint8_t setup_len =
      build(0x11, TASK_CMD_OP_SET_RING, payload, sizeof(payload), setup);
  assert(feed(setup, setup_len, NULL));

  const uint8_t len = build(0x12, TASK_CMD_OP_ARM, phase, 1, frame);
  assert(!feed(frame, len, NULL));
  assert(!task_sieve_armed());

  const uint8_t own = build(0x11, TASK_CMD_OP_ARM, phase, 1, frame);
  assert(feed(frame, own, NULL));
  assert(task_sieve_armed());
}

void test_cmd(void) {
  int crcs = 0, frames = 0;
  test_crc_vectors(&crcs);
  printf("PASS: CRC-8 PEC, %d vectors from model.py\n", crcs);

  test_scenarios(&frames);
  printf("PASS: command scenarios, %d frames from model.py\n", frames);

  test_single_bit_flips();
  printf("PASS: every single-bit flip NACKs the last byte\n");

  test_malformed_frames();
  printf("PASS: unknown opcode, short frame, overlong frame\n");

  test_address_is_in_the_crc();
  printf("PASS: the address byte is folded into the command CRC\n");
}

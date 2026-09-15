#ifndef TASK_SIEVE_H
#define TASK_SIEVE_H

#include <stdbool.h>
#include <stdint.h>

// Ring, phase, and arm state for one card. See 05_avr_design.md, section Ring.
// No AVR headers: this module is compiled and tested on the host.

#define TASK_SIEVE_RING_BYTES 16
#define TASK_SIEVE_MODULUS_MIN 2
#define TASK_SIEVE_MODULUS_MAX 128

// Boot state and the RESET command: no ring, modulus 0, phase 0, disarmed.
void task_sieve_reset(void);

// SET_RING: copies 16 ring bytes, sets the modulus, phase 0, disarmed.
// Ring bit `phase` is bit (phase % 8) of ring[phase / 8]. Rejects a modulus
// outside TASK_SIEVE_MODULUS_MIN..TASK_SIEVE_MODULUS_MAX and changes nothing.
bool task_sieve_set_ring(uint8_t modulus, const uint8_t *ring);

// ARM: validates `phase` and records that the card is armed. Rejects a phase
// at or above the modulus, and rejects any phase when no ring is loaded;
// changes nothing when rejected. The live phase belongs to hal_gpio: the REQ
// handler advances it, and hal_gpio_phase() reads it back.
bool task_sieve_arm(uint8_t phase);

// Decision for one phase of the loaded ring: true releases VOTE, false drives
// VOTE low. Ring bit `phase` is bit (phase % 8) of ring[phase / 8]. Reads the
// ring loaded by task_sieve_set_ring(); the result is meaningless before that.
bool task_sieve_release(uint8_t phase);

// Status read fields.
uint8_t task_sieve_modulus(void);  // 0 when no ring is loaded.
bool task_sieve_armed(void);

#endif  // TASK_SIEVE_H

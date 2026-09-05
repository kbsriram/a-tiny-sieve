#ifndef TASK_SIEVE_H
#define TASK_SIEVE_H

#include <stdbool.h>
#include <stdint.h>

// Reset phase to 0 and disarm.
void task_sieve_reset(void);

// Set the ring modulus (1..128) and bits (16 bytes).
void task_sieve_set_ring(uint8_t modulus, const uint8_t* bits);

// Arm the sieve.
void task_sieve_arm(void);

// Returns true if the current phase should veto (bit is 0), then advances
// phase. Returns false (no veto) if disarmed.
bool task_sieve_step(void);

// Returns true if armed.
bool task_sieve_is_armed(void);

#endif  // TASK_SIEVE_H

#ifndef HAL_GPIO_H
#define HAL_GPIO_H

#include <stdbool.h>
#include <stdint.h>

// Pins for one card: PA6 REQ in, PA3 VOTE out, PA7 LED out.

// Leaves VOTE high-impedance, the LED dark and the card disarmed.
// Call before sei().
void hal_gpio_init(void);

// Expands task_sieve's ring into one VPORTA.DIR byte per phase. The REQ
// handler has no time to unpack a bit, so every phase is already a byte in
// SRAM. Call after each accepted SET_RING, before arming.
void hal_gpio_set_ring(void);

// Starts stepping at `phase`, which must be below the loaded modulus.
// hal_gpio_set_ring() must have run since the last SET_RING.
void hal_gpio_arm(uint8_t phase);

// Disables the PA6 edge, releases VOTE, returns the phase to 0. VOTE and the
// LED share one VPORTA.DIR write, so this darkens the LED too; RESET wants
// that, SET_RING does not, so main.c restores the LED after a SET_RING.
void hal_gpio_disarm(void);

// Only legal while disarmed: armed, the REQ handler owns the same register.
void hal_gpio_led(bool on);

// Phase the next REQ rising edge will act on.
uint8_t hal_gpio_phase(void);

#endif  // HAL_GPIO_H

#ifndef HAL_GPIO_H
#define HAL_GPIO_H

#include <stdbool.h>
#include <stdint.h>

// Pins for one card: PA6 REQ in, PA3 VOTE out, PA7 LED out.
// See 05_avr_design.md, sections Pins, VOTE and LED, and Run path.

// Configures every pin, leaves VOTE high-impedance, the LED dark and the card
// disarmed. Call before sei().
void hal_gpio_init(void);

// Expands the ring held by task_sieve into one VPORTA.DIR byte per phase, the
// table the REQ handler indexes. The handler has no time to unpack a bit, so
// every phase's pin state must already be a byte in SRAM. Call after every
// accepted SET_RING, before arming.
void hal_gpio_set_ring(void);

// Starts stepping at `phase`: loads the handler's registers, then enables the
// PA6 rising-edge interrupt. `phase` must be below the loaded modulus, and
// hal_gpio_set_ring() must have run since the last SET_RING.
void hal_gpio_arm(uint8_t phase);

// Disables the PA6 edge, releases VOTE and returns the phase to 0. It clears
// the LED too, because VOTE and the LED share one VPORTA.DIR write; RESET wants
// that, SET_RING does not, so main.c restores the LED after a SET_RING.
void hal_gpio_disarm(void);

// Lights the LED or darkens it. Only legal while disarmed: armed, the REQ
// handler owns the same register and the LED follows VOTE.
void hal_gpio_led(bool on);

// Phase the next REQ rising edge will act on. Status-read byte 1.
uint8_t hal_gpio_phase(void);

#endif  // HAL_GPIO_H

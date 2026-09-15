#include "hal_gpio.h"

#include <avr/cpufunc.h>
#include <avr/interrupt.h>
#include <avr/io.h>

#include "task/task_sieve.h"

// DIR=1 drives low; OUT stays 0. 0x88 sinks VOTE and lights the LED.
#define VOTE_LOW_DIR (PIN3_bm | PIN7_bm)

// VPORTA.DIR value per phase. One spare entry so the ISR's pointer stays
// in-bounds after the last phase.
static uint8_t s_dir[TASK_SIEVE_MODULUS_MAX + 1];

// Owned by the ISR, reserved in the Makefile via -ffixed.
register uint8_t s_next_dir __asm__("r2");      // DIR value for the next edge
register const uint8_t *s_next __asm__("r26");  // &s_dir[next phase]
register uint8_t s_wrap_lo __asm__("r4");       // low byte of &s_dir[modulus]

// REQ rising edge on PA6. ISR_NAKED because avr-gcc's prologue would delay the
// OUT that drives VOTE. No SREG save: no instruction here writes a flag, which
// is also why CPSE is used instead of CP.
//
// 6 cycles from the edge to PA3 sinking, 16 to the end of RETI, the same at
// every phase. Measured: 947 ns and 1.684 us with 30 cards fitted.
//
// SBI clears any set INTFLAGS bit, so no other PA pin may have an edge sense.
// Errata DS80000933D: a store >=64 then one <64 loses the second; OUT avoids
// ST.
// cppcheck-suppress unusedFunction  ; the vector table calls it.
ISR(PORTA_PORT_vect, ISR_NAKED) {
  __asm__ volatile(
      "out  %[dir], r2"
      "\n\t"  // drive VOTE and the LED
      "sbi  %[flags], 6"
      "\n\t"  // clear the PA6 interrupt flag
      "cpse r26, r4"
      "\n\t"  // reached &s_dir[modulus]?
      "rjmp .+2"
      "\n\t"  // no: keep the pointer
      "ldi  r26, lo8(%[tbl])"
      "\n\t"  // yes: phase wraps to 0
      "ld   r2, X+"
      "\n\t"  // next edge's value, advance the phase
      "reti"
      "\n\t"
      :
      : [dir] "I"(_SFR_IO_ADDR(VPORTA.DIR)),
        [flags] "I"(_SFR_IO_ADDR(VPORTA.INTFLAGS)), [tbl] "i"(&s_dir[0]));
}

// Phase 0, VOTE released. Call only with the PA6 edge disabled. s_next points
// one ahead of s_next_dir, so hal_gpio_phase() returns 0.
static void rewind_phase(void) {
  s_next_dir = 0;
  s_next = &s_dir[1];
  s_wrap_lo = (uint8_t)(uint16_t)&s_dir[1];
}

void hal_gpio_init(void) {
  PORTA.OUT = 0;  // OUT stays 0 forever; DIR drives low or releases.
  PORTA.DIR = 0;

  // An input buffer with no reader only draws current. PA1 and PA2 stay off
  // until hal_twi_init() re-enables them. PA6 with no edge sense is disarmed.
  PORTA.PIN0CTRL = PORT_ISC_INPUT_DISABLE_gc;
  PORTA.PIN1CTRL = PORT_ISC_INPUT_DISABLE_gc;
  PORTA.PIN2CTRL = PORT_ISC_INPUT_DISABLE_gc;
  PORTA.PIN3CTRL = PORT_PULLUPEN_bm | PORT_ISC_INPUT_DISABLE_gc;
  PORTA.PIN6CTRL = PORT_PULLUPEN_bm;
  PORTA.PIN7CTRL = PORT_ISC_INPUT_DISABLE_gc;

  PORTA.INTFLAGS = 0xFF;  // Discard flags set during pin config.
  rewind_phase();
}

void hal_gpio_set_ring(void) {
  // SET_RING disarms, so no REQ edge can read a half-rewritten table.
  const uint8_t modulus = task_sieve_modulus();
  for (uint8_t phase = 0; phase < modulus; phase++) {
    s_dir[phase] = task_sieve_release(phase) ? 0 : VOTE_LOW_DIR;
  }
}

void hal_gpio_arm(uint8_t phase) {
  const uint8_t modulus = task_sieve_modulus();

  const uint8_t sreg = SREG;
  cli();  // Stop a mid-update edge mixing old and new phase registers.

  s_next_dir = s_dir[phase];
  s_next = &s_dir[phase + 1];  // One ahead of the value in r2.
  s_wrap_lo = (uint8_t)(uint16_t)&s_dir[modulus];

  PORTA.INTFLAGS = PIN6_bm;  // Discard edges seen while disarmed.
  PORTA.PIN6CTRL = PORT_PULLUPEN_bm | PORT_ISC_RISING_gc;

  SREG = sreg;
}

void hal_gpio_disarm(void) {
  const uint8_t sreg = SREG;
  cli();  // Stop an edge re-driving VOTE after the release below.

  PORTA.PIN6CTRL = PORT_PULLUPEN_bm;
  PORTA.INTFLAGS = PIN6_bm;
  // Errata DS80000933D: a store to INTFLAGS (>= 64) immediately followed by
  // one to VPORTA.DIR (< 64) loses the second.
  _NOP();
  VPORTA.DIR = 0;

  rewind_phase();
  SREG = sreg;
}

void hal_gpio_led(bool on) {
  // Disarmed: DIR is 0 and the ISR cannot run, so no guard is needed.
  VPORTA.DIR = on ? PIN7_bm : 0;
}

uint8_t hal_gpio_phase(void) {
  return (uint8_t)(s_next - &s_dir[0]) - 1;  // s_next is one phase ahead.
}

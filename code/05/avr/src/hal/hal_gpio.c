#include "hal_gpio.h"

#include <avr/cpufunc.h>
#include <avr/interrupt.h>
#include <avr/io.h>

#include "task/task_sieve.h"

// DIR=1 drives low (OUT stays 0 always); 0x88 sinks VOTE and lights the LED.
#define VOTE_LOW_DIR (PIN3_bm | PIN7_bm)

// VPORTA.DIR value per phase. +1 so the handler's X pointer stays in-bounds
// after the last phase; all SRAM addresses share the same high byte (ch04),
// so wrapping only reloads the low byte.
static uint8_t s_dir[TASK_SIEVE_MODULUS_MAX + 1];

// Registers owned by the ISR, reserved via -ffixed-r2 -ffixed-r4 -ffixed-r26
// -ffixed-r27 (Makefile). A pointer occupies r26:r27 together.
//   r2      VPORTA.DIR value for the next edge.
//   r26:r27 pointer to s_dir[next phase].
//   r4      low byte of &s_dir[modulus], the wrap sentinel.
// All are call-saved or unallocated by avr-gcc under -ffixed; no libgcc
// routine is called, so nothing would restore them from an unreserved build.
register uint8_t s_next_dir __asm__("r2");
register const uint8_t *s_next __asm__("r26");
register uint8_t s_wrap_lo __asm__("r4");

// REQ rising edge, PA6, vector 3 (ch05). ISR_NAKED: avr-gcc's prologue delays
// the first instruction; OUT must come first to meet the 6-cycle budget.
// No SREG save: OUT/SBI/CPSE/RJMP/LDI/LD leave all flags unchanged.
// CPSE instead of CP avoids the flag write that would force a save/restore.
//
// Cycle counts: AVRxt column of DS40002198; 1 cycle = 0.1 us at CLK_PER 10 MHz.
//   Edge to PA3 sinking: 5 (CPUINT finish+push+rjmp) + 1 (OUT)      = 6 cycles
//   Edge to RETI done:   6 + 1 (SBI) + 3 (CPSE) + 2 (LD) + 4 (RETI) = 16 cycles
// Both CPSE paths cost 3 cycles (taken: 2+LDI 1; not taken: 1+RJMP 2), so
// every phase takes the same time. Task 8 measures both on the scope.
//
// SBI is a read-modify-write of VPORTA.INTFLAGS; writing 1 clears any set
// flag (ch14), so no other PA pin may have an edge sense configured.
// Errata DS80000933D: store >=64 then <64 loses the second; OUT avoids ST.
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

// Phase 0, VOTE released. Call only with the PA6 edge disabled.
// s_next points one ahead of s_next_dir so hal_gpio_phase() returns 0.
// s_wrap_lo is unread until hal_gpio_arm() sets it; &s_dir[1] is the value
// already in r26, so the compiler reuses it instead of loading a second one.
static void rewind_phase(void) {
  s_next_dir = 0;
  s_next = &s_dir[1];
  s_wrap_lo = (uint8_t)(uint16_t)&s_dir[1];
}

void hal_gpio_init(void) {
  PORTA.OUT = 0;  // OUT stays 0 forever; DIR drives low or releases.
  PORTA.DIR = 0;

  // PA0 UPDI, PA7 LED and PA3 VOTE are never read, and PA1 SDA and PA2 SCL are
  // not read until hal_twi_init() re-enables their buffers: an input buffer
  // with no reader only draws current. PA6 REQ with no edge sense is disarmed.
  PORTA.PIN0CTRL = PORT_ISC_INPUT_DISABLE_gc;
  PORTA.PIN1CTRL = PORT_ISC_INPUT_DISABLE_gc;
  PORTA.PIN2CTRL = PORT_ISC_INPUT_DISABLE_gc;
  PORTA.PIN3CTRL = PORT_PULLUPEN_bm | PORT_ISC_INPUT_DISABLE_gc;
  PORTA.PIN6CTRL = PORT_PULLUPEN_bm;
  PORTA.PIN7CTRL = PORT_ISC_INPUT_DISABLE_gc;

  PORTA.INTFLAGS = 0xFF;  // Clear any flags set during pin config before sei().
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
  cli();  // Prevent a mid-update edge mixing old and new phase registers.

  s_next_dir = s_dir[phase];
  s_next = &s_dir[phase + 1];  // One ahead of the value in r2.
  s_wrap_lo = (uint8_t)(uint16_t)&s_dir[modulus];

  PORTA.INTFLAGS = PIN6_bm;  // Discard edges seen while disarmed.
  PORTA.PIN6CTRL = PORT_PULLUPEN_bm | PORT_ISC_RISING_gc;

  SREG = sreg;
}

void hal_gpio_disarm(void) {
  const uint8_t sreg = SREG;
  cli();  // Prevent an edge re-driving VOTE after the release below.

  PORTA.PIN6CTRL = PORT_PULLUPEN_bm;
  PORTA.INTFLAGS = PIN6_bm;
  // Errata DS80000933D: a store to an address >= 64 (INTFLAGS) immediately
  // followed by one below 64 (VPORTA.DIR) loses the second.
  _NOP();
  VPORTA.DIR = 0;

  rewind_phase();
  SREG = sreg;
}

void hal_gpio_led(bool on) {
  // Disarmed: DIR is 0 and the ISR cannot run; no guard needed.
  VPORTA.DIR = on ? PIN7_bm : 0;
}

uint8_t hal_gpio_phase(void) {
  // s_next is one phase ahead of the value held in s_next_dir.
  return (uint8_t)(s_next - &s_dir[0]) - 1;
}

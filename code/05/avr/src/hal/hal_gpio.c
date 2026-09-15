#include "hal_gpio.h"

#include <avr/cpufunc.h>
#include <avr/interrupt.h>
#include <avr/io.h>

#include "task/task_sieve.h"

// VOTE (PA3) and LED (PA7) share one VPORTA.DIR byte. Their OUT bits stay 0
// for the life of the program, so a 1 in DIR drives the pin low and a 0 leaves
// it high-impedance and pulled up. 0x88 sinks VOTE and lights the LED.
#define VOTE_LOW_DIR (PIN3_bm | PIN7_bm)

// One byte per phase, each the VPORTA.DIR value that phase needs.
//
// The array is one byte longer than the largest modulus. After reading the
// last phase the handler leaves X pointing one past it, so an element must
// exist there. That keeps X inside the array, and every SRAM address is
// 0x3F00 to 0x3FFF (datasheet ch04), so X's high byte never changes and the
// handler can wrap by reloading the low byte alone.
static uint8_t s_dir[TASK_SIEVE_MODULUS_MAX + 1];

// Three registers the REQ handler owns, kept from the compiler by
// -ffixed-r2 -ffixed-r4 -ffixed-r26 -ffixed-r27 in src/Makefile. Four
// registers in all: a pointer takes r26 and r27 together.
//
//   r2       VPORTA.DIR value the next REQ rising edge writes out.
//   r26:r27  &s_dir[phase after that one].
//   r4       low byte of &s_dir[modulus], where the phase wraps to 0.
//
// The compiler never allocates them, so no other code can corrupt them. They
// are call-saved (r2, r4) or unused by the code avr-gcc emits under -ffixed
// (r26, r27); nothing in this firmware calls a precompiled libgcc routine, so
// nothing restores them from a build that did not reserve them.
register uint8_t s_next_dir __asm__("r2");
register const uint8_t *s_next __asm__("r26");
register uint8_t s_wrap_lo __asm__("r4");

// REQ rising edge on PA6, vector 3 (datasheet ch05).
//
// Hand-written because avr-gcc emits its register-save prologue before the
// first C statement, which delays the pin. ISR_NAKED suppresses that, and the
// first instruction drives PA3.
//
// The handler writes no SREG flag, so it does not save SREG: OUT, SBI, CPSE,
// RJMP, LDI and LD all leave the status register alone. CPSE is the compare
// that costs nothing; CP would have forced a save and restore.
//
// Cycle counts are the AVRxt column of the AVR Instruction Set Manual
// DS40002198, which datasheet ch31 names as this core's reference. At
// CLK_PER 10 MHz one cycle is 0.1 us.
//
//   REQ rising edge to PA3 starting to sink current:
//     CPUINT response, ch11, 4 KB Flash: finish the instruction in
//     progress 1, push the return address 2, rjmp from the vector
//     table 2                                                  5 cycles
//     OUT                                                      1 cycle
//                                                    total     6 cycles = 0.6
//                                                    us
//
//   REQ rising edge to RETI complete:
//     the 6 above                                              6 cycles
//     SBI                                                      1 cycle
//     CPSE taken 2 and LDI 1, or CPSE 1 and RJMP 2             3 cycles
//     LD                                                       2 cycles
//     RETI, 2-byte program counter, ch11                       4 cycles
//                                                    total    16 cycles = 1.6
//                                                    us
//
// Both paths through CPSE cost 3 cycles, so every phase takes the same time,
// wrap or no wrap. Task 8 measures both numbers on the scope.
//
// SBI clears the PA6 interrupt flag. It is a read-modify-write of
// VPORTA.INTFLAGS and writing a 1 clears a flag (ch14), so it also clears any
// other PORTA flag that happens to be set. No other PA pin has an edge sense
// configured, and none may be given one, or its flag would be lost here.
//
// Errata DS80000933D: a store to an address at or above 64 immediately
// followed by a store below 64 loses the second store; the listed work-around
// is to use OUT rather than ST, which is what the first instruction does.
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

void hal_gpio_init(void) {
  // Datasheet ch14: after reset every pin is an input with the output driver
  // off. Make that explicit. OUT stays 0 for the life of the program, so no
  // pin is ever driven high.
  PORTA.OUT = 0;
  PORTA.DIR = 0;

  // PA0 is UPDI. hal_system.c sets SYSCFG0.RSTPINCFG to UPDI, so the UPDI
  // peripheral owns the pin and PORT does not; switching off the PORT digital
  // input buffer removes that buffer's supply current. Datasheet ch14.
  PORTA.PIN0CTRL = PORT_ISC_INPUT_DISABLE_gc;

  // PA1 SDA and PA2 SCL are unused until task 6 enables TWI0.
  PORTA.PIN1CTRL = PORT_ISC_INPUT_DISABLE_gc;
  PORTA.PIN2CTRL = PORT_ISC_INPUT_DISABLE_gc;

  // PA3 VOTE. The pull-up holds the line high while the pin is an input;
  // datasheet ch14 says it is disconnected while the pin is an output, so it
  // never fights the low driver. Nothing reads PA3, so the input buffer is off.
  PORTA.PIN3CTRL = PORT_PULLUPEN_bm | PORT_ISC_INPUT_DISABLE_gc;

  // PA6 REQ: pull-up so an unconnected REQ reads high. ISC is INTDISABLE, the
  // disarmed state; hal_gpio_arm() switches it to RISING. Datasheet ch14 lists
  // PA6 as fully asynchronous, so it senses a pulse shorter than one CLK_PER
  // cycle and imposes no dead time after an interrupt.
  PORTA.PIN6CTRL = PORT_PULLUPEN_bm;

  // PA7 LED, driven low to light it. Nothing reads PA7.
  PORTA.PIN7CTRL = PORT_ISC_INPUT_DISABLE_gc;

  // Datasheet ch14: flags set while the pins were being configured stay set
  // and would fire as soon as sei() runs. Clear all eight.
  PORTA.INTFLAGS = 0xFF;

  // Disarmed at phase 0 with no ring: VOTE released, and the handler is not
  // reachable until hal_gpio_arm() enables the edge.
  s_next_dir = 0;
  s_next = &s_dir[1];
  s_wrap_lo = (uint8_t)(uint16_t)&s_dir[1];
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

  // Re-arming from an armed state is legal, and an edge landing between the
  // three register writes would mix the old phase with the new one.
  const uint8_t sreg = SREG;
  cli();

  // The handler holds the next edge's value in r2 and the pointer one phase
  // ahead of it. phase + 1 is at most the modulus, which is the wrap limit the
  // handler tests before it dereferences the pointer.
  s_next_dir = s_dir[phase];
  s_next = &s_dir[phase + 1];
  s_wrap_lo = (uint8_t)(uint16_t)&s_dir[modulus];

  // Discard any edge seen while disarmed, then let PA6 interrupt.
  PORTA.INTFLAGS = PIN6_bm;
  PORTA.PIN6CTRL = PORT_PULLUPEN_bm | PORT_ISC_RISING_gc;

  SREG = sreg;
}

void hal_gpio_disarm(void) {
  // An edge arriving part-way through would re-drive VOTE after the release
  // below. Hold off interrupts for the four writes.
  const uint8_t sreg = SREG;
  cli();

  PORTA.PIN6CTRL = PORT_PULLUPEN_bm;
  PORTA.INTFLAGS = PIN6_bm;

  // Errata DS80000933D: PORTA.INTFLAGS is at 0x0409 and VPORTA.DIR at 0x0000,
  // and a store to the second can be lost. The NOP is one of the two listed
  // work-arounds, and unlike the other it does not rely on the compiler
  // choosing OUT over ST.
  _NOP();
  VPORTA.DIR = 0;

  SREG = sreg;
}

void hal_gpio_led(bool on) {
  // Disarmed, DIR is 0 and no interrupt can change it, so a plain write needs
  // no guard. VPORTA.DIR is below address 64 and avr-gcc reaches it with OUT,
  // the work-around errata DS80000933D asks for.
  VPORTA.DIR = on ? PIN7_bm : 0;
}

uint8_t hal_gpio_phase(void) {
  // The pointer is one phase ahead of the value in r2, and never sits at
  // s_dir[0]: the handler reloads it and reads through it in one step.
  return (uint8_t)(s_next - &s_dir[0]) - 1;
}

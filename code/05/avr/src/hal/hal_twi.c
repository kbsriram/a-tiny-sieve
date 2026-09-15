#include "hal_twi.h"

#include <avr/interrupt.h>
#include <avr/io.h>

#include "hal_gpio.h"
#include "hal_system.h"
#include "task/task_cmd.h"

// The bytes of the read in progress, taken at the address match so every byte
// of one read, the CRC included, describes the same instant.
static uint8_t s_read[TASK_CMD_READ_MAX];
static uint8_t s_read_len;
static uint8_t s_read_index;
static bool s_read_started;  // At least one byte of this read was sent.
static bool s_write_open;    // A write frame is open and not yet ended.
static volatile bool s_ready;

// STOP or repeated START ends a write frame. task_cmd_end() reports whether it
// held one complete accepted command; the dispatch loop in main.c reads that
// through hal_twi_take_command().
static void end_write_frame(void) {
  if (!s_write_open) {
    return;
  }
  s_write_open = false;
  if (task_cmd_end()) {
    s_ready = true;
  }
}

// TWI0 client, vector 19 (datasheet ch05). Datasheet ch24 sets out the four
// cases this covers: address match writing (S1), address match reading (S2),
// STOP (S3) and collision (S4).
//
// Every byte is acknowledged, whatever the decoder makes of it; the frame's
// outcome reaches the host as the response code of the next read.
//
// SCL is held low from the moment a flag is set until this handler writes
// SCTRLB, so the card decides at its own speed and no byte is ever missed.
// The longest path is the address match of a read after a STATUS, which folds
// 5 bytes into the CRC: about 250 CLK_PER cycles, 25 us at 10 MHz, against the
// 10 us bit period of a 100 kHz bus. Stretching SCL by that is legal I2C, and
// no command arrives while the card is armed, so it cannot delay a REQ edge.
//
// There is no wait loop anywhere in this file: every step is driven by an
// interrupt, so there is nothing to time out. A host that abandons a
// transaction leaves the client waiting for a Start condition, which is what
// COMPTRANS already asks for, and the next Start resynchronises it.
// cppcheck-suppress unusedFunction  ; the vector table calls it.
ISR(TWI0_TWIS_vect) {
  const uint8_t status = TWI0.SSTATUS;

  if (status & TWI_APIF_bm) {
    // A repeated START ends the previous frame without a STOP.
    end_write_frame();

    if (!(status & TWI_AP_bm)) {  // STOP.
      TWI0.SCTRLB = TWI_SCMD_COMPTRANS_gc;
      return;
    }

    if (status & TWI_DIR_bm) {  // The host is about to read.
      s_read_len =
          task_cmd_read(hal_gpio_phase(), hal_system_reset_flags(), s_read);
      s_read_index = 0;
      s_read_started = false;
    } else {
      task_cmd_start();
      s_write_open = true;
    }
    TWI0.SCTRLB = TWI_ACKACT_ACK_gc | TWI_SCMD_RESPONSE_gc;
    return;
  }

  if (status & TWI_DIF_bm) {
    if (status & TWI_DIR_bm) {  // Client transmit.
      // RXACK is the host's answer to the byte before this one, so it only
      // means anything once a byte has gone out; after the address packet it
      // still holds the acknowledge of an earlier transaction.
      if (s_read_started && (status & TWI_RXACK_bm)) {
        TWI0.SCTRLB = TWI_SCMD_COMPTRANS_gc;  // The host NACKed: it is done.
        return;
      }
      // Reading past the end gives 0xFF, the level of an undriven bus, so a
      // host that clocks too far cannot read a stale byte as data.
      TWI0.SDATA = (s_read_index < s_read_len) ? s_read[s_read_index++] : 0xFF;
      s_read_started = true;
      TWI0.SCTRLB = TWI_ACKACT_ACK_gc | TWI_SCMD_RESPONSE_gc;
      return;
    }

    // Client receive. Reading SDATA clears DIF; the acknowledge goes out when
    // SCMD is written. The decoder's verdict is kept for the response code,
    // and the byte is acknowledged either way.
    (void)task_cmd_byte(TWI0.SDATA);
    TWI0.SCTRLB = TWI_ACKACT_ACK_gc | TWI_SCMD_RESPONSE_gc;
    return;
  }

  // Neither flag: a collision or a bus error woke the handler. Both are
  // sticky and clear on a write of 1 (ch24). Wait for the next Start.
  TWI0.SSTATUS = TWI_COLL_bm | TWI_BUSERR_bm;
  TWI0.SCTRLB = TWI_SCMD_COMPTRANS_gc;
}

void hal_twi_init(uint8_t addr) {
  // Datasheet ch14: TWI0 reads SDA and SCL through the PORT input buffers,
  // which hal_gpio_init() disabled while the pins were unused. ISC 0 leaves
  // the buffer on with no pin interrupt.
  //
  // The pull-ups are the only ones on the bus; there is no resistor on the
  // card or the backplane. Each is 20 to 50 kOhm (ch32), so 30 cards give
  // about 1.2 kOhm against their own 300 pF of pin capacitance (ch32, 10 pF
  // per TWI pin): a rise of roughly 0.5 us, against the 5 us half period of a
  // 100 kHz bus. Pulling cards weakens the pull-up and removes their
  // capacitance together, so the rise time barely moves.
  PORTA.PIN1CTRL = PORT_PULLUPEN_bm | PORT_ISC_INTDISABLE_gc;
  PORTA.PIN2CTRL = PORT_PULLUPEN_bm | PORT_ISC_INTDISABLE_gc;

  // Datasheet ch24: SADDR holds the 7-bit address in bits 7:1. Bit 0 would
  // also answer the general call address 0x00; one card per modulus must
  // answer only its own address, so it stays 0.
  TWI0.SADDR = (uint8_t)(addr << 1);

  s_read_len = 0;
  s_read_index = 0;
  s_read_started = false;
  s_write_open = false;
  s_ready = false;

  // Interrupt on every received byte (DIEN), on an address match and on STOP
  // (APIEN with PIEN). Smart mode is left off: the acknowledge must wait for
  // the decoder's answer, not follow automatically from reading SDATA.
  TWI0.SCTRLA = TWI_DIEN_bm | TWI_APIEN_bm | TWI_PIEN_bm | TWI_ENABLE_bm;
}

bool hal_twi_take_command(void) {
  // No cli: the handler only sets this flag and main.c only clears it, so
  // nothing in the main loop disables interrupts while the card is armed.
  if (!s_ready) {
    return false;
  }
  s_ready = false;
  return true;
}

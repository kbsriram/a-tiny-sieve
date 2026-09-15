#include "hal_twi.h"

#include <avr/interrupt.h>
#include <avr/io.h>

#include "hal_gpio.h"
#include "hal_system.h"
#include "task/task_cmd.h"

static uint8_t s_read[TASK_CMD_READ_MAX];  // Snapshot taken at address-match.
static uint8_t s_read_len;
static uint8_t s_read_index;
static bool s_read_started;  // True once the first read byte has gone out.
static bool s_write_open;
static volatile bool s_ready;

// STOP or repeated START ends a write frame.
static void end_write_frame(void) {
  if (!s_write_open) {
    return;
  }
  s_write_open = false;
  if (task_cmd_end()) {
    s_ready = true;
  }
}

// TWI0 client, vector 19 (ch05). Four cases per ch24: address+write (S1),
// address+read (S2), STOP (S3), collision (S4). Every byte is ACKed; the
// outcome reaches the host as the response code of the next read.
//
// SCL is held low from the flag until this handler writes SCTRLB, so no byte is
// ever missed. The longest path, the STATUS CRC over 5 bytes, is about 250
// cycles or 25 us at 10 MHz, against the 10 us bit period of a 100 kHz bus. No
// command arrives while the card is armed, so this cannot delay a REQ edge.
//
// There is no wait loop here, so nothing can time out. An abandoned
// transaction leaves the client waiting for a Start, which is what COMPTRANS
// already asks for, and the next Start resynchronises it.
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
      // RXACK answers the previous byte; it means nothing before the first.
      if (s_read_started && (status & TWI_RXACK_bm)) {
        TWI0.SCTRLB = TWI_SCMD_COMPTRANS_gc;  // Host NACKed: it is done.
        return;
      }
      // Past the end: 0xFF is the idle-bus level, not a stale byte.
      TWI0.SDATA = (s_read_index < s_read_len) ? s_read[s_read_index++] : 0xFF;
      s_read_started = true;
      TWI0.SCTRLB = TWI_ACKACT_ACK_gc | TWI_SCMD_RESPONSE_gc;
      return;
    }

    // Reading SDATA clears DIF; writing SCMD sends the ACK, verdict aside.
    (void)task_cmd_byte(TWI0.SDATA);
    TWI0.SCTRLB = TWI_ACKACT_ACK_gc | TWI_SCMD_RESPONSE_gc;
    return;
  }

  // Collision or bus error (sticky, cleared by writing 1). Wait for next Start.
  TWI0.SSTATUS = TWI_COLL_bm | TWI_BUSERR_bm;
  TWI0.SCTRLB = TWI_SCMD_COMPTRANS_gc;
}

void hal_twi_init(uint8_t addr) {
  // Re-enable PA1/PA2 input buffers disabled in hal_gpio_init(); add pull-ups
  // (the only ones on the bus; no external resistor on the card or backplane).
  PORTA.PIN1CTRL = PORT_PULLUPEN_bm | PORT_ISC_INTDISABLE_gc;
  PORTA.PIN2CTRL = PORT_PULLUPEN_bm | PORT_ISC_INTDISABLE_gc;

  // ch24: SADDR holds the 7-bit address in bits 7:1. Bit 0 would also answer
  // the general call address 0x00, so it stays 0.
  TWI0.SADDR = (uint8_t)(addr << 1);

  s_read_len = 0;
  s_read_index = 0;
  s_read_started = false;
  s_write_open = false;
  s_ready = false;

  // Smart mode off: the ACK must wait for the decoder, not follow from SDATA.
  TWI0.SCTRLA = TWI_DIEN_bm | TWI_APIEN_bm | TWI_PIEN_bm | TWI_ENABLE_bm;
}

bool hal_twi_take_command(void) {
  // The ISR only sets this flag and main.c only clears it, so no cli is needed
  // and the main loop never disables interrupts while the card is armed.
  if (!s_ready) {
    return false;
  }
  s_ready = false;
  return true;
}


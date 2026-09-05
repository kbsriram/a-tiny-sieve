#include "hal_twi.h"

#include <avr/interrupt.h>
#include <avr/io.h>
#include <util/atomic.h>

#define TWI_BUF_SIZE 18

static volatile uint8_t s_rx_buf[TWI_BUF_SIZE];
static volatile uint8_t s_rx_len = 0;
static volatile bool s_cmd_ready = false;

void hal_twi_init(uint8_t addr) {
  TWI0.SADDR = addr << 1;
  // Enable Address/Stop Interrupt, Data Interrupt, and Enable TWI in client mode
  TWI0.SCTRLA = TWI_APIEN_bm | TWI_DIEN_bm | TWI_PIEN_bm | TWI_ENABLE_bm;
}

bool hal_twi_take_command(uint8_t* buffer_out, uint8_t* len_out) {
  if (s_cmd_ready) {
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
      *len_out = s_rx_len;
      for (uint8_t i = 0; i < s_rx_len; i++) {
        buffer_out[i] = s_rx_buf[i];
      }
      s_cmd_ready = false;
    }
    return true;
  }
  return false;
}

ISR(TWI0_TWIS_vect) {
  if (TWI0.SSTATUS & TWI_APIF_bm) {
    if (TWI0.SSTATUS & TWI_AP_bm) {
      // Address Match
      s_rx_len = 0;
      TWI0.SCTRLB = TWI_SCMD_RESPONSE_gc;
    } else {
      // Stop condition
      if (s_rx_len > 0) {
        s_cmd_ready = true;
      }
      TWI0.SCTRLB = TWI_SCMD_COMPTRANS_gc;
    }
  } else if (TWI0.SSTATUS & TWI_DIF_bm) {
    if (TWI0.SSTATUS & TWI_DIR_bm) {
      // Master reading. Not supported.
      TWI0.SCTRLB = TWI_SCMD_COMPTRANS_gc;
    } else {
      // Master writing
      uint8_t d = TWI0.SDATA;
      if (s_rx_len < TWI_BUF_SIZE && !s_cmd_ready) {
        s_rx_buf[s_rx_len++] = d;
      }
      TWI0.SCTRLB = TWI_SCMD_RESPONSE_gc;
    }
  }
}

#pragma once
#include <stdbool.h>

typedef struct {
  bool rtc_tick;
  bool btn_edge;
  bool btn_clicked;
} system_flags_t;

extern volatile system_flags_t sys_flags;

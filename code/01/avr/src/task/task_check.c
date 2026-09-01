#include "task_check.h"

#include "flags.h"

void task_check_process_click(void) {
  sys_flags.btn_clicked = false;
  sys_flags.beep_request = true;
}

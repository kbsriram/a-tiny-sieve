#include <stdio.h>

#include "test_task_beep.h"
#include "test_task_button.h"
#include "test_task_check.h"

int main(void) {
  printf("\nRunning Host Unit Tests\n");
  printf("-------------------------------\n");

  test_task_button();
  test_task_check();
  test_task_beep();

  printf("-------------------------------\n");
  printf("SUCCESS: All tests passed.\n\n");
  return 0;
}

#include <stdio.h>

#include "test_task_button.h"

int main(void) {
  printf("\nRunning Host Unit Tests\n");
  printf("-------------------------------\n");

  test_task_button();

  printf("-------------------------------\n");
  printf("SUCCESS: All tests passed.\n\n");
  return 0;
}

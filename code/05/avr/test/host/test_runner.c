#include <stdio.h>

#include "test_cmd.h"
#include "test_sieve.h"

int main(void) {
  printf("\nRunning Host Unit Tests (build 05)\n");
  printf("--------------------------------------\n");

  test_sieve();
  test_cmd();

  printf("--------------------------------------\n");
  printf("SUCCESS: All tests passed.\n\n");
  return 0;
}

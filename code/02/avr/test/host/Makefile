CC      = gcc

CFLAGS  = -Wall -Wextra -Werror -std=c99 -I../../src -g -DTEST_LIB

# 1. Use all the hardware-agnostic app logic
SRCS_TASK = $(wildcard ../../src/task/*.c)

# 2. Use the host-based mocks and test runners
SRCS_TEST = $(wildcard *.c)

OBJS = $(patsubst ../../src/task/%.c, build/task_%.o, $(SRCS_TASK)) \
       $(patsubst %.c, build/%.o, $(SRCS_TEST))

TARGET = test_runner

.PHONY: all clean test

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^

build/task_%.o: ../../src/task/%.c
	@mkdir -p build
	$(CC) $(CFLAGS) -c $< -o $@

build/%.o: %.c
	@mkdir -p build
	$(CC) $(CFLAGS) -c $< -o $@

# The default 'test' target builds and immediately runs the binary
test: $(TARGET)
	@./$(TARGET)

clean:
	@rm -rf build $(TARGET)

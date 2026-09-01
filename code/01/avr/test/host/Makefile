CC      = gcc

CFLAGS  = -Wall -Wextra -Werror -std=c99 -I../../src -g -DTEST_LIB -MMD -MP

# All build artifacts stay under here, never in ../../src
BUILD   = build

# 1. Use all the hardware-agnostic app logic
SRCS_TASK = $(wildcard ../../src/task/*.c)

# 2. Use the host-based mocks and test runners
SRCS_TEST = $(wildcard *.c)

OBJS = $(patsubst ../../src/%.c,$(BUILD)/src/%.o,$(SRCS_TASK))
OBJS += $(patsubst %.c,$(BUILD)/%.o,$(SRCS_TEST))
DEPS = $(OBJS:.o=.d)

TARGET = $(BUILD)/test_runner

.PHONY: all clean test

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^

$(BUILD)/src/%.o: ../../src/%.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c -o $@ $<

$(BUILD)/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c -o $@ $<

# The default 'test' target builds and immediately runs the binary
test: $(TARGET)
	@./$(TARGET)

clean:
	@rm -rf $(BUILD)

-include $(DEPS)

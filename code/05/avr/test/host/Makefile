CC      = gcc

CFLAGS  = -Wall -Wextra -Werror -std=c99 -I../../src -g -DTEST_LIB

SRCS_TASK = $(wildcard ../../src/task/*.c)
SRCS_TEST = $(wildcard *.c)

OBJS = $(patsubst ../../src/task/%.c, build/%.o, $(SRCS_TASK)) \
       $(patsubst %.c, build/%.o, $(SRCS_TEST))

TARGET = test_runner

.PHONY: all clean test

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^

build/%.o: ../../src/task/%.c
	@mkdir -p build
	$(CC) $(CFLAGS) -c $< -o $@

build/%.o: %.c
	@mkdir -p build
	$(CC) $(CFLAGS) -c $< -o $@

test: $(TARGET)
	@./$(TARGET)

clean:
	@rm -rf build $(TARGET)

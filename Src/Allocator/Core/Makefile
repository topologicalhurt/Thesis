# Makefile to build poly.c for host (Python usage) and RISC-V embedded
# Targets:
#   make              -> build host shared library (libpoly.so)
#   make clean        -> remove build artifacts
#   make riscv        -> build RISC-V static library (libpoly-riscv.a)
#   make riscv-obj    -> build RISC-V object (poly.riscv.o)
# Variables you can override:
#   CC, CFLAGS, LDFLAGS

# Default tools and flags for host build (for Python via ctypes/cffi)
CC      ?= cc
CFLAGS  ?= -O3 -fPIC -std=c11 -Wall -Wextra -Werror
LDFLAGS ?= -shared -lm

SRC        := poly.c
BUILD_DIR  := build
OBJ        := $(BUILD_DIR)/poly.o
OUT        := $(BUILD_DIR)/libpoly.so

.PHONY: all clean riscv

all: $(OUT)

$(BUILD_DIR):
	mkdir -p $@

$(OUT): $(OBJ)
	$(CC) -o $@ $^ $(LDFLAGS)

$(OBJ): $(SRC) poly.h | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -rf $(BUILD_DIR)

# RISC-V cross-compile (override toolchain prefix if needed)
# For bare-metal/embedded, do not use -shared or -fPIC; build a static library or object.
RISCV_PREFIX     ?= riscv64-unknown-elf
RISCV_AR         ?= $(RISCV_PREFIX)-ar
RISCV_CC         ?= $(RISCV_PREFIX)-gcc
RISCV_CFLAGS     ?= -O3 -std=c11 -Wall -Wextra -Werror
RISCV_ARFLAGS    ?= rcs
RISCV_BUILD_DIR  ?= $(BUILD_DIR)/riscv
RISCV_OBJ        := $(RISCV_BUILD_DIR)/poly.riscv.o
RISCV_OUT        := $(RISCV_BUILD_DIR)/libpoly-riscv.a

riscv: $(RISCV_OUT)

riscv-obj: $(RISCV_OBJ)

$(RISCV_BUILD_DIR):
	mkdir -p $@

$(RISCV_OBJ): $(SRC) poly.h | $(RISCV_BUILD_DIR)
	$(RISCV_CC) $(RISCV_CFLAGS) -c $< -o $@

$(RISCV_OUT): $(RISCV_OBJ)
	$(RISCV_AR) $(RISCV_ARFLAGS) $@ $^
	@echo "Built $@ (static library for embedded RISC-V)"

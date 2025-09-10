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
CFLAGS  ?= -O3 -fPIC -std=c11 -Wall -Wextra -Werror -MMD -MP
LDFLAGS ?= -shared -lm

# Build settings
BUILD_DIR       := ../build
RISCV_BUILD_DIR := $(BUILD_DIR)/riscv

# Discover libraries by subdirectories: libs/<name>/*.c -> lib<name>.*
SUBDIRS   := $(filter-out %build%/ %riscv%/, $(wildcard */))

# Keep only subdirs that have at least one .c source
LIBS      := $(foreach d,$(SUBDIRS),$(if $(wildcard $(d)*.c),$(patsubst %/,%,$(d)),))
HOST_OUTS := $(addprefix $(BUILD_DIR)/lib,$(addsuffix .so,$(LIBS)))
RV_OUTS   := $(addprefix $(RISCV_BUILD_DIR)/lib,$(addsuffix .a,$(LIBS)))

.PHONY: all clean riscv riscv-obj

all: $(HOST_OUTS)

$(BUILD_DIR):
	mkdir -p $@

$(RISCV_BUILD_DIR): | $(BUILD_DIR)
	mkdir -p $@

clean:
	rm -rf $(BUILD_DIR)

# RISC-V cross-compile (override toolchain prefix if needed)
# For bare-metal/embedded, do not use -shared or -fPIC; build a static library or object.
RISCV_PREFIX     ?= riscv32-unknown-elf
RISCV_AR         ?= $(RISCV_PREFIX)-ar
RISCV_CC         ?= $(RISCV_PREFIX)-gcc
RISCV_CFLAGS     ?= -O3 -std=c11 -Wall -Wextra -Werror -MMD -MP
RISCV_ARFLAGS    ?= rcs
RISCV_BUILD_DIR  ?= $(BUILD_DIR)/riscv

riscv: $(RV_OUTS)

# Template to generate per-library rules
define LIB_template
SRC_$(1) := $(wildcard $(1)/*.c)
OBJ_$(1) := $$(patsubst $(1)/%.c,$(BUILD_DIR)/$(1)/%.o,$$(SRC_$(1)))
DEPS_$(1) := $$(OBJ_$(1):.o=.d)

RISCV_OBJ_$(1) := $$(patsubst $(1)/%.c,$(RISCV_BUILD_DIR)/$(1)/%.riscv.o,$$(SRC_$(1)))
RISCV_DEPS_$(1) := $$(RISCV_OBJ_$(1):.o=.d)

$(BUILD_DIR)/$(1): | $(BUILD_DIR)
	mkdir -p $$@

$(RISCV_BUILD_DIR)/$(1): | $(RISCV_BUILD_DIR)
	mkdir -p $$@

$(BUILD_DIR)/$(1)/%.o: $(1)/%.c | $(BUILD_DIR)/$(1)
	$$(CC) $$(CFLAGS) -c $$< -o $$@

$(RISCV_BUILD_DIR)/$(1)/%.riscv.o: $(1)/%.c | $(RISCV_BUILD_DIR)/$(1)
	$$(RISCV_CC) $$(RISCV_CFLAGS) -c $$< -o $$@

$(BUILD_DIR)/lib$(1).so: $$(OBJ_$(1)) | $(BUILD_DIR)
	$$(CC) -o $$@ $$^ $$(LDFLAGS)

$(RISCV_BUILD_DIR)/lib$(1).a: $$(RISCV_OBJ_$(1)) | $(RISCV_BUILD_DIR)
	$$(RISCV_AR) $$(RISCV_ARFLAGS) $$@ $$^
	@echo "Built $$@ (static library for embedded RISC-V)"
endef

$(foreach L,$(LIBS),$(eval $(call LIB_template,$(L))))

riscv-obj: $(foreach L,$(LIBS),$$(RISCV_OBJ_$(L)))

# Auto-include dependency files if present
-include $(foreach L,$(LIBS),$$(DEPS_$(L)))
-include $(foreach L,$(LIBS),$$(RISCV_DEPS_$(L)))

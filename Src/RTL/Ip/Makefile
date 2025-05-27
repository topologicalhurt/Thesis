# ── user-configurable knobs ─────────────────────────────────────────
MDIR       ?= $(shell git rev-parse --show-toplevel)/bin/verilator
VFLAGS     ?= -Wall -Wno-fatal
CXXFLAGS   ?= -std=c++17 -O2

# List of sub-directories to skip when collecting HDL
EXCLDIRS   := fft

# ── derived variables ──────────────────────────────────────────────
# Build a find(1) expression that prunes excluded dirs
PRUNE      := $(foreach d,$(EXCLDIRS),-path ./$(d) -prune -o)
SRCS       := $(shell find . $(PRUNE) -type f \( -name '*.v' -o -name '*.sv' \) -print)
INCDIRS    := +incdir+.

# Tell Verilator to put all generated files into $(MDIR)
VERILATE   = verilator $(VFLAGS) --Mdir $(MDIR) --cc $(SRCS) --exe \
             -CFLAGS "$(CXXFLAGS)" $(INCDIRS)

# ── targets ────────────────────────────────────────────────────────
all: build

build: $(SRCS)
	$(VERILATE)
	$(MAKE) -C $(MDIR)

run: build
	./$(MDIR)

view: run
	gtkwave dump.vcd &

clean:
	rm -rf $(MDIR) logs *.vcd

.PHONY: all build run view clean

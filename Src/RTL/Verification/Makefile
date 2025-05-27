# Makefile for Audio Processor Verification
# Author: Generated for PYNQ-Z2 DEMO Verification

# Simulator selection (can be overridden)
SIM ?= verilator

# File paths
TB_TOP = buf_audio_in_tb
DUT_PATH = ../In
DUT_FILE = $(DUT_PATH)/buf_audio_in.sv
DUT_HEADER = $(DUT_PATH)/buf_audio_in.svh
TB_FILE = ./In/buf_audio_in_tb.sv

# Simulation parameters
NUM_CHANNELS ?= 8
BUFFER_DEPTH ?= 4
AUDIO_WIDTH ?= 24
I2S_WIDTH ?= 24

# Compile flags
VLOG_FLAGS = -sv -timescale=1ns/1ps
ELAB_FLAGS =
SIM_FLAGS = -R

# Default target
all: clean compile elaborate simulate

# Xsim targets
xsim_compile:
	@echo "Compiling with Xsim..."
	xvlog $(VLOG_FLAGS) $(DUT_HEADER) $(DUT_FILE) $(TB_FILE)

xsim_elaborate:
	@echo "Elaborating with Xsim..."
	xelab $(ELAB_FLAGS) $(TB_TOP) -s $(TB_TOP)_sim

xsim_simulate:
	@echo "Running simulation with Xsim..."
	xsim $(TB_TOP)_sim $(SIM_FLAGS)

# Modelsim/Questasim targets
modelsim_compile:
	@echo "Compiling with Modelsim/Questa..."
	vlog $(VLOG_FLAGS) $(DUT_HEADER) $(DUT_FILE) $(TB_FILE)

modelsim_elaborate:
	@echo "Elaborating with Modelsim/Questa..."
	# No separate elaboration step needed for Modelsim

modelsim_simulate:
	@echo "Running simulation with Modelsim/Questa..."
	vsim -c -do "run -all; quit" $(TB_TOP)

# VCS targets
vcs_compile:
	@echo "Compiling with VCS..."
	vcs $(VLOG_FLAGS) $(DUT_HEADER) $(DUT_FILE) $(TB_FILE) -o $(TB_TOP)_sim

vcs_simulate:
	@echo "Running simulation with VCS..."
	./$(TB_TOP)_sim

# Verilator targets
verilator_compile:
	@echo "Compiling with Verilator..."
	verilator -Wall --binary --assert --timing $(DUT_FILE) $(TB_FILE) --top-module $(TB_TOP)

verilator_simulate:
	@echo "Running simulation with Verilator..."
	./obj_dir/V$(TB_TOP)

verilator_lint:
	@echo "Linting with Verilator..."
	verilator --lint-only -sv $(DUT_FILE) --top-module buf_audio_in

# Icarus Verilog targets
iverilog_compile:
	@echo "Compiling with Icarus Verilog..."
	iverilog -g2012 -o $(TB_TOP)_sim $(DUT_HEADER) $(DUT_FILE) $(TB_FILE)

iverilog_simulate:
	@echo "Running simulation with Icarus Verilog..."
	vvp $(TB_TOP)_sim

# Generic targets that dispatch to simulator-specific targets
compile:
ifeq ($(SIM),verilator)
	$(MAKE) verilator_compile
else ifeq ($(SIM),iverilog)
	$(MAKE) iverilog_compile
else ifeq ($(SIM),xsim)
	$(MAKE) xsim_compile
else ifeq ($(SIM),modelsim)
	$(MAKE) modelsim_compile
else ifeq ($(SIM),questa)
	$(MAKE) modelsim_compile
else ifeq ($(SIM),vcs)
	$(MAKE) vcs_compile
else
	@echo "Unknown simulator: $(SIM)"
	@echo "Supported simulators: verilator, iverilog, xsim, modelsim, questa, vcs"
	@exit 1
endif

elaborate:
ifeq ($(SIM),verilator)
	@echo "Verilator elaboration included in compile step"
else ifeq ($(SIM),iverilog)
	@echo "Icarus Verilog elaboration included in compile step"
else ifeq ($(SIM),xsim)
	$(MAKE) xsim_elaborate
else ifeq ($(SIM),modelsim)
	$(MAKE) modelsim_elaborate
else ifeq ($(SIM),questa)
	$(MAKE) modelsim_elaborate
else ifeq ($(SIM),vcs)
	@echo "VCS elaboration included in compile step"
endif

simulate:
ifeq ($(SIM),verilator)
	$(MAKE) verilator_simulate
else ifeq ($(SIM),iverilog)
	$(MAKE) iverilog_simulate
else ifeq ($(SIM),xsim)
	$(MAKE) xsim_simulate
else ifeq ($(SIM),modelsim)
	$(MAKE) modelsim_simulate
else ifeq ($(SIM),questa)
	$(MAKE) modelsim_simulate
else ifeq ($(SIM),vcs)
	$(MAKE) vcs_simulate
endif

# Quick run target
run: all

# Lint only
lint: verilator_lint

# View waveforms (assumes VCD file generated)
waves:
	@if [ -f buf_audio_in_tb.vcd ]; then \
		echo "Opening waveform viewer..."; \
		gtkwave buf_audio_in_tb.vcd &; \
	else \
		echo "VCD file not found. Run simulation first."; \
	fi

# Clean generated files
clean:
	@echo "Cleaning verification files..."
	rm -rf xsim.dir
	rm -f *.log *.jou *.pb
	rm -f *.vcd *.wdb
	rm -f *.vstf *.wlf
	rm -f work/
	rm -f transcript
	rm -f modelsim.ini
	rm -f $(TB_TOP)_sim
	rm -rf obj_dir/
	rm -f ucli.key
	rm -f *.vpd *.fsdb
	rm -f csrc/
	rm -f simv*
	@echo "Clean completed."

# Help target
help:
	@echo "Audio In Verification Makefile"
	@echo "======================================"
	@echo "Available targets:"
	@echo "  all         - Clean, compile, elaborate, and simulate (default)"
	@echo "  compile     - Compile source files"
	@echo "  elaborate   - Elaborate design"
	@echo "  simulate    - Run simulation"
	@echo "  run         - Same as 'all'"
	@echo "  lint        - Run lint checking with Verilator"
	@echo "  waves       - Open waveform viewer (gtkwave)"
	@echo "  clean       - Remove generated files"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "Simulator Selection:"
	@echo "  SIM=verilator - Use Verilator (default)"
	@echo "  SIM=iverilog  - Use Icarus Verilog"
	@echo "  SIM=xsim      - Use Xilinx Vivado Simulator"
	@echo "  SIM=modelsim  - Use Mentor ModelSim"
	@echo "  SIM=questa    - Use Mentor QuestaSim"
	@echo "  SIM=vcs       - Use Synopsys VCS"
	@echo ""
	@echo "Parameters:"
	@echo "  NUM_CHANNELS=$(NUM_CHANNELS)  - Number of audio channels"
	@echo "  BUFFER_DEPTH=$(BUFFER_DEPTH)  - Buffer depth per channel"
	@echo "  AUDIO_WIDTH=$(AUDIO_WIDTH)   - Audio sample width"
	@echo "  I2S_WIDTH=$(I2S_WIDTH)     - I2S data width"
	@echo ""
	@echo "Example usage:"
	@echo "  make SIM=xsim NUM_CHANNELS=16"
	@echo "  make lint"
	@echo "  make waves"

.PHONY: all compile elaborate simulate run lint waves clean help
.PHONY: xsim_compile xsim_elaborate xsim_simulate
.PHONY: modelsim_compile modelsim_elaborate modelsim_simulate
.PHONY: vcs_compile vcs_simulate verilator_lint

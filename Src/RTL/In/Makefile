# Makefile for RTL/In audio processing modules

# Variables
VERILATOR = verilator
PYTHON = python3
SV_FILES = $(wildcard *.sv)
SVH_FILES = buf_audio_in.svh
PY_FILES = i2s_mono_stereo_wrapper.py

# Default parameters
STEREO ?= true
N_CHANNELS ?= 24
AUDIO_WIDTH ?= 24
I2S_WIDTH ?= 24

all: check_syntax compile_check

# Syntax check for SystemVerilog files using Verilator
check_syntax:
	@echo "Checking SystemVerilog syntax with Verilator..."
	@for file in $(SV_FILES); do \
		echo "Linting $$file..."; \
		$(VERILATOR) --lint-only -sv -I. -I.. $$file || exit 1; \
	done
	@echo "Syntax check completed successfully."

# Generate wrapper files using Python script (WARNING: OVERWRITES buf_audio_in.sv and buf_audio_in.svh)
generate_wrapper:
	@echo "WARNING: This will OVERWRITE buf_audio_in.sv and buf_audio_in.svh!"
	@echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
	@sleep 5
	@echo "Generating I2S wrapper with parameters:"
	@echo "  Stereo: $(STEREO)"
	@echo "  Channels: $(N_CHANNELS)"
	@echo "  Audio Width: $(AUDIO_WIDTH)"
	@echo "  I2S Width: $(I2S_WIDTH)"
	PYTHONPATH=/home/tophurt/Desktop/Thesis/Src $(PYTHON) $(PY_FILES) -s $(STEREO) -n $(N_CHANNELS) -aw $(AUDIO_WIDTH) -i2sw $(I2S_WIDTH)

# Generate wrapper files without warning (for automated use)
generate_wrapper_force:
	@echo "Force generating I2S wrapper with parameters:"
	@echo "  Stereo: $(STEREO)"
	@echo "  Channels: $(N_CHANNELS)"
	@echo "  Audio Width: $(AUDIO_WIDTH)"
	@echo "  I2S Width: $(I2S_WIDTH)"
	PYTHONPATH=/home/tophurt/Desktop/Thesis/Src $(PYTHON) $(PY_FILES) -s $(STEREO) -n $(N_CHANNELS) -aw $(AUDIO_WIDTH) -i2sw $(I2S_WIDTH)

# Additional Verilator targets
lint_detailed:
	@echo "Running detailed Verilator lint..."
	@for file in $(SV_FILES); do \
		echo "Detailed linting $$file..."; \
		$(VERILATOR) -Wall --lint-only -sv -I. -I.. $$file || exit 1; \
	done

compile_check:
	@echo "Testing compilation with Verilator..."
	@for file in $(SV_FILES); do \
		echo "Testing compilation of $$file..."; \
		$(VERILATOR) --cc -sv -I. -I.. $$file || exit 1; \
	done

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	rm -rf obj_dir/
	rm -f *.log
	rm -f *.jou
	@echo "Clean completed."

# Help target
help:
	@echo "RTL/In Audio Processing Makefile"
	@echo "================================"
	@echo "Available targets:"
	@echo "  all                   - Run syntax check only (default, safe)"
	@echo "  check_syntax          - Check SystemVerilog syntax with Verilator"
	@echo "  lint_detailed         - Run detailed Verilator lint with all warnings"
	@echo "  compile_check         - Test compilation without building executable"
	@echo "  generate_wrapper      - Generate I2S wrapper (WARNING: overwrites files!)"
	@echo "  generate_wrapper_force- Generate wrapper without confirmation"
	@echo "  clean                 - Remove generated files"
	@echo "  help                  - Show this help message"
	@echo ""
	@echo "Tools used:"
	@echo "  Verilator        - SystemVerilog linting and syntax checking"
	@echo "  Python3          - Wrapper generation script"
	@echo ""
	@echo "Parameters:"
	@echo "  STEREO=true/false    - Enable stereo mode (default: true)"
	@echo "  N_CHANNELS=N         - Number of audio channels (default: 24)"
	@echo "  AUDIO_WIDTH=N        - Audio bit width (default: 24)"
	@echo "  I2S_WIDTH=N          - I2S bit width (default: 24)"
	@echo ""
	@echo "Example usage:"
	@echo "  make                                    # Basic syntax check and wrapper generation"
	@echo "  make STEREO=false N_CHANNELS=16         # Custom parameters"
	@echo "  make lint_detailed                      # Detailed linting"
	@echo "  make compile_check                      # Test compilation"

.PHONY: all check_syntax lint_detailed compile_check generate_wrapper generate_wrapper_force clean help

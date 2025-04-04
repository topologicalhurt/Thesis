# PYNQ-Z2 Setup Guide for LLAC Audio System

This guide explains how to set up and run the LLAC Audio System on a PYNQ-Z2 board.

## Prerequisites

- PYNQ-Z2 board with the latest PYNQ image (v2.7+) installed
- Vivado 2020.2 or newer for bitstream generation
- USB microphone or line-in audio source
- Speakers or headphones for output

## Project Setup

### 1. Generate the Bitstream

1. Create a new Vivado project targeting the PYNQ-Z2 board
2. Add all the SystemVerilog files from the `Src/RTL` directory to your project
3. Set `llac_audio_system_top.sv` as the top-level module
4. Create an XDC constraints file with the following:

```
# Clock constraints
create_clock -period 10.000 -name clk_100mhz [get_ports clk_100mhz]
create_clock -period 40.690 -name clk_audio [get_ports clk_audio]

# Audio Pins
set_property -dict {PACKAGE_PIN H5 IOSTANDARD LVCMOS33} [get_ports i2s_mclk]
set_property -dict {PACKAGE_PIN F4 IOSTANDARD LVCMOS33} [get_ports i2s_bclk]
set_property -dict {PACKAGE_PIN F5 IOSTANDARD LVCMOS33} [get_ports i2s_lrclk]
set_property -dict {PACKAGE_PIN D4 IOSTANDARD LVCMOS33} [get_ports i2s_sdata_in]
set_property -dict {PACKAGE_PIN E5 IOSTANDARD LVCMOS33} [get_ports i2s_sdata_out]

# I2C pins for codec configuration
set_property -dict {PACKAGE_PIN E6 IOSTANDARD LVCMOS33} [get_ports i2c_scl]
set_property -dict {PACKAGE_PIN D6 IOSTANDARD LVCMOS33} [get_ports i2c_sda]

# Status LEDs
set_property -dict {PACKAGE_PIN R14 IOSTANDARD LVCMOS33} [get_ports {leds[0]}]
set_property -dict {PACKAGE_PIN P14 IOSTANDARD LVCMOS33} [get_ports {leds[1]}]
set_property -dict {PACKAGE_PIN N16 IOSTANDARD LVCMOS33} [get_ports {leds[2]}]
set_property -dict {PACKAGE_PIN M14 IOSTANDARD LVCMOS33} [get_ports {leds[3]}]
```

5. Create a block design with the Zynq PS and your top module
   - Add the Zynq PS (ZYNQ7 Processing System)
   - Configure the PS to enable the HP0 port for AXI memory access
   - Configure the PS to enable the AXI-Lite General Purpose port
   - Configure the PS to generate the FCLK0 (100MHz) and FCLK1 (audio clock)
   - Add an IRQ connection from your top module to the PS
   - Connect the AXI interfaces, clocks, and reset signals
   - Add the I2S pins as external ports

6. Generate the bitstream:
   - Validate the design
   - Create HDL wrapper
   - Generate bitstream
   - Export hardware (include bitstream)

### 2. Prepare the PYNQ Board

1. Copy the generated bitstream (`llac_audio_system.bit`) and TCL files to your PYNQ-Z2 board
2. Copy the `llac_audio_passthrough.py` script to your PYNQ-Z2 board
3. Ensure the PYNQ board is connected to power and has network access

### 3. Install Required Dependencies

Connect to your PYNQ board via SSH or open a Jupyter notebook and execute:

```python
!pip install matplotlib numpy scipy
```

## Running the Audio Passthrough Demo

1. Connect headphones/speakers to the audio out jack of the PYNQ-Z2
2. Connect a microphone to the audio in jack (or use the onboard microphone if available)
3. Run the passthrough demo:

```bash
python llac_audio_passthrough.py
```

4. Follow the on-screen menu to select options:
   - Option 1: Start microphone to speaker passthrough
   - Option 2: Play 440Hz test tone
   - Option 3: Play 880Hz test tone
   - Option 4: Check system status
   - Option 5: Reset cores
   - Press 'q' to quit

## Troubleshooting

### Audio Not Working

- Check that the audio codec is properly configured by verifying the status register
- Ensure the microphone is connected and working
- Check the volume settings on your PYNQ board

### Bitstream Won't Load

- Make sure the bitstream path in the Python script matches your file location
- Verify that the bitstream was generated for the correct board
- Check connection permissions (may need to run with sudo)

### System Errors

The status register provides error information:
- Bit 0-3: Core status (1 = active, 0 = idle)
- Bit 4: FIFO overflow occurred
- Bit 5: FIFO underflow occurred
- Bit 6-7: Reserved for system errors

Run this command to see the status:

```python
print(f"Core status: 0x{llac.get_core_status():08x}")
```

## Extending the System

To add custom audio processing:

1. Modify the passthrough function in `llac_audio_passthrough.py` to include your DSP code
2. For more complex processing, create new audio core modules in SystemVerilog and add them to the bitstream
3. Expose any control parameters via the AXI-Lite interface

## References

- [PYNQ Documentation](http://www.pynq.io/documentation.html)
- [ADAU1761 Datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ADAU1761.pdf)
- [Zynq-7000 Technical Reference Manual](https://www.xilinx.com/support/documentation/user_guides/ug585-Zynq-7000-TRM.pdf)

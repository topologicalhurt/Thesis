# Audio Processor Verification

This directory contains verification testbenches for the audio processing modules.

## Files

- `buf_audio_in_tb.sv` - Testbench for the I2S audio buffer on the input side
- `Makefile` - Build system for running simulations with various simulators
- `README.md` - This documentation file

## Audio Processor Features Verified

### Core Functionality
- ✅ I2S audio data reception (24-bit samples)
- ✅ Clock domain crossing from I2S to system clock
- ✅ N-way parallel audio channel distribution (configurable, default 24 channels)
- ✅ Clean audio buffering with configurable depth (default 4 samples per channel)
- ✅ Buffer overflow detection and management

### Signal Outputs
- `audio_channel_out[N-1:0]` - N parallel buffered audio channels (each 24-bit)
- `sample_valid` - Pulses when new samples are distributed to all channels
- `buffer_ready` - Indicates clean buffered data is available across all channels
- `buffer_full` - Warning signal for buffer overflow conditions

### Buffering Architecture
Each of the N audio channels has its own circular buffer with:
- **Write pointer** - Points to next location for incoming samples
- **Read pointer** - Points to current output sample
- **Buffer count** - Tracks how many samples are stored
- **Valid flag** - Indicates if channel has valid buffered data

## Running Simulations

### Quick Start
```bash
# Run with default simulator (Vivado XSim)
make

# Run with specific simulator
make SIM=modelsim
make SIM=questa
make SIM=vcs

# Run with custom parameters
make NUM_CHANNELS=16 BUFFER_DEPTH=8
```

### Individual Steps
```bash
# Compile only
make compile

# Lint check
make lint

# View waveforms (after simulation)
make waves

# Clean up
make clean
```

### Supported Simulators
- **Xilinx Vivado XSim** (default) - `SIM=xsim`
- **Mentor ModelSim** - `SIM=modelsim`
- **Mentor QuestaSim** - `SIM=questa`
- **Synopsys VCS** - `SIM=vcs`
- **Verilator** (lint only) - `make lint`

## Test Cases

The testbench includes comprehensive verification:

1. **Basic I2S Reception** - Verifies correct sample capture and distribution
2. **Multi-Channel Distribution** - Tests parallel distribution to N channels
3. **Buffer Management** - Tests circular buffering and overflow handling
4. **Clock Domain Crossing** - Verifies safe I2S to system clock transfer
5. **Reset Behavior** - Tests proper reset and initialization
6. **Pattern Testing** - Validates data integrity with known patterns

## Waveform Analysis

The testbench generates VCD files for waveform analysis:
```bash
# Generate waveforms and view
make
make waves
```

Key signals to observe:
- `i2s_*` - I2S interface timing
- `sample_valid` - Sample distribution timing
- `buffer_ready` - Buffer status
- `audio_channel_out[*]` - Parallel channel outputs

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `NUM_AUDIO_CHANNELS` | 24 | Number of parallel audio output channels |
| `BUFFER_DEPTH` | 4 | Samples buffered per channel |
| `AUDIO_WIDTH` | 24 | Bit width of audio samples |
| `I2S_WIDTH` | 24 | Bit width of I2S data |

## Performance Characteristics

- **Latency**: 2-4 system clock cycles from I2S sample complete to `sample_valid`
- **Throughput**: Supports full I2S sample rate with parallel N-channel distribution
- **Buffer Depth**: Configurable per-channel buffering prevents data loss
- **Clock Domains**: Safe crossing with 2-stage synchronizer

## Debugging Tips

1. **Sample Timing**: Check `i2s_lrclk` transitions align with expected sample boundaries
2. **Buffer Status**: Monitor `buffer_full` for overflow conditions
3. **Channel Distribution**: Verify all `audio_channel_out[]` receive identical data
4. **Clock Relationships**: Ensure I2S bit clock is properly synchronized

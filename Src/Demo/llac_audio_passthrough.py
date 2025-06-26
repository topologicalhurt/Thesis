#!/usr/bin/env python3
"""
------------------------------------------------------------------------
Filename: 	llac_audio_passthrough.py

Project:	LLAC, intelligent hardware scheduler targeting common audio signal chains.

For more information see the repository: https://github.com/topologicalhurt/Thesis

Purpose:	N/A

Author: topologicalhurt csin0659@uni.sydney.edu.au

------------------------------------------------------------------------
Copyright (C) 2025, LLAC project LLC

This file is a part of the None module
None
LICENSE:     GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
As defined by GNU GPL 3.0 https://www.gnu.org/licenses/gpl-3.0.html

A copy of this license is included at the root directory. It should've been provided to you
Otherwise please consult: https://github.com/topologicalhurt/Thesis/blob/main/LICENSE
------------------------------------------------------------------------
"""


import time
import numpy as np
from pynq import Overlay
from pynq.lib.audio import Audio
from pynq.ps import Clocks

class LLACAudioPassthrough:
    """
    LLAC Audio System wrapper for PYNQ-Z2 with simple audio passthrough
    """

    def __init__(self, bitstream_path='llac_audio_system.bit'):
        """
        Initialize the LLAC Audio System

        Parameters:
        -----------
        bitstream_path : str
            Path to the bitstream file
        """
        # Load bitstream
        print('Loading LLAC Audio System overlay...')
        self.overlay = Overlay(bitstream_path)

        # Initialize audio driver
        print('Initializing audio subsystem...')
        self.audio = Audio()

        # Get handles to IP cores from the overlay
        self.llac_top = self.overlay.llac_audio_system_top_0

        # Define control register addresses
        self.CTRL_REG_ADDR = 0x00
        self.STATUS_REG_ADDR = 0x04
        self.CORE_CTRL_REG_ADDR = 0x08
        self.INT_ENABLE_REG_ADDR = 0x10
        self.INT_CLEAR_REG_ADDR = 0x18
        self.CORE_SELECT_REG_ADDR = 0x1C

        # Define control bits
        self.CTRL_GLOBAL_PAUSE = 0
        self.CTRL_GLOBAL_STOP = 1
        self.CTRL_GLOBAL_RESUME = 2
        self.CTRL_INT_ENABLE = 3

        # Define core control bits
        self.CORE_CTRL_PAUSE = 0
        self.CORE_CTRL_STOP = 1
        self.CORE_CTRL_RESUME = 2

        # Initialize the system
        self.init_audio_system()

    def init_audio_system(self):
        """Initialize the audio system and prepare for streaming"""
        # Configure audio codec
        print('Configuring audio codec...')
        self.audio.configure()

        # Enable global interrupt
        self.write_reg(self.CTRL_REG_ADDR, 1 << self.CTRL_INT_ENABLE)

        # Enable all cores
        self.resume_all_cores()

        # Wait for system to become ready
        time.sleep(0.1)
        status = self.read_reg(self.STATUS_REG_ADDR)
        print(f'Audio system status: 0x{status:08x}')

        print('LLAC Audio System initialized and ready')

    def write_reg(self, offset, value):
        """Write to a register in the control interface"""
        self.llac_top.write(offset, value)

    def read_reg(self, offset):
        """Read from a register in the control interface"""
        return self.llac_top.read(offset)

    def pause_core(self, core_id=0):
        """Pause a specific audio core"""
        # Select the core
        self.write_reg(self.CORE_SELECT_REG_ADDR, core_id)
        # Send pause command
        self.write_reg(self.CORE_CTRL_REG_ADDR, 1 << self.CORE_CTRL_PAUSE)

    def stop_core(self, core_id=0):
        """Stop a specific audio core"""
        # Select the core
        self.write_reg(self.CORE_SELECT_REG_ADDR, core_id)
        # Send stop command
        self.write_reg(self.CORE_CTRL_REG_ADDR, 1 << self.CORE_CTRL_STOP)

    def resume_core(self, core_id=0):
        """Resume a specific audio core"""
        # Select the core
        self.write_reg(self.CORE_SELECT_REG_ADDR, core_id)
        # Send resume command
        self.write_reg(self.CORE_CTRL_REG_ADDR, 1 << self.CORE_CTRL_RESUME)

    def pause_all_cores(self):
        """Pause all audio cores"""
        self.write_reg(self.CTRL_REG_ADDR, 1 << self.CTRL_GLOBAL_PAUSE)

    def stop_all_cores(self):
        """Stop all audio cores"""
        self.write_reg(self.CTRL_REG_ADDR, 1 << self.CTRL_GLOBAL_STOP)

    def resume_all_cores(self):
        """Resume all audio cores"""
        self.write_reg(self.CTRL_REG_ADDR, 1 << self.CTRL_GLOBAL_RESUME)

    def get_core_status(self):
        """Get the status of all cores"""
        return self.read_reg(self.STATUS_REG_ADDR)

    def passthrough_from_mic(self, duration=10):
        """
        Record audio from microphone and play it back immediately

        Parameters:
        -----------
        duration : int
            Duration in seconds for the passthrough
        """
        print(f'Starting audio passthrough for {duration} seconds...')

        # Start audio passthrough using the audio driver
        self.audio.start()

        # Wait for the specified duration
        try:
            for i in range(duration):
                time.sleep(1)
                print(f'Passthrough running... {i+1}/{duration} seconds')
                # Check for any interrupt or error conditions
                status = self.get_core_status()
                if status & 0xF0:  # Check upper bits for errors
                    print(f'Warning: Detected issue in audio core, status: 0x{status:08x}')

        except KeyboardInterrupt:
            print('Passthrough interrupted by user')

        finally:
            # Stop the audio
            self.audio.stop()
            print('Audio passthrough stopped')

    def play_sine_wave(self, freq=440, duration=5):
        """
        Generate and play a sine wave through the audio system

        Parameters:
        -----------
        freq : int
            Frequency of the sine wave in Hz
        duration : int
            Duration in seconds
        """
        print(f'Playing {freq}Hz sine wave for {duration} seconds...')

        # Generate sine wave
        sample_rate = 48000
        t = np.linspace(0, duration, sample_rate * duration, False)
        audio_data = 0.5 * np.sin(2 * np.pi * freq * t)

        # Convert to the format expected by the audio driver
        audio_data_stereo = np.column_stack((audio_data, audio_data))

        # Play the audio
        self.audio.play(audio_data_stereo)

        # Wait for playback to complete
        time.sleep(duration + 0.5)
        print('Playback completed')

    def cleanup(self):
        """Clean up and release resources"""
        print('Shutting down LLAC Audio System...')
        self.stop_all_cores()
        time.sleep(0.1)
        self.audio.stop()
        print('LLAC Audio System shut down successfully')


def main():
    """Main function to demonstrate audio passthrough"""
    print('LLAC Audio System - Passthrough Demo')
    print('====================================')

    try:
        # Initialize the LLAC Audio system
        llac = LLACAudioPassthrough()

        # Print system info
        clk_rate = Clocks.fclk0_mhz
        print(f'System clock rate: {clk_rate} MHz')

        # Menu for the demo
        while True:
            print('\nOptions:')
            print('1. Start microphone to speaker passthrough')
            print('2. Play 440Hz test tone')
            print('3. Play 880Hz test tone')
            print('4. Check system status')
            print('5. Reset cores')
            print('q. Quit')

            choice = input('Select an option: ')

            if choice == '1':
                llac.passthrough_from_mic(10)
            elif choice == '2':
                llac.play_sine_wave(440, 3)
            elif choice == '3':
                llac.play_sine_wave(880, 3)
            elif choice == '4':
                status = llac.get_core_status()
                print(f'Core status: 0x{status:08x}')
            elif choice == '5':
                llac.stop_all_cores()
                time.sleep(0.1)
                llac.resume_all_cores()
                print('Cores reset successfully')
            elif choice.lower() == 'q':
                break
            else:
                print('Invalid option')

    except Exception as e:
        print(f'Error: {e}')

    finally:
        # Cleanup
        if 'llac' in locals():
            llac.cleanup()
        print('Demo completed')


if __name__ == '__main__':
    main()

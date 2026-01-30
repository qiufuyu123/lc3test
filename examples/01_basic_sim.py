#!/usr/bin/env python3
"""
Example 01: Basic LC3 Simulator Usage

This example demonstrates the basic usage of LC3Sim to:
1. Load an object file
2. Set the program counter
3. Run the program
4. Access the output and register values

Usage:
    module load lc3tools
    python 01_basic_sim.py program.obj
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lc3sim import LC3Sim, LC3Value, LC3Obj


def main():
    if len(sys.argv) < 2:
        print("Usage: python 01_basic_sim.py <program.obj>")
        print("\nThis example shows basic LC3Sim usage.")
        sys.exit(1)
    
    program_file = sys.argv[1]
    
    print("=" * 60)
    print("Example 01: Basic LC3 Simulator Usage")
    print("=" * 60)
    
    # --- Step 1: Initialize the simulator ---
    print("\n[1] Initializing LC3 simulator...")
    sim = LC3Sim()
    print("    Simulator initialized successfully!")
    
    # --- Step 2: Load the object file ---
    print(f"\n[2] Loading object file: {program_file}")
    sim.load_file(program_file)
    print("    File loaded successfully!")
    
    # --- Step 3: Set the program counter ---
    start_addr = LC3Value('x3000')
    print(f"\n[3] Setting PC to {start_addr}")
    sim.set_pc(start_addr)
    print("    PC set successfully!")
    
    # --- Step 4: Run the program ---
    print("\n[4] Running program (continue until HALT)...")
    response = sim.sim_continue()
    print("    Program halted!")
    
    # --- Step 5: Access results ---
    print("\n[5] Results:")
    print("-" * 40)
    
    # Program output
    print("Program Output:")
    print(response.raw_resp if response.raw_resp else "(no output)")
    
    # Register values
    print("\nRegister Values:")
    print(f"    R0 = {response.regs.R0} (signed: {response.regs.R0.signed})")
    print(f"    R1 = {response.regs.R1} (signed: {response.regs.R1.signed})")
    print(f"    R2 = {response.regs.R2} (signed: {response.regs.R2.signed})")
    print(f"    R3 = {response.regs.R3} (signed: {response.regs.R3.signed})")
    print(f"    R4 = {response.regs.R4} (signed: {response.regs.R4.signed})")
    print(f"    R5 = {response.regs.R5} (signed: {response.regs.R5.signed})")
    print(f"    R6 = {response.regs.R6} (signed: {response.regs.R6.signed})")
    print(f"    R7 = {response.regs.R7} (signed: {response.regs.R7.signed})")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

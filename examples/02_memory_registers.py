#!/usr/bin/env python3
"""
Example 02: Memory and Register Operations

This example demonstrates how to:
1. Read and write memory
2. Read and set registers
3. Use LC3Value for different number formats

Usage:
    module load lc3tools
    python 02_memory_registers.py [program.obj]
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lc3sim import LC3Sim, LC3Value, LC3Obj


def main():
    print("=" * 60)
    print("Example 02: Memory and Register Operations")
    print("=" * 60)
    
    # --- Initialize simulator ---
    print("\n[1] Initializing LC3 simulator...")
    sim = LC3Sim()
    
    # Load program if provided
    if len(sys.argv) >= 2:
        print(f"    Loading: {sys.argv[1]}")
        sim.load_file(sys.argv[1])
    
    # --- LC3Value Examples ---
    print("\n[2] LC3Value - Different Input Formats:")
    print("-" * 40)
    
    # Different ways to create LC3Value
    v1 = LC3Value(0x1234)       # Python hex integer
    v2 = LC3Value('x5678')      # LC-3 hex notation
    v3 = LC3Value('0xABCD')     # Standard hex string
    v4 = LC3Value('#100')       # LC-3 decimal notation
    v5 = LC3Value(255)          # Decimal integer
    v6 = LC3Value('xFFFF')      # Max 16-bit value
    
    print(f"    LC3Value(0x1234)   = {v1}")
    print(f"    LC3Value('x5678')  = {v2}")
    print(f"    LC3Value('0xABCD') = {v3}")
    print(f"    LC3Value('#100')   = {v4} (decimal 100)")
    print(f"    LC3Value(255)      = {v5}")
    print(f"    LC3Value('xFFFF')  = {v6} (signed: {v6.signed})")
    
    # Arithmetic
    print("\n    Arithmetic:")
    result = v1 + 10
    print(f"    {v1} + 10 = {result}")
    
    # --- Memory Operations ---
    print("\n[3] Memory Operations:")
    print("-" * 40)
    
    # Write to memory
    addr = LC3Value('x4000')
    data = LC3Value('x1234')
    print(f"    Writing {data} to address {addr}...")
    sim.write_mem(addr, data)
    
    # Read from memory
    read_value = sim.read_mem(addr)
    print(f"    Read from {addr}: {read_value}")
    
    # Write multiple values
    print("\n    Writing a sequence to memory x4001-x4005:")
    for i in range(5):
        addr = LC3Value(0x4001 + i)
        data = LC3Value(0x0041 + i)  # 'A', 'B', 'C', 'D', 'E'
        sim.write_mem(addr, data)
        print(f"        {addr} = {data} (ASCII: '{chr(0x41 + i)}')")
    
    # Read them back
    print("\n    Reading back:")
    for i in range(5):
        addr = LC3Value(0x4001 + i)
        value = sim.read_mem(addr)
        print(f"        {addr} = {value}")
    
    # --- Register Operations ---
    print("\n[4] Register Operations:")
    print("-" * 40)
    
    # Set registers
    print("    Setting registers:")
    sim.set_reg('R0', LC3Value('xDEAD'))
    sim.set_reg('R1', LC3Value('xBEEF'))
    sim.set_reg('R2', LC3Value('x0042'))
    sim.set_reg('R3', LC3Value('xFFFF'))  # -1 in signed
    print("        R0 = xDEAD")
    print("        R1 = xBEEF")
    print("        R2 = x0042 (66 decimal)")
    print("        R3 = xFFFF (-1 signed)")
    
    # Read all registers
    print("\n    Reading all registers:")
    regs = sim.read_regs()
    print(f"        R0 = {regs.R0} (signed: {regs.R0.signed})")
    print(f"        R1 = {regs.R1} (signed: {regs.R1.signed})")
    print(f"        R2 = {regs.R2} (signed: {regs.R2.signed})")
    print(f"        R3 = {regs.R3} (signed: {regs.R3.signed})")
    print(f"        R4 = {regs.R4}")
    print(f"        R5 = {regs.R5}")
    print(f"        R6 = {regs.R6}")
    print(f"        R7 = {regs.R7}")
    
    # Set PC
    print("\n    Setting PC:")
    sim.set_reg('PC', LC3Value('x3000'))
    regs = sim.read_regs()
    print(f"        PC set to x3000")
    
    # --- LC3Obj Example ---
    print("\n[5] LC3Obj - Creating Dynamic Object Files:")
    print("-" * 40)
    
    # Create an object file with string data
    test_string = "Hello LC3!"
    obj = LC3Obj(LC3Value('x5000'), test_string.encode())
    
    print(f"    Created LC3Obj with string: '{test_string}'")
    print(f"    Origin address: x5000")
    print(f"    Buffer size: {len(obj.buffer)} bytes")
    
    # Load it into simulator
    obj_path = obj.to_file()
    print(f"    Temp file created: {obj_path}")
    sim.load_file(obj_path)
    print("    Loaded into simulator!")
    
    # Read back the data
    print("\n    Reading string from memory:")
    for i, char in enumerate(test_string):
        addr = LC3Value(0x5000 + i)
        value = sim.read_mem(addr)
        print(f"        {addr} = {value} ('{chr(int(value))}')")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

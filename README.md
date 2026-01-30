# LC3 Simulator Test Framework

A Python-based testing framework for the LC-3 (Little Computer 3) simulator. This library provides utilities for automating LC-3 program testing, including value manipulation, register inspection, and randomized test generation.

## Features

- **LC3Value**: A robust 16-bit value class with support for various input formats (hex, decimal, LC-3 notation)
- **LC3Obj**: Create LC-3 object files dynamically with data at specified memory addresses
- **LC3Sim**: Automated interaction with the `lc3sim` simulator via pexpect
- **LC3Response**: Parse and analyze simulator output, including register states
- **LC3RandomGenTests**: Framework for running parallel randomized test suites with progress tracking
- **LC3SequenceTest**: Framework for running individual/boundary test cases with named tests

## Requirements

- Python 3.6+
- `pexpect` library
- `lc3tools` module (provides `lc3sim` command-line simulator)

## Installation

```bash
pip install pexpect
```

Make sure `lc3sim` is installed and accessible from your command line.

## Quick Start

```bash
# 1. Load lc3tools module (on systems with module environment)
module load lc3tools

# 2. Run tests on your LC-3 program
python test_mp1.py your_program.obj

# 3. Run boundary tests only
python test_mp1.py your_program.obj --boundary-only
```

## Usage

### LC3Value - Working with 16-bit Values

```python
from lc3sim import LC3Value

# Create values from different formats
v1 = LC3Value(0x1234)        # From Python hex integer
v2 = LC3Value('x1234')       # From LC-3 hex notation
v3 = LC3Value('0x1234')      # From standard hex string
v4 = LC3Value('#100')        # From LC-3 decimal notation
v5 = LC3Value(1234)          # From decimal integer

# Get signed value (two's complement)
neg_one = LC3Value('xFFFF')
print(neg_one.signed)        # Output: -1

# Arithmetic operations
result = v1 + 10             # Returns new LC3Value

# String representation
print(str(v1))               # Output: x1234
```

### LC3Obj - Creating Dynamic Object Files

`LC3Obj` allows you to create LC-3 object files dynamically with data at a specified memory address. This is useful for injecting test data into memory.

```python
from lc3sim import LC3Obj, LC3Value

# Create an object file with string data at address x4000
input_string = "Hello World"
obj = LC3Obj(LC3Value('x4000'), input_string.encode())

# Get the temporary file path (auto-generated UUID filename)
obj_path = obj.to_file()  # Returns something like 'tmp/abc123.obj'

# Load into simulator
sim = LC3Sim()
sim.load_file('program.obj')      # Load your program
sim.load_file(obj.to_file())      # Load the data object file

# The object file is automatically deleted when obj goes out of scope
```

**Memory Layout:**
- The data is stored starting at the specified origin address
- Each byte of input data is stored as a 16-bit word (high byte = 0x00)
- A null terminator (0x0000) is automatically appended

### LC3Sim - Interacting with the Simulator

```python
from lc3sim import LC3Sim, LC3Value

# Initialize simulator
sim = LC3Sim()

# Load an object file
sim.load_file('program.obj')

# Set program counter
sim.set_pc(LC3Value('x3000'))

# Run until halt
response = sim.sim_continue()

# Access results
print(response.raw_resp)           # Program output
print(response.regs.R0)            # Register R0 value
print(response.regs.R1.signed)     # R1 as signed value
```

### LC3Response - Comparing Output

```python
# Compare actual output with expected
expected = """Hello, World!
Result: 42"""

if response.diff_resp(expected):
    print("Test passed!")
else:
    print("Test failed - see diff above")
```

### LC3RandomGenTests - Parallel Randomized Testing

Create a subclass and override `run_case` to implement your test logic. Tests run in parallel for faster execution.

```python
from lc3sim import LC3RandomGenTests, LC3Sim, LC3Value, LC3Obj
import random

class MyTests(LC3RandomGenTests):
    def set_target(self, target):
        self.target = target
    
    def run_case(self, case_num):
        # Use case_num as seed for reproducibility
        random.seed(case_num)
        
        # Generate random test input
        test_data = ''.join(random.choices('ABCDEF123', k=100))
        expected_output = compute_expected(test_data)
        
        # Create data object file
        obj = LC3Obj(LC3Value('x4000'), test_data.encode())
        
        # Run simulation
        sim = LC3Sim()
        sim.load_file(self.target)
        sim.load_file(obj.to_file())
        sim.set_pc(LC3Value('x3000'))
        response = sim.sim_continue()
        
        # Return True if passed, False if failed
        return response.diff_resp(expected_output)

# Run 100 test cases with 8 parallel workers
tests = MyTests(test_nums=100, max_workers=8)
tests.set_target('my_program.obj')
tests.run_all()
```

Sample output:
```
>>> Starting LC3 Parallel Random Tests (100 test cases)...
Using 8 parallel workers

Progress: [========================================>] 100.0% (100/100)

============================================================
Test Report (Parallel)
============================================================
Duration:     1.2345 seconds
Avg Time:     12.35 ms/case
Throughput:   81.0 cases/sec
Total:        100
Passed:       98
Failed:       2
Pass Rate:    98.00%

>>> Failure Details:
------------------------------------------------------------
Case ID    | Error Reason
------------------------------------------------------------
Case 23    | Assertion Failed (Returned False)
Case 67    | ValueError: Invalid input
============================================================
```

### LC3SequenceTest - Boundary/Edge Case Testing

Use this for individual named test cases, especially boundary tests:

```python
from lc3sim import LC3SequenceTest, LC3Sim, LC3Value, LC3Obj

def run_test(target, input_str, expected):
    """Helper function to run a single test"""
    obj = LC3Obj(LC3Value('x4000'), input_str.encode())
    sim = LC3Sim()
    sim.load_file(target)
    sim.load_file(obj.to_file())
    sim.set_pc(LC3Value('x3000'))
    return sim.sim_continue().diff_resp(expected)

# Create test suite
boundary_tests = LC3SequenceTest("MP1 Boundary Tests")

# Add tests using decorator
@boundary_tests.test("Empty string input")
def test_empty():
    return run_test('program.obj', "", expected_empty_output)

@boundary_tests.test("Single character 'A'")
def test_single_char():
    return run_test('program.obj', "A", expected_single_output)

@boundary_tests.test("Maximum length input (500 chars)")
def test_max_length():
    return run_test('program.obj', "A" * 500, expected_max_output)

# Or add tests programmatically
boundary_tests.add_test("All digits 0-9", lambda: run_test('program.obj', "0123456789", expected))

# Run all tests
boundary_tests.run_all()
```

Sample output:
```
>>> Starting MP1 Boundary Tests (4 test cases)...

----------------------------------------------------------------------
#    Test Name                                     Result     Time
----------------------------------------------------------------------
1    Empty string input                            PASS       45.23ms
2    Single character 'A'                          PASS       43.12ms
3    Maximum length input (500 chars)              FAIL       52.34ms
4    All digits 0-9                                PASS       44.56ms
----------------------------------------------------------------------

============================================================
Test Report: MP1 Boundary Tests
============================================================
Duration:     0.1853 seconds
Avg Time:     46.31 ms/case
Total:        4
Passed:       3
Failed:       1
Pass Rate:    75.00%

>>> Failure Details:
------------------------------------------------------------
Test Name                           | Error Reason
------------------------------------------------------------
Maximum length input (500 chars)    | Returned False
============================================================
```

## Complete Example

Here's a complete example for testing an LC-3 program:

```bash
# Step 1: Load the LC3 tools
module load lc3tools

# Step 2: Assemble your program (if needed)
lc3as my_program.asm

# Step 3: Run the test suite
python test_mp1.py my_program.obj
```

```python
# test_mp1.py
from lc3sim import *
import sys

def run_boundary_tests(target):
    tests = LC3SequenceTest("Boundary Tests")
    
    @tests.test("Empty input")
    def t1():
        # Your test logic here
        return True
    
    @tests.test("Edge case: single char")
    def t2():
        return True
    
    tests.run_all()

def run_random_tests(target):
    class RandomTests(LC3RandomGenTests):
        def set_target(self, t):
            self.target = t
        def run_case(self, case_num):
            # Your random test logic here
            return True
    
    tests = RandomTests(test_nums=100, max_workers=8)
    tests.set_target(target)
    tests.run_all()

if __name__ == "__main__":
    target = sys.argv[1]
    
    print("=" * 60)
    print("Phase 1: Boundary Tests")
    print("=" * 60)
    run_boundary_tests(target)
    
    print("=" * 60)
    print("Phase 2: Random Tests")
    print("=" * 60)
    run_random_tests(target)
```

## API Reference

### LC3Value

| Method/Property | Description |
|-----------------|-------------|
| `__init__(value)` | Create from int or string (supports 'x1234', '0x1234', '#10') |
| `signed` | Get 16-bit signed (two's complement) value |
| `h16raw()` | Get raw hex string without prefix (e.g., '1234') |
| `to_bytes()` | Export as 2-byte big-endian bytes |

### LC3Obj

| Method/Property | Description |
|-----------------|-------------|
| `__init__(orig, data)` | Create with origin address (LC3Value) and data (bytes) |
| `to_file()` | Write to temp file and return path |
| `buffer` | Raw bytearray of the object file |

### LC3Sim

| Method | Description |
|--------|-------------|
| `load_file(path)` | Load an LC-3 object file |
| `set_pc(LC3Value)` | Set the program counter |
| `sim_continue()` | Run until HALT, returns LC3Response |
| `send_command(cmd)` | Send raw command to simulator |

### LC3Response

| Property/Method | Description |
|-----------------|-------------|
| `raw_resp` | Raw program output (before HALT) |
| `regs` | LC3Regs object with R0-R7 values |
| `diff_resp(expected)` | Compare output, returns bool, prints diff on mismatch |

### LC3RandomGenTests

| Method | Description |
|--------|-------------|
| `__init__(test_nums, max_workers)` | Initialize with test count and parallel workers |
| `run_case(case_num)` | Override this - implement single test, return True/False |
| `run_all()` | Execute all tests in parallel with progress bar |
| `report()` | Print final test report |

### LC3SequenceTest

| Method | Description |
|--------|-------------|
| `__init__(name)` | Initialize with test suite name |
| `add_test(name, func)` | Add a named test case |
| `test(name)` | Decorator to add a test function |
| `run_all()` | Execute all tests sequentially |
| `report()` | Print final test report |

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

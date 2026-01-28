# LC3 Simulator Test Framework

A Python-based testing framework for the LC-3 (Little Computer 3) simulator. This library provides utilities for automating LC-3 program testing, including value manipulation, register inspection, and randomized test generation.

## Features

- **LC3Value**: A robust 16-bit value class with support for various input formats (hex, decimal, LC-3 notation)
- **LC3Sim**: Automated interaction with the `lc3sim` simulator via pexpect
- **LC3Response**: Parse and analyze simulator output, including register states
- **LC3RandomGenTests**: Framework for running randomized test suites with progress tracking and detailed reports

## Requirements

- Python 3.6+
- `pexpect` library
- `lc3sim` command-line simulator installed and available in PATH

## Installation

```bash
pip install pexpect
```

Make sure `lc3sim` is installed and accessible from your command line.

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

### LC3RandomGenTests - Randomized Testing

Create a subclass and override `run_case` to implement your test logic:

```python
from lc3sim import LC3RandomGenTests, LC3Sim, LC3Value
import random

class MyTests(LC3RandomGenTests):
    def run_case(self, case_num):
        # Use case_num as seed for reproducibility
        random.seed(case_num)
        
        # Generate test input
        test_input = random.randint(0, 100)
        expected_output = test_input * 2  # Expected behavior
        
        # Run simulation
        sim = LC3Sim()
        sim.load_file('my_program.obj')
        # ... setup and run ...
        
        # Return True if passed, False if failed
        return actual_output == expected_output

# Run 100 test cases
tests = MyTests(test_nums=100)
tests.run_all()
```

Sample output:
```
>>> Starting LC3 Random Tests (100 test cases)...

Progress: [========================================>] 100.0% (100/100)

============================================================
Test Report
============================================================
Duration:     2.3456 seconds
Avg Time:     23.46 ms/case
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

## API Reference

### LC3Value

| Method/Property | Description |
|-----------------|-------------|
| `__init__(value)` | Create from int or string (supports 'x1234', '0x1234', '#10') |
| `signed` | Get 16-bit signed (two's complement) value |
| `h16raw()` | Get raw hex string without prefix (e.g., '1234') |
| `to_bytes()` | Export as 2-byte big-endian bytes |

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
| `__init__(test_nums)` | Initialize with number of test cases |
| `run_case(case_num)` | Override this - implement single test, return True/False |
| `run_all()` | Execute all tests with progress bar |
| `report()` | Print final test report |

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

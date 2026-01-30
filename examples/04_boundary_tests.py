#!/usr/bin/env python3
"""
Example 04: Boundary/Edge Case Testing

This example demonstrates how to use LC3SequenceTest for:
1. Creating named test cases
2. Testing boundary conditions
3. Using decorators to define tests
4. Generating detailed test reports

Usage:
    module load lc3tools
    python 04_boundary_tests.py program.obj
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lc3sim import LC3SequenceTest, LC3Sim, LC3Value, LC3Obj


def run_test(target, input_str, expected_output):
    """
    Helper function to run a single test case.
    
    :param target: Path to LC3 object file
    :param input_str: Input string to test
    :param expected_output: Expected program output
    :return: True if passed, False if failed
    """
    # Create data object file
    obj = LC3Obj(LC3Value('x4000'), input_str.encode())
    
    # Initialize and run simulator
    sim = LC3Sim()
    sim.load_file(target)
    sim.load_file(obj.to_file())
    sim.set_pc(LC3Value('x3000'))
    response = sim.sim_continue()
    
    # Compare output
    return response.diff_resp(expected_output)


def create_boundary_tests(target):
    """
    Create a suite of boundary tests for the given program.
    """
    tests = LC3SequenceTest("Boundary Tests")
    
    # --- Method 1: Using decorator ---
    
    @tests.test("Empty string input")
    def test_empty():
        # Test with empty input
        # return run_test(target, "", expected_empty_output)
        return True  # Demo: always pass
    
    @tests.test("Single character 'A'")
    def test_single_a():
        # Test with single uppercase letter
        # return run_test(target, "A", expected_single_output)
        return True
    
    @tests.test("Single character 'z'")
    def test_single_z():
        # Test with single lowercase letter
        return True
    
    @tests.test("Single digit '5'")
    def test_single_digit():
        # Test with non-letter character
        return True
    
    # --- Method 2: Using add_test ---
    
    tests.add_test("All uppercase A-Z", lambda: True)
    tests.add_test("All lowercase a-z", lambda: True)
    tests.add_test("Mixed case 'AaBbCc'", lambda: True)
    
    # --- Boundary tests ---
    
    @tests.test("ASCII boundary: '@' (before 'A')")
    def test_before_a():
        # Character just before 'A' in ASCII
        return True
    
    @tests.test("ASCII boundary: '[' (after 'Z')")
    def test_after_z():
        # Character just after 'Z' in ASCII
        return True
    
    @tests.test("ASCII boundary: '`' (before 'a')")
    def test_before_lower_a():
        return True
    
    @tests.test("ASCII boundary: '{' (after 'z')")
    def test_after_lower_z():
        return True
    
    # --- Length tests ---
    
    @tests.test("Minimum length (1 char)")
    def test_min_length():
        return True
    
    @tests.test("Short string (10 chars)")
    def test_short():
        return True
    
    @tests.test("Medium string (100 chars)")
    def test_medium():
        return True
    
    @tests.test("Long string (500 chars)")
    def test_long():
        return True
    
    # --- Special patterns ---
    
    @tests.test("All same character 'AAAA'")
    def test_same_char():
        return True
    
    @tests.test("Alternating 'AbAbAbAb'")
    def test_alternating():
        return True
    
    @tests.test("Numbers only '0123456789'")
    def test_numbers():
        return True
    
    @tests.test("Special chars '!@#$%^&*()'")
    def test_special():
        return True
    
    @tests.test("Whitespace ' \\t\\n'")
    def test_whitespace():
        return True
    
    # --- Simulated failure for demo ---
    
    @tests.test("Intentional failure (demo)")
    def test_fail():
        return False  # This will show as FAIL
    
    @tests.test("Intentional error (demo)")
    def test_error():
        raise ValueError("Demo error message")
    
    return tests


def create_demo_tests():
    """
    Create demo tests that don't require an actual LC3 program.
    """
    import time
    
    tests = LC3SequenceTest("Demo Boundary Tests")
    
    @tests.test("Fast test (10ms)")
    def test_fast():
        time.sleep(0.01)
        return True
    
    @tests.test("Medium test (50ms)")
    def test_medium():
        time.sleep(0.05)
        return True
    
    @tests.test("Slow test (100ms)")
    def test_slow():
        time.sleep(0.1)
        return True
    
    @tests.test("Pass test 1")
    def test_pass1():
        return True
    
    @tests.test("Pass test 2")
    def test_pass2():
        return True
    
    @tests.test("Fail test (demo)")
    def test_fail():
        return False
    
    @tests.test("Error test (demo)")
    def test_error():
        raise RuntimeError("Simulated error")
    
    @tests.test("Pass test 3")
    def test_pass3():
        return True
    
    return tests


def main():
    print("=" * 60)
    print("Example 04: Boundary/Edge Case Testing")
    print("=" * 60)
    
    if len(sys.argv) >= 2:
        # Run actual tests on provided program
        program_file = sys.argv[1]
        print(f"\nRunning boundary tests on: {program_file}")
        print("-" * 60)
        
        tests = create_boundary_tests(program_file)
        tests.run_all()
    else:
        # Run demo tests
        print("\nNo program file provided. Running demo tests...")
        print("Usage: python 04_boundary_tests.py program.obj")
        print("-" * 60)
        
        tests = create_demo_tests()
        tests.run_all()
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

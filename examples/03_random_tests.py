#!/usr/bin/env python3
"""
Example 03: Parallel Random Testing

This example demonstrates how to use LC3RandomGenTests for:
1. Creating randomized test cases
2. Running tests in parallel
3. Generating test reports

Usage:
    module load lc3tools
    python 03_random_tests.py program.obj
"""

import sys
import os
import random

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lc3sim import LC3RandomGenTests, LC3Sim, LC3Value, LC3Obj


class SimpleRandomTests(LC3RandomGenTests):
    """
    Example random test class.
    
    This demonstrates a simple pattern where we:
    1. Generate random input data
    2. Compute expected output
    3. Run the LC3 program
    4. Compare actual vs expected
    """
    
    def set_target(self, target_file):
        """Set the target LC3 object file to test"""
        self.target = target_file
    
    def run_case(self, case_num):
        """
        Execute a single test case.
        
        :param case_num: Test case number (can be used as random seed)
        :return: True if test passed, False if failed
        """
        # Use case_num as seed for reproducibility
        random.seed(case_num)
        
        # --- Generate random test input ---
        # Example: generate a random string of letters
        length = random.randint(10, 50)
        test_input = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=length))
        
        # --- Compute expected output ---
        # Example: count each letter (simplified version)
        # In a real test, this would match your LC3 program's expected behavior
        expected_output = self._compute_expected(test_input)
        
        # --- Create data object file ---
        obj = LC3Obj(LC3Value('x4000'), test_input.encode())
        
        # --- Run simulation ---
        sim = LC3Sim()
        sim.load_file(self.target)
        sim.load_file(obj.to_file())
        sim.set_pc(LC3Value('x3000'))
        response = sim.sim_continue()
        
        # --- Compare results ---
        # Option 1: Use diff_resp for output comparison
        # return response.diff_resp(expected_output)
        
        # Option 2: Check register values
        # return response.regs.R0 == expected_value
        
        # For this demo, we'll simulate success/failure
        # In a real test, compare actual output with expected
        return True  # Replace with actual comparison
    
    def _compute_expected(self, input_str):
        """
        Compute expected output for the given input.
        This should match what your LC3 program produces.
        """
        # Example: count letters and format output
        counts = {}
        for char in input_str:
            if char.isalpha():
                upper = char.upper()
                counts[upper] = counts.get(upper, 0) + 1
        
        # Format as expected output
        result = ""
        for letter in sorted(counts.keys()):
            result += f"{letter}: {counts[letter]}\n"
        
        return result


class DemoRandomTests(LC3RandomGenTests):
    """
    Demo test class that doesn't require an actual LC3 program.
    Simulates test execution with random pass/fail.
    """
    
    def run_case(self, case_num):
        """
        Demo test case - simulates 95% pass rate.
        """
        import time
        
        # Simulate some work
        time.sleep(0.01)  # 10ms per test
        
        # 95% pass rate for demo
        random.seed(case_num)
        return random.random() > 0.05


def main():
    print("=" * 60)
    print("Example 03: Parallel Random Testing")
    print("=" * 60)
    
    if len(sys.argv) >= 2:
        # Run actual tests on provided program
        program_file = sys.argv[1]
        print(f"\nRunning tests on: {program_file}")
        print("-" * 60)
        
        tests = SimpleRandomTests(test_nums=50, max_workers=8)
        tests.set_target(program_file)
        tests.run_all()
    else:
        # Run demo tests
        print("\nNo program file provided. Running demo tests...")
        print("Usage: python 03_random_tests.py program.obj")
        print("-" * 60)
        
        # Demo with different configurations
        print("\n[Demo 1] 50 tests with 4 workers:")
        tests1 = DemoRandomTests(test_nums=50, max_workers=4)
        tests1.run_all()
        
        print("\n[Demo 2] 100 tests with 8 workers:")
        tests2 = DemoRandomTests(test_nums=100, max_workers=8)
        tests2.run_all()
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

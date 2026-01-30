"""
LC3 Simulator Test Framework

A Python-based testing framework for the LC-3 (Little Computer 3) simulator.
Provides utilities for automating LC-3 program testing, including value manipulation,
register inspection, memory operations, and randomized test generation.

Classes:
    LC3Value: 16-bit value wrapper with format conversion
    LC3Obj: Dynamic LC-3 object file generator
    LC3Regs: Container for LC-3 register values
    LC3Response: Parser for simulator output
    LC3Sim: Simulator interface via pexpect
    LC3RandomGenTests: Parallel randomized test framework
    LC3SequenceTest: Sequential boundary test framework
"""

import pexpect
import sys, os
import re
import uuid
import difflib
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


class LC3Value:
    """
    A class representing a 16-bit LC-3 value.
    
    Supports multiple input formats and provides conversion utilities.
    All values are automatically truncated to 16 bits (0x0000 - 0xFFFF).
    
    Attributes:
        _value (int): The internal 16-bit unsigned integer value
    
    Example:
        >>> v1 = LC3Value(0x1234)
        >>> v2 = LC3Value('x5678')
        >>> v3 = LC3Value('#100')
        >>> print(v1)
        x1234
        >>> print(v1.signed)
        4660
    """
    
    def __init__(self, value):
        """
        Initialize an LC3 value from various formats.
        
        :param value: The value to convert. Accepts:
            - int: Python integer (e.g., 0x1234, 255)
            - str: LC-3 hex notation ('x1234'), standard hex ('0x1234'),
                   LC-3 decimal ('#100'), or plain hex string ('1234')
        :raises TypeError: If value is not int or str
        
        Example:
            >>> LC3Value(0x1234)      # From Python hex
            >>> LC3Value('x1234')     # From LC-3 notation
            >>> LC3Value('#100')      # From LC-3 decimal
        """
        self._value = 0
        
        if isinstance(value, int):
            self._value = value
        elif isinstance(value, str):
            value = value.strip().lower()
            if value.startswith('x'):
                # Handle 'x1234' format
                self._value = int(value[1:], 16)
            elif value.startswith('0x'):
                # Handle '0x1234' format
                self._value = int(value, 16)
            elif value.startswith('#'):
                # Handle '#10' (LC3 assembly sometimes uses # for decimal)
                self._value = int(value[1:])
            else:
                # Plain numeric string, try parsing as hex (LC3 output is usually hex)
                try:
                    self._value = int(value, 16)
                except ValueError:
                    # If conversion fails, might be empty string or other
                    self._value = 0
        else:
            raise TypeError(f"Unsupported type: {type(value)}")

        # Core logic: force truncation to 16 bits (0 ~ 65535)
        self._value &= 0xFFFF

    def h16raw(self):
        """
        Get the raw 4-digit uppercase hex string without prefix.
        
        :return: 4-character hex string (e.g., '1234', '00FF')
        
        Example:
            >>> LC3Value(0x1234).h16raw()
            '1234'
        """
        return f"{self._value:04X}"
    
    def to_bytes(self):
        """
        Export as 2-byte Big-Endian bytes object.
        
        LC-3 is a big-endian machine (high byte first).
        
        :return: 2-byte bytes object in big-endian order
        
        Example:
            >>> LC3Value(0x4000).to_bytes()
            b'@\\x00'
        """
        return self._value.to_bytes(2, byteorder='big')
    
    def __int__(self):
        """
        Convert to Python integer.
        
        :return: Unsigned 16-bit integer value (0-65535)
        
        Example:
            >>> int(LC3Value('xFFFF'))
            65535
        """
        return self._value

    def __str__(self):
        """
        Convert to LC-3 hex notation string.
        
        :return: String in 'xXXXX' format (e.g., 'x1234')
        
        Example:
            >>> str(LC3Value(0x1234))
            'x1234'
        """
        return f"x{self._value:04X}"

    def __repr__(self):
        """
        Get detailed string representation for debugging.
        
        :return: String in 'LC3Value(xXXXX)' format
        """
        return f"LC3Value({self.__str__()})"

    def __eq__(self, other):
        """
        Compare equality with another value.
        
        :param other: LC3Value, int, or string to compare
        :return: True if values are equal, False otherwise
        
        Example:
            >>> LC3Value(0x1234) == 'x1234'
            True
        """
        if isinstance(other, LC3Value):
            return self._value == other._value
        if isinstance(other, int):
            return self._value == other
        if isinstance(other, str):
            return self._value == LC3Value(other)._value
        return False

    def __add__(self, other):
        """
        Add another value, returning a new LC3Value.
        
        :param other: LC3Value or int to add
        :return: New LC3Value with the sum (truncated to 16 bits)
        
        Example:
            >>> LC3Value(0x1000) + 0x234
            LC3Value(x1234)
        """
        val = other
        if isinstance(other, LC3Value):
            val = other._value
        return LC3Value(self._value + val)

    @property
    def signed(self):
        """
        Get the 16-bit signed two's complement value.
        
        :return: Signed integer in range -32768 to 32767
        
        Example:
            >>> LC3Value('xFFFF').signed
            -1
            >>> LC3Value('x7FFF').signed
            32767
        """
        if self._value & 0x8000:  # Check sign bit (bit 15)
            return self._value - 0x10000
        return self._value


class LC3Obj:
    """
    A class for creating LC-3 object files dynamically.
    
    Creates a temporary .obj file with data at a specified memory address.
    The file is automatically deleted when the object is garbage collected.
    
    Attributes:
        buffer (bytearray): Raw bytes of the object file
        tmp_path (str): Path to the temporary file (empty until to_file() is called)
    
    Example:
        >>> obj = LC3Obj(LC3Value('x4000'), b'Hello')
        >>> path = obj.to_file()
        >>> # File is auto-deleted when obj goes out of scope
    """
    
    def __init__(self, orig: LC3Value, data: bytes):
        """
        Create an LC-3 object file with data at specified origin.
        
        Memory layout:
        - First 2 bytes: Origin address (big-endian)
        - Following words: Each byte of data as a 16-bit word (0x00XX)
        - Final word: Null terminator (0x0000)
        
        :param orig: Origin address as LC3Value (where data will be loaded)
        :param data: Bytes to store in memory
        
        Example:
            >>> obj = LC3Obj(LC3Value('x4000'), "Hello".encode())
        """
        self.buffer = bytearray(orig.to_bytes())
        for item in data:
            self.buffer.append(0x00)
            self.buffer.append(item)
        self.buffer.append(0x00)
        self.buffer.append(0x00)
        self.tmp_path = ''
    
    def to_file(self):
        """
        Write the object file to disk and return the path.
        
        Creates a temporary file in the 'tmp/' directory with a UUID filename.
        Subsequent calls return the same path without rewriting.
        
        :return: Path to the temporary .obj file
        
        Example:
            >>> obj = LC3Obj(LC3Value('x4000'), b'test')
            >>> path = obj.to_file()  # e.g., 'tmp/abc123-def456.obj'
        """
        if self.tmp_path == '':
            name = f'tmp/{uuid.uuid4()}.obj'
            os.makedirs('tmp', exist_ok=True)
            with open(name, 'wb') as f:
                f.write(self.buffer)
            self.tmp_path = name
        return self.tmp_path
    
    def __del__(self):
        """
        Destructor that removes the temporary file.
        
        Called automatically when the object is garbage collected.
        """
        if self.tmp_path:
            try:
                os.remove(self.tmp_path)
            except OSError:
                pass


class LC3Regs:
    """
    Container for LC-3 register values.
    
    Holds the 8 general-purpose registers (R0-R7) as LC3Value objects.
    
    Attributes:
        R0-R7 (LC3Value): General purpose registers
    
    Example:
        >>> regs = sim.read_regs()
        >>> print(regs.R0)
        x1234
        >>> print(regs.R0.signed)
        4660
    """
    
    def __init__(self, reg_map={}):
        """
        Initialize registers, optionally from a dictionary.
        
        :param reg_map: Optional dict mapping register names to LC3Value objects.
                       Expected keys: 'R0', 'R1', ..., 'R7'
        
        Example:
            >>> regs = LC3Regs({'R0': LC3Value(0x1234), ...})
        """
        self.R0 = LC3Value(0)
        self.R1 = LC3Value(0)
        self.R2 = LC3Value(0)
        self.R3 = LC3Value(0)
        self.R4 = LC3Value(0)
        self.R5 = LC3Value(0)
        self.R6 = LC3Value(0)
        self.R7 = LC3Value(0)
        if reg_map:
            self.R0 = reg_map['R0']
            self.R1 = reg_map['R1']
            self.R2 = reg_map['R2']
            self.R3 = reg_map['R3']
            self.R4 = reg_map['R4']
            self.R5 = reg_map['R5']
            self.R6 = reg_map['R6']
            self.R7 = reg_map['R7']
    
    def __str__(self):
        """
        Get formatted string representation of all registers.
        
        :return: Multi-line string with all register values
        """
        return f'''
R0: {self.R0}
R1: {self.R1}
R2: {self.R2}  
R3: {self.R3}
R4: {self.R4}
R5: {self.R5}
R6: {self.R6}
R7: {self.R7}
              '''


class LC3Response:
    """
    Parser for LC-3 simulator output after program execution.
    
    Parses the raw output from 'continue' command, extracting program output
    and final register states.
    
    Attributes:
        raw_resp (str): Program output (before HALT message)
        raw_status (str): Status output (after HALT message)
        regs (LC3Regs): Final register values
    
    Example:
        >>> response = sim.sim_continue()
        >>> print(response.raw_resp)  # Program output
        >>> print(response.regs.R0)   # Final R0 value
    """
    
    def __init__(self, raw_resp: str):
        """
        Parse simulator output from continue command.
        
        :param raw_resp: Raw output string from simulator
        
        The output is split at '--- halting the LC-3 ---' to separate
        program output from register dump.
        """
        segs = raw_resp.strip().split('--- halting the LC-3 ---')
        
        self.raw_resp = segs[0]
        self.raw_status = segs[1]
        regs = self.parse_registers(self.raw_status)
        self.regs = LC3Regs(regs)
    
    def parse_registers(self, output_str):
        """
        Parse register values from simulator output.
        
        :param output_str: String containing register dump (e.g., 'R0=x1234 R1=x5678...')
        :return: Dictionary mapping register names to LC3Value objects
        
        Example output format:
            PC=x0494 IR=xB1AE PSR=x0400 (ZERO)
            R0=x0000 R1=x7FFF R2=x0000 R3=x0000 R4=x0000 R5=x0000 R6=x0000 R7=x0490
        """
        pattern = r'(\w+)=(x[\da-fA-F]+)'
        matches = re.findall(pattern, output_str)
        reg_dict_str = dict(matches)
        
        reg_dict_val = {}
        for key, val in matches:
            reg_dict_val[key] = LC3Value(val)
            
        return reg_dict_val
    
    def diff_resp(self, expect_txt: str):
        """
        Compare actual output with expected output.
        
        If outputs differ, prints a colored diff report showing line-by-line
        comparison with expected (green) and actual (red for mismatches) values.
        
        :param expect_txt: Expected program output string
        :return: True if outputs match exactly, False otherwise
        
        Example:
            >>> if response.diff_resp("Expected output"):
            ...     print("Test passed!")
            ... else:
            ...     print("Test failed - see diff above")
        """
        # Data cleaning: split by lines, strip whitespace
        expect_lines = [line.strip() for line in expect_txt.strip().splitlines()]
        actual_lines = [line.strip() for line in self.raw_resp.strip().splitlines()]

        # Quick check: if identical, return True immediately
        if expect_lines == actual_lines:
            return True

        # Calculate total lines (take max of both to handle missing lines)
        max_lines = max(len(expect_lines), len(actual_lines))
        
        # Calculate max width for expected column for alignment
        max_width = max([len(line) for line in expect_lines]) if expect_lines else 10
        col_width = max_width + 4

        # ANSI color definitions
        GREEN = '\033[92m'
        RED = '\033[91m'
        RESET = '\033[0m'
        
        print("\n" + "="*60)
        print(f"❌  (Diff Report)")
        print(f"{'Line':<5} {'Expected (Correct)':<{col_width}} {'Actual (Original)'}")
        print("-" * (col_width + 30))

        # Iterate and print line by line
        for i in range(max_lines):
            exp_str = expect_lines[i] if i < len(expect_lines) else "<MISSING>"
            act_str = actual_lines[i] if i < len(actual_lines) else "<MISSING>"
            is_match = (exp_str == act_str)

            color_line = GREEN if is_match else RED
            color_exp = GREEN
            color_act = GREEN if is_match else RED

            line_num_str = f"{i+1}".ljust(5)
            exp_str_padded = exp_str.ljust(col_width)

            print(f"{color_line}{line_num_str}{RESET} "
                  f"{color_exp}{exp_str_padded}{RESET} "
                  f"{color_act}{act_str}{RESET}")

        print("="*60 + "\n")
        print("Diff Failed\n")
        print("="*60 + "\n")

        return False
    
    def __str__(self):
        """
        Get formatted string representation of the response.
        
        :return: String containing raw output and register values
        """
        return f'''
--- Raw Content ---
{self.raw_resp}
--- Regs ---
{self.regs}
        '''


class LC3Sim:
    """
    Interface for interacting with the LC-3 simulator via pexpect.
    
    Provides methods for loading files, setting registers, reading/writing memory,
    and running programs.
    
    Attributes:
        child (pexpect.spawn): The pexpect child process
    
    Example:
        >>> sim = LC3Sim()
        >>> sim.load_file('program.obj')
        >>> sim.set_pc(LC3Value('x3000'))
        >>> response = sim.sim_continue()
        >>> print(response.regs.R0)
    """
    
    def __init__(self):
        """
        Initialize the LC-3 simulator.
        
        Spawns an lc3sim process and waits for the prompt.
        
        :raises Exception: If lc3sim is not found or fails to start
        """
        self.child = pexpect.spawn('lc3sim', encoding='utf-8')
        self.wait_for_input()
    
    def wait_for_input(self) -> str:
        """
        Wait for the simulator prompt '(lc3sim)'.
        
        :return: Output before the prompt
        :raises Exception: If EOF or timeout occurs
        """
        index = self.child.expect([r'\(lc3sim\)', pexpect.EOF, pexpect.TIMEOUT])
        if index > 0:
            raise Exception("expect EOF or timeout!")
        tmp = self.child.before
        return tmp
    
    def before(self):
        """
        Get the output before the last matched pattern.
        
        :return: String of output before last expect match
        """
        return self.child.before
    
    def randomize_reg(self):
        """
        Set all registers to predefined non-zero values.
        
        Used before running tests to ensure registers don't start at zero,
        which helps catch bugs where uninitialized registers are used.
        
        Register values set:
            R0=x1234, R1=x5678, R2=x9ABC, R3=xDEF0,
            R4=x1111, R5=x2222, R6=x3333, R7=x4444
        """
        self.send_command("r r0 x1234")
        self.send_command("r r1 x5678")
        self.send_command("r r2 x9ABC")
        self.send_command("r r3 xDEF0")
        self.send_command("r r4 x1111")
        self.send_command("r r5 x2222")
        self.send_command("r r6 x3333")
        self.send_command("r r7 x4444")
    
    def send_command(self, command):
        """
        Send a command to the simulator and return the response.
        
        :param command: Command string to send (e.g., 'file prog.obj')
        :return: Simulator response with command echo removed
        
        Example:
            >>> sim.send_command('file test.obj')
        """
        self.child.sendline(command)
        return self.wait_for_input().replace(command, '').strip()
    
    def set_pc(self, pc: LC3Value):
        """
        Set the program counter to a specific address.
        
        :param pc: Address to set PC to
        :return: Simulator response
        
        Example:
            >>> sim.set_pc(LC3Value('x3000'))
        """
        return self.send_command(f'r pc {str(pc)}')
    
    def load_file(self, file):
        """
        Load an LC-3 object file into the simulator.
        
        :param file: Path to the .obj file
        :return: Simulator response
        
        Example:
            >>> sim.load_file('program.obj')
        """
        return self.send_command(f'file {file}')
    
    def write_mem(self, addr: LC3Value, data: LC3Value):
        """
        Write a value to a memory address.
        
        :param addr: Memory address to write to
        :param data: Value to write
        
        Example:
            >>> sim.write_mem(LC3Value('x3000'), LC3Value('x1234'))
        """
        self.send_command(f'memory {str(addr)} {str(data)}')

    def read_mem(self, addr: LC3Value) -> LC3Value:
        """
        Read a value from a memory address.
        
        Uses the 'translate' command and parses the response.
        
        :param addr: Memory address to read from
        :return: Value at the specified address as LC3Value
        :raises ValueError: If response cannot be parsed
        
        Example:
            >>> value = sim.read_mem(LC3Value('x3000'))
            >>> print(value)  # e.g., x1234
        """
        raw = self.send_command(f'translate {str(addr)}')
        # Parse "Address x0300 has value x0065."
        pattern = r'Address\s+x[\da-fA-F]+\s+has\s+value\s+(x[\da-fA-F]+)'
        match = re.search(pattern, raw)
        if match:
            return LC3Value(match.group(1))
        raise ValueError(f"Failed to parse memory read response: {raw}")

    def read_regs(self) -> LC3Regs:
        """
        Read all register values from the simulator.
        
        Uses the 'printregs' command to get current register state.
        
        :return: LC3Regs object containing all register values
        
        Example:
            >>> regs = sim.read_regs()
            >>> print(regs.R0, regs.R1)
        """
        raw = self.send_command('printregs')
        reg_dict = self._parse_registers(raw)
        return LC3Regs(reg_dict)

    def _parse_registers(self, output_str):
        """
        Parse register values from printregs output.
        
        :param output_str: Raw output from printregs command
        :return: Dictionary mapping register names to LC3Value objects
        """
        pattern = r'(\w+)=(x[\da-fA-F]+)'
        matches = re.findall(pattern, output_str)
        reg_dict = {}
        for key, val in matches:
            reg_dict[key] = LC3Value(val)
        return reg_dict

    def set_reg(self, reg: str, data: LC3Value):
        """
        Set a register to a specific value.
        
        :param reg: Register name (e.g., 'R0', 'R1', 'PC', 'PSR')
        :param data: Value to set
        
        Example:
            >>> sim.set_reg('R0', LC3Value('xABCD'))
            >>> sim.set_reg('PC', LC3Value('x3000'))
        """
        self.send_command(f'r {reg} {str(data)}')
    
    def sim_continue(self):
        """
        Run the program until HALT instruction.
        
        Randomizes registers before running to help catch uninitialized
        register bugs, then executes 'continue' command.
        
        :return: LC3Response object with program output and final register state
        
        Example:
            >>> response = sim.sim_continue()
            >>> print(response.raw_resp)  # Program output
            >>> print(response.regs.R0)   # Final R0 value
        """
        self.randomize_reg()
        raw = self.send_command('continue')
        return LC3Response(raw)


class LC3RandomGenTests:
    """
    Framework for running parallel randomized test cases.
    
    Subclass this and override run_case() to implement your test logic.
    Tests are executed in parallel using ThreadPoolExecutor for faster execution.
    
    Attributes:
        test_nums (int): Number of test cases to run
        max_workers (int): Maximum parallel workers
        passed_count (int): Number of passed tests
        failed_count (int): Number of failed tests
        failed_cases (list): List of failed case details
    
    Example:
        >>> class MyTests(LC3RandomGenTests):
        ...     def run_case(self, case_num):
        ...         # Your test logic here
        ...         return True  # or False
        >>> tests = MyTests(test_nums=100, max_workers=8)
        >>> tests.run_all()
    """
    
    class Colors:
        """ANSI color codes for terminal output."""
        HEADER = '\033[95m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        RESET = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'

    def __init__(self, test_nums=100, max_workers=None):
        """
        Initialize the parallel random test framework.
        
        :param test_nums: Number of test cases to run (default: 100)
        :param max_workers: Maximum parallel workers (default: min(32, cpu_count + 4))
        """
        self.test_nums = test_nums
        self.max_workers = max_workers
        self.passed_count = 0
        self.failed_count = 0
        self.failed_cases = []
        self.start_time = 0
        self.end_time = 0
        self._lock = threading.Lock()
        self._completed = 0

    def run_case(self, case_num):
        """
        Execute a single test case. Override this in subclass.
        
        :param case_num: Current test number (can be used as random seed)
        :return: True for pass, False for fail (or raise exception)
        
        Example:
            >>> def run_case(self, case_num):
            ...     random.seed(case_num)  # For reproducibility
            ...     # Generate test data, run simulation, check results
            ...     return actual == expected
        """
        import random
        if random.random() < 0.05:
            if random.random() < 0.5:
                return False
            else:
                raise ValueError("Simulated Exception")
        return True

    def _run_single_case(self, case_num):
        """
        Internal wrapper to run a single test case and capture result.
        
        :param case_num: Test case number
        :return: Tuple of (case_num, passed: bool, error_msg or None)
        """
        try:
            is_pass = self.run_case(case_num)
            if is_pass:
                return (case_num, True, None)
            else:
                return (case_num, False, "Assertion Failed (Returned False)")
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            return (case_num, False, error_msg)

    def _print_progress(self, current, total, bar_length=40):
        """
        Print a real-time progress bar to stdout.
        
        :param current: Current progress count
        :param total: Total count
        :param bar_length: Width of the progress bar in characters
        """
        percent = float(current) * 100 / total
        arrow = '=' * int(percent / 100 * bar_length - 1) + '>'
        spaces = ' ' * (bar_length - len(arrow))
        sys.stdout.write(f'\r{self.Colors.CYAN}Progress: [{arrow}{spaces}] {percent:.1f}% ({current}/{total}){self.Colors.RESET}')
        sys.stdout.flush()

    def run_all(self):
        """
        Execute all test cases in parallel.
        
        Uses ThreadPoolExecutor to run tests concurrently, displaying
        a progress bar and generating a final report.
        """
        print(f"{self.Colors.HEADER}{self.Colors.BOLD}>>> Starting LC3 Parallel Random Tests ({self.test_nums} test cases)...{self.Colors.RESET}")
        
        if self.max_workers is None:
            self.max_workers = min(32, (os.cpu_count() or 1) + 4)
        
        print(f"{self.Colors.CYAN}Using {self.max_workers} parallel workers{self.Colors.RESET}\n")
        
        self.start_time = time.time()
        self._completed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._run_single_case, i): i for i in range(1, self.test_nums + 1)}
            
            for future in as_completed(futures):
                case_num, passed, error_msg = future.result()
                
                with self._lock:
                    if passed:
                        self.passed_count += 1
                    else:
                        self.failed_count += 1
                        self.failed_cases.append({'id': case_num, 'reason': error_msg})
                    
                    self._completed += 1
                    self._print_progress(self._completed, self.test_nums)

        self.end_time = time.time()
        print("\n")
        
        self.failed_cases.sort(key=lambda x: x['id'])
        self.report()

    def report(self):
        """
        Print the final test report with statistics and failure details.
        
        Shows duration, throughput, pass/fail counts, and details of
        failed test cases (up to 10).
        """
        duration = self.end_time - self.start_time
        
        print(f"{self.Colors.HEADER}{'='*60}{self.Colors.RESET}")
        print(f"{self.Colors.BOLD}Test Report (Parallel){self.Colors.RESET}")
        print(f"{self.Colors.HEADER}{'='*60}{self.Colors.RESET}")
        
        print(f"Duration:     {duration:.4f} seconds")
        print(f"Avg Time:     {duration/self.test_nums*1000:.2f} ms/case")
        print(f"Throughput:   {self.test_nums/duration:.1f} cases/sec")
        
        print(f"Total:        {self.test_nums}")
        print(f"{self.Colors.GREEN}Passed:       {self.passed_count}{self.Colors.RESET}")
        
        if self.failed_count > 0:
            print(f"{self.Colors.RED}Failed:       {self.failed_count}{self.Colors.RESET}")
            print(f"{self.Colors.YELLOW}Pass Rate:    {self.passed_count/self.test_nums*100:.2f}%{self.Colors.RESET}")
            
            print(f"\n{self.Colors.RED}>>> Failure Details:{self.Colors.RESET}")
            print(f"{'-'*60}")
            print(f"{'Case ID':<10} | {'Error Reason'}")
            print(f"{'-'*60}")
            
            for fail in self.failed_cases[:10]:
                print(f"Case {fail['id']:<5} | {fail['reason']}")
            
            if len(self.failed_cases) > 10:
                print(f"... ({len(self.failed_cases)-10} more failures not shown)")
        else:
            print(f"\n{self.Colors.GREEN}{self.Colors.BOLD}🎉 All Tests Passed! 🎉{self.Colors.RESET}")

        print(f"{self.Colors.HEADER}{'='*60}{self.Colors.RESET}\n")


class LC3SequenceTest:
    """
    Framework for running sequential named test cases.
    
    Useful for boundary tests, edge cases, or specific scenarios where
    each test has a descriptive name and runs sequentially.
    
    Attributes:
        name (str): Name of the test suite
        test_cases (list): List of (name, test_func) tuples
        passed_count (int): Number of passed tests
        failed_count (int): Number of failed tests
        failed_cases (list): List of failed case details
    
    Example:
        >>> tests = LC3SequenceTest("Boundary Tests")
        >>> @tests.test("Empty input")
        ... def test_empty():
        ...     return True
        >>> tests.run_all()
    """
    
    class Colors:
        """ANSI color codes for terminal output."""
        HEADER = '\033[95m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        RESET = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'

    def __init__(self, name="LC3 Sequence Test"):
        """
        Initialize the sequence test framework.
        
        :param name: Name of the test suite (displayed in output)
        """
        self.name = name
        self.test_cases = []
        self.passed_count = 0
        self.failed_count = 0
        self.failed_cases = []
        self.start_time = 0
        self.end_time = 0

    def add_test(self, name, test_func):
        """
        Add a test case to the sequence.
        
        :param name: Descriptive name for the test case
        :param test_func: Callable that returns True for pass, False for fail
        :return: self (for method chaining)
        
        Example:
            >>> tests.add_test("Test A", lambda: True)
            >>> tests.add_test("Test B", my_test_function)
        """
        self.test_cases.append((name, test_func))
        return self

    def test(self, name):
        """
        Decorator to add a test function.
        
        :param name: Descriptive name for the test case
        :return: Decorator function
        
        Example:
            >>> @tests.test("My Test Name")
            ... def my_test():
            ...     return True
        """
        def decorator(func):
            self.add_test(name, func)
            return func
        return decorator

    def run_all(self):
        """
        Execute all registered test cases sequentially.
        
        Prints a table showing each test result and timing,
        then generates a summary report.
        """
        total = len(self.test_cases)
        print(f"{self.Colors.HEADER}{self.Colors.BOLD}>>> Starting {self.name} ({total} test cases)...{self.Colors.RESET}\n")
        print(f"{'-'*70}")
        print(f"{'#':<4} {'Test Name':<45} {'Result':<10} {'Time'}")
        print(f"{'-'*70}")
        
        self.start_time = time.time()
        
        for idx, (test_name, test_func) in enumerate(self.test_cases, 1):
            case_start = time.time()
            try:
                result = test_func()
                case_duration = (time.time() - case_start) * 1000
                
                if result:
                    self.passed_count += 1
                    status = f"{self.Colors.GREEN}PASS{self.Colors.RESET}"
                else:
                    self.failed_count += 1
                    self.failed_cases.append({'name': test_name, 'reason': "Returned False"})
                    status = f"{self.Colors.RED}FAIL{self.Colors.RESET}"
                    
            except Exception as e:
                case_duration = (time.time() - case_start) * 1000
                self.failed_count += 1
                error_msg = f"{type(e).__name__}: {str(e)}"
                self.failed_cases.append({'name': test_name, 'reason': error_msg})
                status = f"{self.Colors.RED}ERROR{self.Colors.RESET}"

            display_name = test_name[:42] + "..." if len(test_name) > 45 else test_name
            print(f"{idx:<4} {display_name:<45} {status:<19} {case_duration:.2f}ms")

        self.end_time = time.time()
        print(f"{'-'*70}\n")
        self.report()

    def report(self):
        """
        Print the final test report with statistics and failure details.
        
        :return: True if all tests passed, False otherwise
        """
        duration = self.end_time - self.start_time
        total = len(self.test_cases)
        
        print(f"{self.Colors.HEADER}{'='*60}{self.Colors.RESET}")
        print(f"{self.Colors.BOLD}Test Report: {self.name}{self.Colors.RESET}")
        print(f"{self.Colors.HEADER}{'='*60}{self.Colors.RESET}")
        
        print(f"Duration:     {duration:.4f} seconds")
        if total > 0:
            print(f"Avg Time:     {duration/total*1000:.2f} ms/case")
        
        print(f"Total:        {total}")
        print(f"{self.Colors.GREEN}Passed:       {self.passed_count}{self.Colors.RESET}")
        
        if self.failed_count > 0:
            print(f"{self.Colors.RED}Failed:       {self.failed_count}{self.Colors.RESET}")
            print(f"{self.Colors.YELLOW}Pass Rate:    {self.passed_count/total*100:.2f}%{self.Colors.RESET}")
            
            print(f"\n{self.Colors.RED}>>> Failure Details:{self.Colors.RESET}")
            print(f"{'-'*60}")
            print(f"{'Test Name':<35} | {'Error Reason'}")
            print(f"{'-'*60}")
            
            for fail in self.failed_cases:
                name = fail['name'][:32] + "..." if len(fail['name']) > 35 else fail['name']
                print(f"{name:<35} | {fail['reason']}")
        else:
            print(f"\n{self.Colors.GREEN}{self.Colors.BOLD}🎉 All Tests Passed! 🎉{self.Colors.RESET}")

        print(f"{self.Colors.HEADER}{'='*60}{self.Colors.RESET}\n")
        
        return self.failed_count == 0


# --- Import Welcome Message ---
_welcome_printed = False

def _print_welcome():
    global _welcome_printed
    if not _welcome_printed:
        print("Welcome to use LC3 Test Framework. Designed by qiufuyu. Github: qiufuyu123/lc3test")
        _welcome_printed = True

_print_welcome()

# --- Usage Example ---

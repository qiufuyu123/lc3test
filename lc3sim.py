import pexpect
import sys,os
import re
import uuid
import difflib
class LC3Value:
    def __init__(self, value):
        """
        Initialize an LC3 value
        :param value: Can be an integer (123, 0x1234) or string ('x1234', '1234')
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
                # If you want decimal by default, change to int(value)
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
        return f"{self._value:04X}"
    def to_bytes(self):
        """
        Export as 2-byte Big-Endian bytes object
        LC-3 is a big-endian machine (high byte first)
        """
        # length=2: two bytes
        # byteorder='big': high byte first (x40 before 00)
        return self._value.to_bytes(2, byteorder='big')
    def __int__(self):
        """Support int(obj)"""
        return self._value

    def __str__(self):
        """Support str(obj) -> returns 'x1234' format"""
        return f"x{self._value:04X}"

    def __repr__(self):
        """Display when printing directly in console"""
        return f"LC3Value({self.__str__()})"

    def __eq__(self, other):
        """Support == comparison"""
        if isinstance(other, LC3Value):
            return self._value == other._value
        if isinstance(other, int):
            return self._value == other
        if isinstance(other, str):
            return self._value == LC3Value(other)._value
        return False

    def __add__(self, other):
        """Support addition, returns LC3Value"""
        val = other
        if isinstance(other, LC3Value):
            val = other._value
        return LC3Value(self._value + val)

    @property
    def signed(self):
        """
        Get 16-bit signed two's complement value
        Example: xFFFF -> -1
        """
        if self._value & 0x8000: # Check sign bit (bit 15)
            return self._value - 0x10000
        return self._value

class LC3Obj:
    def __init__(self,orig:LC3Value,data:bytes):
        self.buffer = bytearray(orig.to_bytes())
        for item in data:
            self.buffer.append(0x00)
            self.buffer.append(item)
        self.buffer.append(0x00)
        self.buffer.append(0x00)
        self.tmp_path = ''
    def to_file(self):
        if self.tmp_path == '':
            name = f'tmp/{uuid.uuid4()}.obj'
            os.makedirs('tmp',exist_ok=True)
            with open(name,'wb') as f:
                f.write(self.buffer)
            self.tmp_path = name
        return self.tmp_path
    def __del__(self):
        if self.tmp_path:
            os.remove(self.tmp_path)

class LC3Regs:
    def __init__(self,reg_map={}):
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
    def __init__(self,raw_resp:str):
        segs = raw_resp.strip().split('--- halting the LC-3 ---')
        
        self.raw_resp = segs[0]
        self.raw_status = segs[1]
        regs = self.parse_registers(self.raw_status)
        self.regs = LC3Regs(regs)
    def parse_registers(self,output_str):
        # 1. Define regex pattern
        pattern = r'(\w+)=(x[\da-fA-F]+)'
        
        # 2. Find all matches
        # findall returns a list of tuples: [('PC', 'x0494'), ('IR', 'xB1AE'), ...]
        matches = re.findall(pattern, output_str)
        
        # 3. Convert to dictionary (string format)
        # Result: {'PC': 'x0494', 'R0': 'x0000', ...}
        reg_dict_str = dict(matches)
        
        # 4. (Optional) Convert to integers for computation
        # LC3's xFFFF typically means -1 or 65535, here we treat as unsigned
        reg_dict_val = {}
        for key, val in matches:
            # Python recognizes hex with 0x prefix, replace x with 0x
            # Or use int(val[1:], 16) to skip the first character
            reg_dict_val[key] = LC3Value(val)
            
        return reg_dict_val
    def diff_resp(self, expect_txt: str):
        # 1. Data cleaning: split by lines, strip whitespace
        expect_lines = [line.strip() for line in expect_txt.strip().splitlines()]
        actual_lines = [line.strip() for line in self.raw_resp.strip().splitlines()]

        # 2. Quick check: if identical, return True immediately
        if expect_lines == actual_lines:
            return True

        # 3. Prepare print format
        # Calculate total lines (take max of both to handle missing lines)
        max_lines = max(len(expect_lines), len(actual_lines))
        
        # Calculate max width for expected column for alignment
        # If expect_lines is empty, default width is 10
        max_width = max([len(line) for line in expect_lines]) if expect_lines else 10
        col_width = max_width + 4  # Add some extra spacing

        # ANSI color definitions
        GREEN = '\033[92m'
        RED = '\033[91m'
        RESET = '\033[0m'
        
        print("\n" + "="*60)
        print(f"❌  (Diff Report)")
        # Print header
        print(f"{'Line':<5} {'Expected (Correct)':<{col_width}} {'Actual (Original)'}")
        print("-" * (col_width + 30))

        # 4. Iterate and print line by line
        for i in range(max_lines):
            # Get current line content, show <MISSING> if index out of bounds
            exp_str = expect_lines[i] if i < len(expect_lines) else "<MISSING>"
            act_str = actual_lines[i] if i < len(actual_lines) else "<MISSING>"

            # Check if they match
            is_match = (exp_str == act_str)

            # --- Color logic ---
            # 1. Line number color: green if match, red if different
            color_line = GREEN if is_match else RED
            
            # 2. Expected value color: always green (reference)
            color_exp = GREEN
            
            # 3. Actual value color: green if correct, red if wrong
            color_act = GREEN if is_match else RED

            # --- Formatted print ---
            # Tip: first pad the string with ljust(width), then add color
            # If you add color first then pad, Python counts color codes in length, breaking alignment
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
        return f'''
--- Raw Content ---
{self.raw_resp}
--- Regs ---
{self.regs}
        '''
class LC3Sim:
    def __init__(self):
        self.child = pexpect.spawn('lc3sim', encoding='utf-8')
        # self.child.logfile_read = sys.stdout
        self.wait_for_input()
    def wait_for_input(self)->str:
        index = self.child.expect(['\(lc3sim\)', pexpect.EOF, pexpect.TIMEOUT])
        if index > 0:
            raise Exception("expect EOF or timeout!")
        tmp= self.child.before
        # print(tmp)
        return tmp
    def before(self):
        return self.child.before
    
    def send_command(self,command):
        self.child.sendline(command)
        return self.wait_for_input().replace(command,'').strip()
    def set_pc(self,pc:LC3Value):
        return self.send_command(f'r pc {str(pc)}')
    def load_file(self,file):
        return self.send_command(f'file {file}')
    
    def sim_continue(self):
        raw= self.send_command('continue')
        return LC3Response(raw)
    
import time
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class LC3RandomGenTests:
    # --- ANSI Color Definitions ---
    class Colors:
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
        Initialize the parallel random test framework
        :param test_nums: Number of test cases to run
        :param max_workers: Max parallel workers (default: min(32, cpu_count + 4))
        """
        self.test_nums = test_nums
        self.max_workers = max_workers
        self.passed_count = 0
        self.failed_count = 0
        self.failed_cases = []  # Record failed case IDs and reasons
        self.start_time = 0
        self.end_time = 0
        self._lock = threading.Lock()  # Thread lock for counters
        self._completed = 0  # Track completed tests for progress

    def run_case(self, case_num):
        """
        [Override in subclass] Execute a single test case
        :param case_num: Current test number (seed)
        :return: True for pass, False for fail (or raise exception)
        """
        # Default simulation: 95% pass rate, simulating some failures
        import random
        if random.random() < 0.05:
            # Simulate random failure
            if random.random() < 0.5:
                return False  # Logic error returns False
            else:
                raise ValueError("Simulated Exception")  # Simulate crash
        return True

    def _run_single_case(self, case_num):
        """
        Internal wrapper to run a single test case and return result
        :param case_num: Test case number
        :return: Tuple of (case_num, passed, error_msg or None)
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
        Print real-time progress bar (no newline)
        """
        percent = float(current) * 100 / total
        arrow = '=' * int(percent / 100 * bar_length - 1) + '>'
        spaces = ' ' * (bar_length - len(arrow))

        # \r moves cursor to line start for in-place refresh
        sys.stdout.write(f'\r{self.Colors.CYAN}Progress: [{arrow}{spaces}] {percent:.1f}% ({current}/{total}){self.Colors.RESET}')
        sys.stdout.flush()

    def run_all(self):
        """
        Execute all test cases in parallel using ThreadPoolExecutor
        """
        print(f"{self.Colors.HEADER}{self.Colors.BOLD}>>> Starting LC3 Parallel Random Tests ({self.test_nums} test cases)...{self.Colors.RESET}")
        
        # Determine worker count
        if self.max_workers is None:
            import os
            self.max_workers = min(32, (os.cpu_count() or 1) + 4)
        
        print(f"{self.Colors.CYAN}Using {self.max_workers} parallel workers{self.Colors.RESET}\n")
        
        self.start_time = time.time()
        self._completed = 0
        
        # Submit all tasks to thread pool
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all test cases
            futures = {executor.submit(self._run_single_case, i): i for i in range(1, self.test_nums + 1)}
            
            # Process results as they complete
            for future in as_completed(futures):
                case_num, passed, error_msg = future.result()
                
                with self._lock:
                    if passed:
                        self.passed_count += 1
                    else:
                        self.failed_count += 1
                        self.failed_cases.append({'id': case_num, 'reason': error_msg})
                    
                    self._completed += 1
                    # Update progress bar
                    self._print_progress(self._completed, self.test_nums)

        self.end_time = time.time()
        # Newline after completion
        print("\n")
        
        # Sort failed cases by ID for consistent output
        self.failed_cases.sort(key=lambda x: x['id'])
        
        self.report()

    def report(self):
        duration = self.end_time - self.start_time
        
        print(f"{self.Colors.HEADER}{'='*60}{self.Colors.RESET}")
        print(f"{self.Colors.BOLD}Test Report (Parallel){self.Colors.RESET}")
        print(f"{self.Colors.HEADER}{'='*60}{self.Colors.RESET}")
        
        # Print summary
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
            
            # Only show first 10 errors to prevent flooding
            for fail in self.failed_cases[:10]:
                print(f"Case {fail['id']:<5} | {fail['reason']}")
            
            if len(self.failed_cases) > 10:
                print(f"... ({len(self.failed_cases)-10} more failures not shown)")
        else:
            print(f"\n{self.Colors.GREEN}{self.Colors.BOLD}🎉 All Tests Passed! 🎉{self.Colors.RESET}")

        print(f"{self.Colors.HEADER}{'='*60}{self.Colors.RESET}\n")


class LC3SequenceTest:
    """
    A test framework for running individual/sequential test cases.
    Useful for boundary tests, edge cases, or specific scenarios.
    Each test case has a name and a test function.
    """
    # --- ANSI Color Definitions ---
    class Colors:
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
        Initialize the sequence test framework
        :param name: Name of the test suite
        """
        self.name = name
        self.test_cases = []  # List of (name, test_func) tuples
        self.passed_count = 0
        self.failed_count = 0
        self.failed_cases = []
        self.start_time = 0
        self.end_time = 0

    def add_test(self, name, test_func):
        """
        Add a test case to the sequence
        :param name: Descriptive name for the test case
        :param test_func: A callable that returns True for pass, False for fail
        """
        self.test_cases.append((name, test_func))
        return self

    def test(self, name):
        """
        Decorator to add a test function
        Usage:
            @seq_test.test("My Test Name")
            def my_test():
                return True  # or False
        """
        def decorator(func):
            self.add_test(name, func)
            return func
        return decorator

    def run_all(self):
        """
        Execute all registered test cases sequentially
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
                case_duration = (time.time() - case_start) * 1000  # ms
                
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

            # Print result for this test case
            # Truncate long test names
            display_name = test_name[:42] + "..." if len(test_name) > 45 else test_name
            print(f"{idx:<4} {display_name:<45} {status:<19} {case_duration:.2f}ms")

        self.end_time = time.time()
        print(f"{'-'*70}\n")
        self.report()

    def report(self):
        """
        Print final test report summary
        """
        duration = self.end_time - self.start_time
        total = len(self.test_cases)
        
        print(f"{self.Colors.HEADER}{'='*60}{self.Colors.RESET}")
        print(f"{self.Colors.BOLD}Test Report: {self.name}{self.Colors.RESET}")
        print(f"{self.Colors.HEADER}{'='*60}{self.Colors.RESET}")
        
        # Print summary
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
            
            # Show all failures for sequence tests (usually fewer cases)
            for fail in self.failed_cases:
                name = fail['name'][:32] + "..." if len(fail['name']) > 35 else fail['name']
                print(f"{name:<35} | {fail['reason']}")
        else:
            print(f"\n{self.Colors.GREEN}{self.Colors.BOLD}🎉 All Tests Passed! 🎉{self.Colors.RESET}")

        print(f"{self.Colors.HEADER}{'='*60}{self.Colors.RESET}\n")
        
        return self.failed_count == 0


# --- Usage Example ---

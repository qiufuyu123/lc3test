from lc3sim import *
import os,sys
import random
import string

def generate_and_count(length):
    # --- 1. Generate random string ---
    # Define character pool: includes uppercase/lowercase letters, digits, and punctuation
    # This ensures the generated string contains both letters and "other characters"
    char_pool = string.ascii_letters + string.digits + string.punctuation
    
    # random.choices picks k characters from the pool, join merges them into a string
    random_str = ''.join(random.choices(char_pool, k=length))

    # print(f"\n>>> Generated random string (length {length}):")
    # print(f"「{random_str}」\n")

    # --- 2. Initialize statistics ---
    # Create a dictionary with keys 'A' to 'Z', all initialized to 0
    # chr(65) is 'A', chr(90) is 'Z'
    letter_stats = {chr(i): 0 for i in range(65, 91)}
    letter_stats['@']=0

    # --- 3. Iterate and count ---
    for char in random_str:
        # Check if it's a letter (a-z or A-Z)
        if char.isalpha():
            # Convert to uppercase as the key
            upper_char = char.upper()
            letter_stats[upper_char] += 1
        else:
            # Not a letter (digits, symbols, spaces, etc.)
            letter_stats['@'] += 1

    # --- 4. Format output ---
    tmp_at = LC3Value(letter_stats["@"])
    desired_str = f'@ {tmp_at.h16raw()}\n'
    for i in range(26):
        ch = chr(ord('A')+i)
        val = LC3Value(letter_stats[chr(ord('A')+i).upper()]).h16raw()
        desired_str += f'{ch.upper()} {val}\n'

    # Simple formatted output
    return random_str,desired_str,letter_stats


def generate_expected_output(input_str):
    """
    Generate expected output for a given input string
    """
    letter_stats = {chr(i): 0 for i in range(65, 91)}
    letter_stats['@'] = 0
    
    for char in input_str:
        if char.isalpha():
            letter_stats[char.upper()] += 1
        else:
            letter_stats['@'] += 1
    
    tmp_at = LC3Value(letter_stats["@"])
    desired_str = f'@ {tmp_at.h16raw()}\n'
    for i in range(26):
        ch = chr(ord('A') + i)
        val = LC3Value(letter_stats[ch]).h16raw()
        desired_str += f'{ch} {val}\n'
    
    return desired_str


def run_single_test(target, input_str):
    """
    Run a single test with given input string
    :param target: Path to the LC3 object file
    :param input_str: Input string to test
    :return: True if passed, False if failed
    """
    expected = generate_expected_output(input_str)
    obj = LC3Obj(LC3Value('x4000'), input_str.encode())
    
    sim = LC3Sim()
    sim.load_file(target)
    sim.load_file(obj.to_file())
    sim.set_pc(LC3Value('x3000'))
    ret = sim.sim_continue()
    return ret.diff_resp(expected)


class MP1LC3Test(LC3RandomGenTests):
    def set_target(self,target):
        self.target = target
    def run_case(self, case_num):
        # This is a simulated test logic
        # Assume we are testing the LC3 ADD instruction
        rd,rd_expect,rd_stats=generate_and_count(random.randint(100,500))
        obj = LC3Obj(LC3Value('x4000'),rd.encode())
        # print(rd)
        # print(rd_expect)
        
        sim = LC3Sim()
        sim.load_file(self.target)
        sim.load_file(obj.to_file())
        sim.set_pc(LC3Value('x3000'))
        ret = sim.sim_continue()
        return (ret.diff_resp(rd_expect))


def run_boundary_tests(target):
    """
    Run boundary/edge case tests for MP1
    """
    boundary_test = LC3SequenceTest("MP1 Boundary Tests")
    
    # --- Test 1: Empty string (only null terminator) ---
    @boundary_test.test("Empty string - no characters")
    def test_empty():
        return run_single_test(target, "")
    
    # --- Test 2: Single character tests ---
    @boundary_test.test("Single lowercase letter 'a'")
    def test_single_lower():
        return run_single_test(target, "a")
    
    @boundary_test.test("Single uppercase letter 'Z'")
    def test_single_upper():
        return run_single_test(target, "Z")
    
    @boundary_test.test("Single digit '5'")
    def test_single_digit():
        return run_single_test(target, "5")
    
    @boundary_test.test("Single special character '@'")
    def test_single_special():
        return run_single_test(target, "@")
    
    # --- Test 3: All same character ---
    @boundary_test.test("All same letter 'AAAA' (4 chars)")
    def test_all_same_letter():
        return run_single_test(target, "AAAA")
    
    @boundary_test.test("All same digit '9999' (4 chars)")
    def test_all_same_digit():
        return run_single_test(target, "9999")
    
    # --- Test 4: Alphabet boundary tests ---
    @boundary_test.test("First letter 'A' only")
    def test_first_letter():
        return run_single_test(target, "A")
    
    @boundary_test.test("Last letter 'Z' only")
    def test_last_letter():
        return run_single_test(target, "Z")
    
    @boundary_test.test("All 26 uppercase letters A-Z")
    def test_all_uppercase():
        return run_single_test(target, "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    
    @boundary_test.test("All 26 lowercase letters a-z")
    def test_all_lowercase():
        return run_single_test(target, "abcdefghijklmnopqrstuvwxyz")
    
    @boundary_test.test("Mixed case - same letters 'AaAaAa'")
    def test_mixed_case():
        return run_single_test(target, "AaAaAa")
    
    # --- Test 5: Non-letter character tests ---
    @boundary_test.test("All digits 0-9")
    def test_all_digits():
        return run_single_test(target, "0123456789")
    
    @boundary_test.test("Special characters only '!@#$%^&*()'")
    def test_special_chars():
        return run_single_test(target, "!@#$%^&*()")
    
    @boundary_test.test("Spaces only '     ' (5 spaces)")
    def test_spaces_only():
        return run_single_test(target, "     ")
    
    @boundary_test.test("Mixed: letters, digits, special 'Abc123!@#'")
    def test_mixed_all():
        return run_single_test(target, "Abc123!@#")
    
    # --- Test 6: ASCII boundary tests ---
    @boundary_test.test("Character before 'A' (ASCII 64 = '@')")
    def test_before_A():
        return run_single_test(target, "@")  # ASCII 64
    
    @boundary_test.test("Character after 'Z' (ASCII 91 = '[')")
    def test_after_Z():
        return run_single_test(target, "[")  # ASCII 91
    
    @boundary_test.test("Character before 'a' (ASCII 96 = '`')")
    def test_before_a():
        return run_single_test(target, "`")  # ASCII 96
    
    @boundary_test.test("Character after 'z' (ASCII 123 = '{')")
    def test_after_z():
        return run_single_test(target, "{")  # ASCII 123
    
    # --- Test 7: Length boundary tests ---
    @boundary_test.test("Very short string (1 char)")
    def test_length_1():
        return run_single_test(target, "X")
    
    @boundary_test.test("Short string (10 chars)")
    def test_length_10():
        return run_single_test(target, "AbCdEfGhIj")
    
    @boundary_test.test("Medium string (100 chars)")
    def test_length_100():
        return run_single_test(target, "A" * 50 + "b" * 50)
    
    @boundary_test.test("Long string (500 chars)")
    def test_length_500():
        return run_single_test(target, "Test" * 125)
    
    # --- Test 8: Edge patterns ---
    @boundary_test.test("Alternating letter/digit 'A1B2C3D4E5'")
    def test_alternating():
        return run_single_test(target, "A1B2C3D4E5")
    
    @boundary_test.test("Repeated pattern 'AbAbAbAbAb'")
    def test_repeated_pattern():
        return run_single_test(target, "AbAbAbAbAb")
    
    @boundary_test.test("Newline and tab characters")
    def test_whitespace():
        return run_single_test(target, "A\nB\tC")
    
    # Run all boundary tests
    boundary_test.run_all()
    return boundary_test.failed_count == 0


# --- Main program entry ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_mp1.py <target.obj> [--boundary-only]")
        sys.exit(1)
    
    target_file = sys.argv[1]
    boundary_only = "--boundary-only" in sys.argv
    
    if boundary_only:
        # Run only boundary tests
        print("Running boundary tests only...\n")
        run_boundary_tests(target_file)
    else:
        # Run boundary tests first
        print("=" * 60)
        print("Phase 1: Boundary Tests")
        print("=" * 60)
        boundary_passed = run_boundary_tests(target_file)
        
        # Then run random tests
        print("\n" + "=" * 60)
        print("Phase 2: Random Tests")
        print("=" * 60)
        test_inst = MP1LC3Test()
        test_inst.set_target(target_file)
        test_inst.run_all()

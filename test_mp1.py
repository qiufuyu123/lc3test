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
        
test_inst = MP1LC3Test()
test_inst.set_target(sys.argv[1])
test_inst.run_all()
# test_inst.report()
# --- Main program entry ---


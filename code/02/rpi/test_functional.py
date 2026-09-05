import time
from machine import I2C, Pin
import pins
from sieve import Sieve

def test_ring(sieve, name, modulus, ring_bits_16bytes, expected_votes):
    print(f"Testing {name}...")
    sieve.reset()
    sieve.set_ring(modulus, ring_bits_16bytes)
    sieve.arm()
    
    num_steps = 2 * modulus + 5
    
    all_pass = True
    for i in range(num_steps):
        sieve.step()
        time.sleep_us(1000)
        
        actual_vote = sieve.vote.value()
        expected = expected_votes[i % modulus]
        if actual_vote != expected:
            print(f"FAIL at step {i} (phase {i%modulus}): expected VOTE={expected}, got {actual_vote}")
            all_pass = False
            
    if all_pass:
        print(f"PASS: {name}")
    return all_pass

def main():
    i2c = I2C(0, scl=Pin(pins.PIN_SCL), sda=Pin(pins.PIN_SDA), freq=400000)
    req = Pin(pins.PIN_REQ, Pin.OUT)
    vote = Pin(pins.PIN_VOTE, Pin.IN, Pin.PULL_UP)
    
    s = Sieve(i2c, 0x20, req, vote)
    
    modulus = 11
    
    # 1. All-accept (all 1s)
    ring_all_accept = bytearray([0xFF] * 16)
    exp_all_accept = [1] * modulus
    
    # 2. All-reject (all 0s)
    ring_all_reject = bytearray([0x00] * 16)
    exp_all_reject = [0] * modulus
    
    # 3. Alternating (0xAA) = 10101010
    ring_alternating = bytearray([0xAA] * 16)
    exp_alternating = [ (1 if (i % 2 != 0) else 0) for i in range(modulus) ]
    
    # 4. Single set bit (e.g. only bit 2 is set)
    ring_single = bytearray([0x00] * 16)
    ring_single[0] = 0x04
    exp_single = [ (1 if i == 2 else 0) for i in range(modulus) ]
    
    print(f"Running functional tests with modulus={modulus} at ~1kHz...")
    all_pass = True
    all_pass &= test_ring(s, "All-accept", modulus, ring_all_accept, exp_all_accept)
    all_pass &= test_ring(s, "All-reject", modulus, ring_all_reject, exp_all_reject)
    all_pass &= test_ring(s, "Alternating", modulus, ring_alternating, exp_alternating)
    all_pass &= test_ring(s, "Single set bit", modulus, ring_single, exp_single)
    
    if all_pass:
        print("\nALL TESTS PASSED.")
    else:
        print("\nSOME TESTS FAILED.")

if __name__ == '__main__':
    main()

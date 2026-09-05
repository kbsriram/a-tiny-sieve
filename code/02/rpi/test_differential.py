import time
from machine import I2C, Pin
import pins
from sieve import Sieve
from sieve_runner import SieveRunner
import random

def generate_ring(modulus, accept_rate=0.5):
    ring_bits = bytearray([0] * 16)
    expected_votes = [0] * modulus
    for i in range(modulus):
        if random.random() < accept_rate:
            byte_idx = i // 8
            bit_idx = i % 8
            ring_bits[byte_idx] |= (1 << bit_idx)
            expected_votes[i] = 1
    return ring_bits, expected_votes

def test_moduli_configuration(runner, moduli, num_candidates=10000):
    configs = []
    py_configs = []
    for mod in moduli:
        ring_bits, exp_votes = generate_ring(mod, accept_rate=0.5)
        configs.append((mod, ring_bits))
        py_configs.append((mod, exp_votes))
        
    # Precompute expected survivor candidate indices in Python
    expected_survivors = []
    for k in range(num_candidates):
        survives = True
        for mod, exp_votes in py_configs:
            if exp_votes[k % mod] == 0:
                survives = False
                break
        if survives:
            expected_survivors.append(k)
            
    # Safely program, arm, and start the array via the orchestrator
    runner.configure_array(configs, start_candidate=0)
    
    t0 = time.ticks_us()
    n_expected = len(expected_survivors)
    hardware_survivors = [runner.next_survivor() for _ in range(n_expected)]
    t_elapsed_us = time.ticks_diff(time.ticks_us(), t0)
    
    last_cand = expected_survivors[-1] + 1 if expected_survivors else num_candidates
    rate_khz = (last_cand * 1000) / t_elapsed_us if t_elapsed_us > 0 else 0
    rej_rate = 100.0 * (1.0 - len(hardware_survivors) / last_cand) if last_cand > 0 else 0.0
    
    passed = (expected_survivors == hardware_survivors)
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] Moduli {moduli}: {n_expected} survivors in {last_cand} candidates "
          f"({t_elapsed_us/1000:.1f}ms, {rate_khz:.2f} kHz, {rej_rate:.2f}% rejected)")
    if not passed:
        print(f"  Exp[:10]: {expected_survivors[:10]}")
        print(f"  Got[:10]: {hardware_survivors[:10]}")
        print(f"  Exp[-5:]: {expected_survivors[-5:]}")
        print(f"  Got[-5:]: {hardware_survivors[-5:]}")
    return passed

def main():
    i2c = I2C(0, scl=Pin(pins.PIN_SCL), sda=Pin(pins.PIN_SDA), freq=400000)
    req_pin = Pin(pins.PIN_REQ, Pin.OUT)
    vote = Pin(pins.PIN_VOTE, Pin.IN, Pin.PULL_UP)
    
    devices = i2c.scan()
    print(f"I2C scan found devices at: {[hex(d) for d in devices]}")
    devices = [d for d in devices if d != 0x3c]
    
    if len(devices) == 0:
        print("No ATtiny sieves found on I2C bus.")
        return
        
    sieves = [Sieve(i2c, addr) for addr in devices]
    
    # Initialize SieveRunner as the array orchestrator
    runner = SieveRunner(req_pin, vote, sieves=sieves, sm_id=0, freq=5000000)
    
    num_candidates = 10000
    all_passed = True
    
    if len(sieves) == 1:
        test_moduli_list = [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 47, 64, 97, 127]
        print(f"Testing 1 sieve across {len(test_moduli_list)} moduli ({num_candidates} checks each at 50kHz)...")
        for mod in test_moduli_list:
            if not test_moduli_configuration(runner, [mod], num_candidates=num_candidates):
                all_passed = False
    else:
        moduli_combos = [
            [5, 7, 11, 13, 17][:len(sieves)],
            [19, 23, 29, 31, 37][:len(sieves)],
            [41, 43, 47, 53, 59][:len(sieves)],
            [61, 67, 71, 73, 79][:len(sieves)],
        ]
        print(f"Testing {len(sieves)} sieves across {len(moduli_combos)} combos ({num_candidates} checks each at 50kHz)...")
        for combo in moduli_combos:
            if not test_moduli_configuration(runner, combo, num_candidates=num_candidates):
                all_passed = False
                
    if all_passed:
        print("\nALL DIFFERENTIAL TESTS PASSED AT 50KHz.")
    else:
        print("\nDIFFERENTIAL TEST FAILED.")

if __name__ == '__main__':
    main()

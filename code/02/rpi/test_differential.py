import time
from machine import I2C, Pin
import rp2
import pins
from sieve import Sieve
import random

@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def req_pulse():
    wrap_target()
    pull(block)
    
    # 50 kHz -> 20 us period at freq=5_000_000 (200 ns per cycle)
    # HIGH Phase: 10 us total (50 cycles)
    set(pins, 1) [31]   # 6.4 us
    nop() [17]          # 3.6 us (total 10.0 us)
    
    # LOW Phase: 10 us total (50 cycles)
    set(pins, 0) [31]   # 6.4 us
    nop() [15]          # 3.2 us
    in_(pins, 1)        # 0.2 us: sample VOTE at the end of low phase (19.8 us)
    push(block)         # 0.2 us
    wrap()

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

def test_moduli_configuration(sieves, sm, moduli, num_candidates=2000):
    configs = []
    for i, s in enumerate(sieves):
        ring_bits, exp_votes = generate_ring(moduli[i], accept_rate=0.5)
        configs.append((moduli[i], ring_bits, exp_votes))
        
        s.reset()
        time.sleep_ms(2)
        s.set_ring(moduli[i], ring_bits)
        time.sleep_ms(2)
        
    for s in sieves:
        s.arm()
        time.sleep_ms(2)
        
    num_bytes = (num_candidates + 7) // 8
    expected_survivors = bytearray(num_bytes)
    hardware_survivors = bytearray(num_bytes)
    
    expected_count = 0
    for k in range(num_candidates):
        survives = True
        for mod, _, exp_votes in configs:
            if exp_votes[k % mod] == 0:
                survives = False
                break
        if survives:
            expected_survivors[k // 8] |= (1 << (k % 8))
            expected_count += 1
            
    t0 = time.ticks_us()
    hardware_count = 0
    for k in range(num_candidates):
        sm.put(1)
        vote_val = sm.get()
        if vote_val != 0:
            hardware_survivors[k // 8] |= (1 << (k % 8))
            hardware_count += 1
    t_elapsed_us = time.ticks_diff(time.ticks_us(), t0)
    rate_khz = (num_candidates * 1000) / t_elapsed_us if t_elapsed_us > 0 else 0
    
    passed = (expected_survivors == hardware_survivors)
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] Moduli {moduli}: {num_candidates} checks in {t_elapsed_us/1000:.1f}ms "
          f"({rate_khz:.2f} kHz), survivors={hardware_count}/{expected_count}")
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
        
    sieves = [Sieve(i2c, addr, req_pin, vote) for addr in devices]
    
    # StateMachine at 5 MHz (100 cycles per pulse = 50 kHz hardware stepping)
    sm = rp2.StateMachine(0, req_pulse, freq=5000000, set_base=req_pin, in_base=vote)
    sm.active(1)
    
    num_candidates = 2000
    all_passed = True
    
    if len(sieves) == 1:
        test_moduli_list = [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 47, 64, 97, 127]
        print(f"Testing 1 sieve across {len(test_moduli_list)} moduli ({num_candidates} checks each at 50kHz)...")
        for mod in test_moduli_list:
            if not test_moduli_configuration(sieves, sm, [mod], num_candidates=num_candidates):
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
            if not test_moduli_configuration(sieves, sm, combo, num_candidates=num_candidates):
                all_passed = False
                
    if all_passed:
        print("\nALL DIFFERENTIAL TESTS PASSED AT 50KHz.")
    else:
        print("\nDIFFERENTIAL TEST FAILED.")

if __name__ == '__main__':
    main()

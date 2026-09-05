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
    # Ensure at least one 1 and at least one 0 for a meaningful sieve
    if sum(expected_votes) == 0:
        ring_bits[0] |= 1
        expected_votes[0] = 1
    elif sum(expected_votes) == modulus:
        ring_bits[0] &= ~1
        expected_votes[0] = 0
    return ring_bits, expected_votes

def main():
    random.seed(42)
    i2c = I2C(0, scl=Pin(pins.PIN_SCL), sda=Pin(pins.PIN_SDA), freq=400000)
    req_pin = Pin(pins.PIN_REQ, Pin.OUT)
    vote = Pin(pins.PIN_VOTE, Pin.IN, Pin.PULL_UP)
    
    # Dynamically discover all ATtinys on the bus
    devices = i2c.scan()
    devices = [d for d in devices if d != 0x3c]
    n_tinys = len(devices)
    print(f"I2C scan detected {n_tinys} ATtiny sieve(s): {[hex(d) for d in devices]}")
    
    if n_tinys == 0:
        print("Error: No ATtiny sieves found.")
        return
        
    sieves = [Sieve(i2c, addr, req_pin, vote) for addr in devices]
    
    # StateMachine at 5 MHz (100 cycles = 50 kHz hardware stepping)
    sm = rp2.StateMachine(0, req_pulse, freq=5000000, set_base=req_pin, in_base=vote)
    sm.active(1)
    
    prime_moduli = [5, 7, 11, 13, 17, 19, 23, 29, 31]
    configs = []
    for i in range(n_tinys):
        mod = prime_moduli[i % len(prime_moduli)]
        ring_bits, exp_votes = generate_ring(mod, accept_rate=0.5)
        configs.append({
            'index': i,
            'addr': devices[i],
            'modulus': mod,
            'ring_bits': ring_bits,
            'exp_votes': exp_votes,
            'accept_count': sum(exp_votes),
            'single_rate': sum(exp_votes) / mod,
        })
        
    num_candidates = 10000
    num_bytes = (num_candidates + 7) // 8
    
    print("\nPre-configured sieve rings:")
    for c in configs:
        ones = c['accept_count']
        m = c['modulus']
        print(f"  Sieve @ {hex(c['addr'])}: mod {m:2d}, {ones}/{m} ones ({c['single_rate']*100:.1f}% accept)")
        
    results = []
    
    print(f"\nRunning progressive tests over {num_candidates} candidates at 50 kHz...")
    for k in range(1, n_tinys + 1):
        active_configs = configs[:k]
        active_sieves = sieves[:k]
        inactive_sieves = sieves[k:]
        
        # Configure and arm active sieves
        for i, s in enumerate(active_sieves):
            s.reset()
            time.sleep_ms(2)
            s.set_ring(active_configs[i]['modulus'], active_configs[i]['ring_bits'])
            time.sleep_ms(2)
            s.arm()
            time.sleep_ms(2)
            
        # Disarm inactive sieves (so they never veto)
        for s in inactive_sieves:
            s.reset()
            time.sleep_ms(2)
            
        # Compute expected survivors in Python
        expected_survivors = bytearray(num_bytes)
        expected_count = 0
        for cand in range(num_candidates):
            survives = True
            for c in active_configs:
                if c['exp_votes'][cand % c['modulus']] == 0:
                    survives = False
                    break
            if survives:
                expected_survivors[cand // 8] |= (1 << (cand % 8))
                expected_count += 1
                
        # Run hardware sieves via PIO at 50 kHz
        hardware_survivors = bytearray(num_bytes)
        hardware_count = 0
        t0 = time.ticks_us()
        for cand in range(num_candidates):
            sm.put(1)
            v = sm.get()
            if v != 0:
                hardware_survivors[cand // 8] |= (1 << (cand % 8))
                hardware_count += 1
        elapsed_us = time.ticks_diff(time.ticks_us(), t0)
        rate_khz = (num_candidates * 1000) / elapsed_us if elapsed_us > 0 else 0
        
        matches = (expected_survivors == hardware_survivors)
        obs_rate = (hardware_count / num_candidates) * 100
        exp_rate = (expected_count / num_candidates) * 100
        
        # Theoretical independent probability
        theo_rate = 1.0
        for c in active_configs:
            theo_rate *= c['single_rate']
        theo_rate *= 100
        
        active_moduli = [c['modulus'] for c in active_configs]
        status = "PASS" if matches else "FAIL"
        print(f"[{status}] {k}/{n_tinys} tinys active (moduli {active_moduli}):")
        print(f"       Observed survivors: {hardware_count}/{num_candidates} ({obs_rate:.2f}%)")
        print(f"       Expected survivors: {expected_count}/{num_candidates} ({exp_rate:.2f}%)")
        print(f"       Theoretical rate:   {theo_rate:.2f}%")
        print(f"       Throughput:         {elapsed_us/1000:.1f}ms ({rate_khz:.2f} kHz)\n")
        
        results.append({
            'k': k,
            'moduli': active_moduli,
            'hardware_count': hardware_count,
            'expected_count': expected_count,
            'obs_rate': obs_rate,
            'exp_rate': exp_rate,
            'theo_rate': theo_rate,
            'matches': matches,
        })
        
    print("=" * 65)
    print(f"{'Active Tinys':<14}{'Moduli':<16}{'Observed Rate':<16}{'Theoretical':<14}{'Status'}")
    print("-" * 65)
    for r in results:
        mod_str = str(r['moduli'])
        obs_str = f"{r['obs_rate']:.2f}% ({r['hardware_count']})"
        theo_str = f"{r['theo_rate']:.2f}%"
        status_str = "PASS" if r['matches'] else "FAIL"
        print(f"{r['k']:<14}{mod_str:<16}{obs_str:<16}{theo_str:<14}{status_str}")
    print("=" * 65)

if __name__ == '__main__':
    main()

import time
from machine import I2C, Pin
import pins
from sieve import Sieve
from sieve_runner import SieveRunner

def main():
    print("Testing 64-Bit Continuous Sieve Rollover and Streaming...")
    i2c = I2C(0, scl=Pin(pins.PIN_SCL), sda=Pin(pins.PIN_SDA), freq=400000)
    req_pin = Pin(pins.PIN_REQ, Pin.OUT)
    vote = Pin(pins.PIN_VOTE, Pin.IN, Pin.PULL_UP)
    
    devices = [d for d in i2c.scan() if d != 0x3c]
    if not devices:
        print("FAIL: No ATtiny sieves found.")
        return
        
    sieves = [Sieve(i2c, addr) for addr in devices]
    runner = SieveRunner(req_pin, vote, sieves=sieves, sm_id=0, freq=5000000)
    
    # Configure all sieves to all-accept via orchestrator
    all_accept = bytearray([0xFF] * 16)
    start_cand = 0xFFFFFFFD
    runner.configure_array([(5, all_accept)] * len(sieves), start_candidate=start_cand)
    
    # Stream 1: Fetch 6 survivors spanning the 32-bit rollover boundary
    # Expected indices in 64-bit:
    # 0xFFFFFFFD, 0xFFFFFFFE, 0xFFFFFFFF, 0x100000000, 0x100000001, 0x100000002
    expected_stream1 = [0xFFFFFFFD, 0xFFFFFFFE, 0xFFFFFFFF, 0x100000000, 0x100000001, 0x100000002]
    print(f"\nStreaming 6 survivors across 32-bit boundary from {hex(start_cand)}...")
    t0 = time.ticks_us()
    survivors1 = [runner.next_survivor() for _ in range(6)]
    t1 = time.ticks_diff(time.ticks_us(), t0)
    
    print(f"  Received: {[hex(x) for x in survivors1]}")
    print(f"  Expected: {[hex(x) for x in expected_stream1]}")
    print(f"  Elapsed time: {t1} us")
    
    pass1 = (survivors1 == expected_stream1)
    
    # Stream 2: Fetch next 4 survivors continuously in Epoch 1
    # Expected indices: 0x100000003, 0x100000004, 0x100000005, 0x100000006
    expected_stream2 = [0x100000003, 0x100000004, 0x100000005, 0x100000006]
    print(f"\nStreaming next 4 survivors continuously in 64-bit space...")
    survivors2 = [runner.next_survivor() for _ in range(4)]
    print(f"  Received: {[hex(x) for x in survivors2]}")
    print(f"  Expected: {[hex(x) for x in expected_stream2]}")
    
    pass2 = (survivors2 == expected_stream2)
    
    if pass1 and pass2:
        print("\nPASS: 64-bit continuous rollover verified successfully.")
    else:
        print("\nFAIL: 64-bit rollover verification failed.")

if __name__ == '__main__':
    main()

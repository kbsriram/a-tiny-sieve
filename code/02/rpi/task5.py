from machine import Pin, I2C
import pins
from sieve import Sieve
from time import sleep

def main():
    i2c = I2C(0, scl=Pin(pins.PIN_SCL), sda=Pin(pins.PIN_SDA), freq=400000)
    req = Pin(pins.PIN_REQ, Pin.OUT)
    vote = Pin(pins.PIN_VOTE, Pin.IN, Pin.PULL_UP)
    
    s = Sieve(i2c, 0x20, req, vote)
    
    print("Resetting...")
    s.reset()
    sleep(0.1)
    
    print("Setting ring (modulus 4, bits: 1 1 0 1)")
    bits = bytearray(16)
    bits[0] = 0x0B # 1101 in binary (bit 0=1, bit 1=1, bit 2=0, bit 3=1)
    s.set_ring(4, bits)
    
    print("Arming...")
    s.arm()
    sleep(0.1)
    
    print("Stepping through the ring...")
    for i in range(8):
        s.step()
        v = s.vote.value()
        expected = 1 if (0x0B & (1 << (i % 4))) else 0
        print(f"Candidate {i} (phase {i%4}, expected {expected}): VOTE={v}")

if __name__ == '__main__':
    main()

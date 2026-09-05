from machine import Pin, I2C
from time import sleep_us
import pins

class Sieve:
    def __init__(self, i2c: I2C, addr: int, req_pin: Pin, vote_pin: Pin):
        self.i2c = i2c
        self.addr = addr
        self.req = req_pin
        self.vote = vote_pin
        
        self.req.init(Pin.OUT, value=0)
        self.vote.init(Pin.IN, Pin.PULL_UP)

    def set_ring(self, modulus: int, bits: bytearray):
        if len(bits) != 16:
            raise ValueError("bits must be 16 bytes")
        buf = bytearray(18)
        buf[0] = 0x01
        buf[1] = modulus
        buf[2:18] = bits
        self.i2c.writeto(self.addr, buf)
        
    def reset(self):
        self.i2c.writeto(self.addr, b'\x02')
        
    def arm(self):
        self.i2c.writeto(self.addr, b'\x03')
        
    def step(self):
        self.req.value(1)
        sleep_us(1)
        self.req.value(0)

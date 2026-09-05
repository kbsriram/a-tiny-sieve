from machine import I2C

class Sieve:
    """I2C device driver for an individual ATtiny412 Lehmer sieve node."""
    def __init__(self, i2c: I2C, addr: int, req_pin=None, vote_pin=None):
        self.i2c = i2c
        self.addr = addr

    def set_ring(self, modulus: int, bits: bytearray):
        """Programs the ring modulus (1-128) and 16-byte truth table."""
        if len(bits) != 16:
            raise ValueError("bits must be 16 bytes")
        buf = bytearray(18)
        buf[0] = 0x01
        buf[1] = modulus
        buf[2:18] = bits
        self.i2c.writeto(self.addr, buf)
        
    def reset(self):
        """Resets the ring shift register pointer to phase 0 and releases veto."""
        self.i2c.writeto(self.addr, b'\x02')
        
    def arm(self):
        """Arms the sieve node to evaluate candidates on REQ edges."""
        self.i2c.writeto(self.addr, b'\x03')

import time
from machine import Pin
import rp2
from sieve import Sieve

@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def sieve_scanner():
    """Continuous 50 kHz sieve engine with native 64-bit hardware counter:
    1. X holds ~low32, Y holds ~high32.
    2. Steps candidate via cascaded ~X / ~Y decrement.
    3. Pushes 64-bit index (low word then high word) only on survivor.
    """
    # Pull starting 64-bit candidate from host (low word, then high word)
    pull(block)
    mov(x, invert(osr))
    pull(block)
    mov(y, invert(osr))
    
    wrap_target()
    label("step_loop")
    # HIGH Phase: 10.0 us (50 cycles at 5 MHz)
    set(pins, 1) [31]           # 32 cycles
    nop() [17]                  # 18 cycles
    
    # LOW Phase: 10.0 us (50 cycles at 5 MHz)
    set(pins, 0) [31]           # 32 cycles
    nop() [11]                  # 12 cycles (sample at cycle 45 of low phase)
    
    # Branch on VOTE pin (jmp_pin)
    jmp(pin, "survivor")        # 1 cycle
    
    # Veto path: 4 cycles delay padding to match survivor path
    nop() [2]                   # 3 cycles
    jmp("decrement")            # 1 cycle
    
    # Survivor path: 5 cycles (pushes full 64-bit candidate to RX FIFO)
    label("survivor")
    mov(isr, invert(x))         # 1 cycle: load low 32 bits
    push(block)                 # 1 cycle: push low 32 bits
    mov(isr, invert(y))         # 1 cycle: load high 32 bits
    push(block)                 # 1 cycle: push high 32 bits
    
    # Cascaded 64-bit decrement
    label("decrement")
    jmp(x_dec, "step_loop")     # 1 cycle: decrement low 32 bits. Jumps if > 0
    jmp(y_dec, "step_loop")     # On low wrap: decrement high 32 bits (increment epoch)
    wrap()

class SieveRunner:
    """Orchestrator for Lehmer sieve array and RP2040 50 kHz PIO engine."""
    
    def __init__(self, req_pin: Pin, vote_pin: Pin, sieves: list = None, sm_id: int = 0, freq: int = 5000000, start_candidate: int = 0):
        self.req_pin = req_pin
        self.vote_pin = vote_pin
        self.sieves = list(sieves) if sieves else []
        self.sm_id = sm_id
        self.freq = freq
        
        self.sm = rp2.StateMachine(
            sm_id,
            sieve_scanner,
            freq=freq,
            set_base=req_pin,
            in_base=vote_pin,
            jmp_pin=vote_pin,
        )
        self.set_counter(start_candidate)

    def add_sieve(self, sieve: Sieve):
        """Adds an individual ATtiny Sieve node to the array."""
        self.sieves.append(sieve)

    def pause(self):
        """Pauses the hardware sieve stepping and clamps GP14 LOW via PIO."""
        self.sm.active(0)
        self.sm.exec("set(pins, 0)")

    def resume(self):
        """Resumes the hardware sieve stepping."""
        self.sm.active(1)

    def flush_fifo(self):
        """Flushes and discards all pending words in the RX FIFO."""
        while self.sm.rx_fifo() > 0:
            self.sm.get()

    def quiet_for(self, num_candidates: int) -> bool:
        """Returns True if no survivor is reported while the sieve steps
        num_candidates times. Only valid when no survivors are expected: the RX
        FIFO holds two survivors, after which the PIO stalls and stops stepping.
        """
        period_us = 100 * 1_000_000 // self.freq
        t0 = time.ticks_us()
        budget_us = num_candidates * period_us + 1000
        while time.ticks_diff(time.ticks_us(), t0) < budget_us:
            if self.sm.rx_fifo() > 0:
                return False
        return True

    def set_counter(self, candidate: int = 0):
        """Initializes StateMachine entry point, seeds 64-bit counter, and activates."""
        self.pause()
        self.flush_fifo()
        self.sm.init(
            sieve_scanner,
            freq=self.freq,
            set_base=self.req_pin,
            in_base=self.vote_pin,
            jmp_pin=self.vote_pin,
        )
        self.sm.active(1)
        # Push low 32 bits, then high 32 bits
        self.sm.put(candidate & 0xFFFFFFFF)
        self.sm.put((candidate >> 32) & 0xFFFFFFFF)

    def reset_counter(self):
        """Resets the PIO 64-bit candidate counter back to candidate 0."""
        self.set_counter(0)

    def configure_array(self, configs: list, start_candidate: int = 0):
        """Safely programs and arms all sieves in the array, then starts stepping.
        
        Args:
            configs: List of (modulus, ring_bits_16bytes) tuples, one per sieve.
            start_candidate: Starting 64-bit candidate index.
        """
        if len(configs) != len(self.sieves):
            raise ValueError(f"Config count ({len(configs)}) must match sieve count ({len(self.sieves)})")
            
        # 1. Halt PIO stepping so ATtinys receive zero clocks during I2C programming
        self.pause()
        
        # 2. Program ring parameters into each ATtiny
        for sieve, (modulus, ring_bits) in zip(self.sieves, configs):
            sieve.reset()
            time.sleep_ms(2)
            sieve.set_ring(modulus, ring_bits)
            time.sleep_ms(2)
            
        # 3. Arm each ATtiny
        for sieve in self.sieves:
            sieve.arm()
            time.sleep_ms(2)
            
        # 4. Flush FIFO, seed starting candidate counter, and activate PIO
        self.set_counter(start_candidate)

    def next_survivor(self) -> int:
        """Runs continuously until the next survivor is found and returns its 64-bit candidate index."""
        low = self.sm.get()
        high = self.sm.get()
        return (high << 32) | low

    def stream_survivors(self):
        """Generator that continuously yields 64-bit survivor candidate indices."""
        while True:
            yield self.next_survivor()

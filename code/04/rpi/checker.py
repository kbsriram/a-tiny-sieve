"""Electrical self-test routines for an ATtiny412 card on the test jig.

Executes the four test stages specified in flashing_self_test.md:
1. Shorts to GND
2. Pin-to-pin bridges and shorts to VCC
3. Open circuits
4. JP1 closure and PA7 isolation (3-second square wave observation)
"""

import time
from machine import Pin
import pins


class JigChecker:
    """Automated electrical tester for ATtiny412 modulus cards."""

    def __init__(self):
        # Monitored test pins: label -> GPIO number
        self.pin_defs = [
            ("PA6 (H1-2)", pins.PIN_H1_2_PA6),
            ("PA7 (H1-3)", pins.PIN_H1_3_PA7),
            ("PA1 (H1-4)", pins.PIN_H1_4_PA1),
            ("PA2 (H1-5)", pins.PIN_H1_5_PA2),
            ("PA3 (H1-7)", pins.PIN_H1_7_PA3),
        ]
        # Pins driven low sequentially during bridge tests
        self.drive_pins = [
            ("PA6 (H1-2)", pins.PIN_H1_2_PA6),
            ("PA1 (H1-4)", pins.PIN_H1_4_PA1),
            ("PA2 (H1-5)", pins.PIN_H1_5_PA2),
            ("PA3 (H1-7)", pins.PIN_H1_7_PA3),
        ]
        self.pins = {}

    def _setup_idle_state(self):
        """Sets PA6, PA1, PA2, PA3 to floating inputs (relying on ATtiny pull-ups).

        Sets PA7 (H1-3) to input with Pico pull-up (since JP1 is normally open).
        """
        for name, gpio in self.pin_defs:
            if gpio == pins.PIN_H1_3_PA7:
                self.pins[name] = Pin(gpio, Pin.IN, Pin.PULL_UP)
            else:
                self.pins[name] = Pin(gpio, Pin.IN)
        time.sleep_ms(2)

    def check_shorts_to_gnd(self):
        """Check 1: Read all five pins. Expect all HIGH.

        Catches shorts to GND or missing board power.
        Returns: (passed: bool, message: str)
        """
        self._setup_idle_state()
        failed = []
        for name, _ in self.pin_defs:
            if self.pins[name].value() != 1:
                failed.append(name)

        if failed:
            return False, f"Short to GND or unpowered on: {', '.join(failed)}"
        return True, "All five pins read HIGH"

    def check_bridges_and_vcc(self):
        """Check 2: Drive each line low one at a time, verify others stay high.

        Verifies the driven pin reads LOW (detects VCC shorts) and other pins
        remain HIGH (detects solder bridges).
        Returns: (passed: bool, message: str)
        """
        self._setup_idle_state()

        for d_name, d_gpio in self.drive_pins:
            # Drive target pin low
            p_drive = Pin(d_gpio, Pin.OUT)
            p_drive.value(0)
            time.sleep_ms(1)

            # 1. Check if driven pin was held high by VCC
            if p_drive.value() != 0:
                self._setup_idle_state()
                return False, f"{d_name} failed to pull LOW (shorted to VCC)"

            # 2. Check if any other pin was pulled low by a solder bridge
            bridges = []
            for other_name, other_gpio in self.pin_defs:
                if other_gpio == d_gpio:
                    continue
                if self.pins[other_name].value() != 1:
                    bridges.append(other_name)

            # Release driven pin back to input
            self._setup_idle_state()

            if bridges:
                return (
                    False,
                    f"Bridge detected: driving {d_name} pulled down {', '.join(bridges)}",
                )

        return True, "No pin bridges or VCC shorts detected"

    def check_opens(self):
        """Check 3: Release all lines and verify all read HIGH.

        Catches open circuits, socket contact issues, or missing ATtiny pull-ups.
        Returns: (passed: bool, message: str)
        """
        self._setup_idle_state()
        time.sleep_ms(2)

        failed = []
        for name, _ in self.pin_defs:
            if self.pins[name].value() != 1:
                failed.append(name)

        if failed:
            return False, f"Open circuit / missing pull-up on: {', '.join(failed)}"
        return True, "All five pins read HIGH after release"

    def check_jp1_and_pa7_isolation(self, duration_s=3.0, sample_interval_ms=50):
        """Check 4: Hold pin 3 down and monitor all pins over 3 seconds.

        With Pin 3 (H1-3) weakly pulled down, verify none of the pins follow
        the ATtiny's internal PA7 1.0s square wave.
        - If Pin 3 toggles: JP1 is closed.
        - If any other pin toggles: bridge to PA7.
        Returns: (passed: bool, message: str)
        """
        # Configure Pin 3 with weak pull-down; other pins as floating inputs
        for name, gpio in self.pin_defs:
            if gpio == pins.PIN_H1_3_PA7:
                self.pins[name] = Pin(gpio, Pin.IN, Pin.PULL_DOWN)
            else:
                self.pins[name] = Pin(gpio, Pin.IN)
        time.sleep_ms(5)

        total_samples = int((duration_s * 1000) // sample_interval_ms)
        last_val = {name: self.pins[name].value() for name, _ in self.pin_defs}
        toggles = {name: 0 for name, _ in self.pin_defs}
        high_counts = {name: 0 for name, _ in self.pin_defs}

        for _ in range(total_samples):
            time.sleep_ms(sample_interval_ms)
            for name, _ in self.pin_defs:
                val = self.pins[name].value()
                if val == 1:
                    high_counts[name] += 1
                if val != last_val[name]:
                    toggles[name] += 1
                    last_val[name] = val

        # Restore idle state
        self._setup_idle_state()

        # Check for closed JP1 (PA7 square wave overrode the weak pull-down)
        pa7_name = "PA7 (H1-3)"
        if toggles[pa7_name] > 0:
            return (
                False,
                f"JP1 is CLOSED: Pin 3 toggled {toggles[pa7_name]} times with PA7",
            )
        if high_counts[pa7_name] == total_samples:
            return (
                False,
                "Pin 3 (H1-3) stuck HIGH (shorted to VCC or bridged to active high line)",
            )

        # Check for bridges from PA7 to other lines
        bridged_to_pa7 = []
        for name, _ in self.drive_pins:
            if toggles[name] > 0:
                bridged_to_pa7.append(f"{name} ({toggles[name]} toggles)")

        if bridged_to_pa7:
            return (
                False,
                f"Bridge to PA7 detected on: {', '.join(bridged_to_pa7)}",
            )

        return True, "JP1 is open and PA7 is isolated from all pins"

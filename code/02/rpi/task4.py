import time
from machine import Pin, I2C
import pins

def main():
    print("Blinking LED...")
    try:
        led = Pin("LED", Pin.OUT)
    except Exception:
        led = Pin(25, Pin.OUT)

    
    # Blink 3 times
    for _ in range(3):
        led.on()
        time.sleep(0.2)
        led.off()
        time.sleep(0.2)
        
    print("Scanning I2C bus...")
    i2c = I2C(0, scl=Pin(pins.PIN_SCL), sda=Pin(pins.PIN_SDA), freq=400_000)
    devices = i2c.scan()
    
    if devices:
        print("I2C devices found:", [hex(device) for device in devices])
    else:
        print("No I2C devices found")

if __name__ == "__main__":
    main()

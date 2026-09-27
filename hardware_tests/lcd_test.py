# Writes "Hello world!" to the LCD. Same pins as code.py.
# Blank screen: turn the contrast pot before suspecting the wiring.
# Run: python3 hardware_tests/lcd_test.py
import time
from RPLCD import CharLCD
from RPi import GPIO

lcd = CharLCD(numbering_mode=GPIO.BOARD,
              cols=16,
              rows=2,
              pin_rs=19,
              pin_e=18,
              pins_data=[16,11,12,15])

time.sleep(1)
lcd.write_string("Hello world!")

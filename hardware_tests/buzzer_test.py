# Plays the reject tone once. Buzzer is on BCM 20 = physical pin 38.
# (It was on BCM 21 until the LED strip took that pin -- don't put it back.)
# Run: python3 hardware_tests/buzzer_test.py
from gpiozero import TonalBuzzer
from time import sleep

bz = TonalBuzzer(20)

bz.play(320)
sleep(0.5)
bz.stop()

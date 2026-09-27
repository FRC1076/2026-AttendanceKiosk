# Wipes the strip purple one LED at a time, holds 5 s, then turns it off.
# Same settings as code.py. Needs root for /dev/mem and DMA.
# Run: sudo python3 hardware_tests/led_strip_test.py
from rpi_ws281x import PixelStrip, Color
from time import sleep

LED_COUNT = 50
LED_PIN   = 21     # BCM 21 = physical pin 40 (PCM)
LED_DMA   = 10     # not 5 -- on a Pi 3 channel 5 belongs to the SD card

strip = PixelStrip(LED_COUNT, LED_PIN, dma=LED_DMA)
strip.begin()
for i in range(LED_COUNT):
	strip.setPixelColor(i, Color(75, 0, 120))
	strip.show()
	sleep(0.1)

sleep(5)
for i in range(LED_COUNT):
	strip.setPixelColor(i, Color(0, 0, 0))
strip.show()

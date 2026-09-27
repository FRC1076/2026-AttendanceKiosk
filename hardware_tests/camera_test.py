# Grabs one frame from the Pi Camera and prints its shape, e.g. (480, 640, 4).
# An exception here means the ribbon cable or camera, not the kiosk code.
# Run: python3 hardware_tests/camera_test.py
from picamera2 import Picamera2

picam2 = Picamera2()
picam2.start()

frame = picam2.capture_array()
print(frame.shape)
picam2.stop()

# Live camera preview for aiming and focusing. Needs a monitor attached.
# Press q in the preview window to quit.
# Run: python3 hardware_tests/camera_preview.py
from picamera2 import Picamera2
import cv2

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration())
picam2.start()

while True:
    frame = picam2.capture_array()

    if frame is None:
        print("No frame")
        continue

    cv2.imshow("Camera", frame)

    if cv2.waitKey(1) == ord('q'):
        break

cv2.destroyAllWindows()
picam2.stop()

import cv2
from pyzbar import pyzbar
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from picamera2 import Picamera2
import time
from time import sleep
from RPLCD import CharLCD
from RPi import GPIO
import keyboard
from gpiozero import TonalBuzzer
from rpi_ws281x import PixelStrip, Color

# WS2812B RGB strip. Data is on BCM 21 = physical pin 40, driven by the PCM
# block; the buzzer moved to BCM 20 to make room. rpi_ws281x always uses BCM
# numbering, whatever mode RPLCD sets. See docs/led-strip-wiring.md.
LED_COUNT      = 50
LED_PIN        = 21
LED_FREQ_HZ    = 800000
LED_DMA        = 10      # not 5 -- on a Pi 3 channel 5 belongs to the SD card
LED_INVERT     = False
LED_BRIGHTNESS = 255     # the look tuned on the kiosk; lower it to cut current
LED_CHANNEL    = 0

IDLE         = Color(75, 0, 120)   # purple
ACCEPTED     = Color(0, 255, 0)
UNAUTHORIZED = Color(255, 0, 0)
OFF          = Color(0, 0, 0)

strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                   LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()
print("LED ready")

def fill(color):
	for i in range(LED_COUNT):
		strip.setPixelColor(i, color)
	strip.show()

bz = TonalBuzzer(20)
print("Buzzer ready")
lcd = CharLCD(numbering_mode=GPIO.BOARD,
              cols=16,
              rows=2,
              pin_rs=19,
              pin_e=18,
              pins_data=[16,11,12,15])
print("LCD ready")

scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("/home/pihirobotics/QR_reader/fifth-chalice-487115-u5-1f3b8eea7e11.json", scopes=scopes)
client = gspread.authorize(creds)
sheet = client.open("PiHi samurai NEW attendance sheet QR test 61").worksheet("login logs")

master_sheet = client.open("PiHi samurai NEW attendance sheet QR test 61").worksheet("master list of names")
print("Connected to sheet")

# Badges encode an opaque ID (1076-A7F3), not a name. Column layout of the
# roster sheet must match generate_badges.py: A name, B subteam, C badge ID.
COL_NAME = 0
COL_SUBTEAM = 1
COL_ID = 2

# Set True only while transitioning from the old "Name,Subteam" badges, so
# unreprinted badges keep working. Turn it off once everyone has a new badge.
ALLOW_LEGACY_NAME_BADGES = False

# Test badges, printed in test_badges/ by generate_badges.py --test. Built in so
# anyone can check the kiosk without editing the roster. Each maps to
# (LCD name, subteam, append a row to the sheet?). TEST-REJECT is absent on
# purpose: it takes the reject path like any unknown ID.
TEST_BADGES = {
	"TEST-OK":  ("Test: not logged", "Test", False),
	"TEST-LOG": ("TEST BADGE", "Test", True),
}

def load_roster(worksheet):
	"""Map badge ID -> (name, subteam)."""
	rows = worksheet.get_all_values()
	if rows and rows[0] and rows[0][0].strip().lower() in ("name", "names"):
		rows = rows[1:]
	roster = {}
	for row in rows:
		row = list(row) + [""] * (3 - len(row))
		name = row[COL_NAME].strip()
		subteam = row[COL_SUBTEAM].strip()
		badge_id = row[COL_ID].strip().upper()
		if name and badge_id:
			roster[badge_id] = (name, subteam)
	return roster

roster = load_roster(master_sheet)
legacy_names = {name for name, _ in roster.values()}
print("Loaded " + str(len(roster)) + " badge IDs")

def show_accepted(name, time_str):
	lcd.clear()
	lcd.cursor_pos = (0, 0)
	lcd.write_string(name[:16])
	lcd.cursor_pos = (1, 0)
	lcd.write_string("at " + time_str)
	fill(ACCEPTED)
	bz.play(440)
	sleep(0.2)
	bz.play(600)
	sleep(0.3)
	bz.stop()

def show_unauthorized():
	lcd.clear()
	lcd.cursor_pos = (0, 0)
	lcd.write_string("Unauthorized")
	fill(UNAUTHORIZED)
	bz.play(320)
	sleep(0.5)
	bz.stop()

# Purple wipe down the strip: the sheet is reachable and the roster is loaded.
for i in range(LED_COUNT):
	strip.setPixelColor(i, IDLE)
	strip.show()
	sleep(0.05)

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration())
picam2.start()
lcd.write_string("Scanner ready")

while True:
	frame = picam2.capture_array()
	if frame is None:
		print("No frame")
		continue

	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	qrs = pyzbar.decode(gray)

	for qr in qrs:
		data = qr.data.decode('utf-8').strip()
		print(data)
		badge_id = data.upper()
		entry = roster.get(badge_id)
		log_scan = True

		if badge_id in TEST_BADGES:
			name, title, log_scan = TEST_BADGES[badge_id]
			entry = (name, title)

		if entry is None and ALLOW_LEGACY_NAME_BADGES and "," in data:
			old_name, _, old_subteam = data.partition(",")
			if old_name.strip() in legacy_names:
				entry = (old_name.strip(), old_subteam.strip())

		if entry is not None:
			name, title = entry
			now = datetime.now()
			date_str = now.strftime("%Y-%m-%d")
			time_str = now.strftime("%H:%M:%S")

			if log_scan:
				sheet.append_row([name, title, date_str, time_str])
			show_accepted(name, time_str)
		else:
			show_unauthorized()
		# The result colour holds through the pause; purple means "scan now".
		time.sleep(15)
		fill(IDLE)

	if keyboard.is_pressed('q'):
		lcd.clear()
		break
picam2.stop()
fill(OFF)
bz.close()
GPIO.cleanup()

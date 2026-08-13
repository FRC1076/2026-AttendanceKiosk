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
bz = TonalBuzzer(21)
lcd = CharLCD(numbering_mode=GPIO.BOARD,
              cols=16,
              rows=2,
              pin_rs=19,
              pin_e=18,
              pins_data=[16,11,12,15])

scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("/home/pihirobotics/QR_reader/fifth-chalice-487115-u5-1f3b8eea7e11.json", scopes=scopes)
client = gspread.authorize(creds)
sheet = client.open("PiHi samurai NEW attendance sheet QR test 61").worksheet("login logs")

master_sheet = client.open("PiHi samurai NEW attendance sheet QR test 61").worksheet("master list of names")

# Badges encode an opaque ID (1076-A7F3), not a name. Column layout of the
# roster sheet must match generate_badges.py: A name, B subteam, C badge ID.
COL_NAME = 0
COL_SUBTEAM = 1
COL_ID = 2

# Set True only while transitioning from the old "Name,Subteam" badges, so
# unreprinted badges keep working. Turn it off once everyone has a new badge.
ALLOW_LEGACY_NAME_BADGES = False

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
		entry = roster.get(data.upper())

		if entry is None and ALLOW_LEGACY_NAME_BADGES and "," in data:
			old_name, _, old_subteam = data.partition(",")
			if old_name.strip() in legacy_names:
				entry = (old_name.strip(), old_subteam.strip())

		if entry is not None:
			name, title = entry
			now = datetime.now()
			date_str = now.strftime("%Y-%m-%d")
			time_str = now.strftime("%H:%M:%S")

			sheet.append_row([name, title, date_str, time_str])
			lcd.clear()
			lcd.cursor_pos = (0, 0)
			lcd.write_string(name[:16])
			lcd.cursor_pos = (1, 0)
			lcd.write_string("at " + time_str)
			bz.play(440)
			sleep(0.2)
			bz.play(600)
			sleep(0.3)
			bz.stop()
		else:
			lcd.clear()
			lcd.cursor_pos = (0, 0)
			lcd.write_string("Unauthorized")
			bz.play(320)
			sleep(0.5)
			bz.stop()
		time.sleep(15)
		
	if keyboard.is_pressed('q'):
		lcd.clear()
		break
picam2.stop()

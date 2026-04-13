import cv2
from pyzbar import pyzbar
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from picamera2 import Picamera2
import time
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
authorized_names = master_sheet.col_values(1)

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration())
picam2.start()
lcd.write_string("Scanner ready")

while True:
	frame = picam2.capture_array()
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	qrs = pyzbar.decode(gray)
	if frame is None:
		print("No frame")
		continue
	
	for qr in qrs:
		data = qr.data.decode('utf-8')
		print(data)
		if "," in data:
			parts = data.split(",")
			name = parts[0]
			title = parts[1]
			if name in authorized_names:
				now = datetime.now()
				date_str = now.strftime("%Y-%m-%d")
				time_str = now.strftime("%H:%M:%S")

				sheet.append_row([name, title, date_str, time_str])
				lcd.clear()
				lcd.cursor_pos = (0, 0)
				lcd.write_string("" + name)
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

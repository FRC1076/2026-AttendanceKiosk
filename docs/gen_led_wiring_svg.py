#!/usr/bin/env python3
"""Generate led-strip-wiring.svg, next to this script.

The diagram is drawn from hard-coded coordinates and pin assignments. Edit
this file and rerun it rather than editing the SVG by hand:

    python3 docs/gen_led_wiring_svg.py
"""

import os

W, H = 1780, 1300

BG      = "#ffffff"
INK     = "#0f172a"
MUTED   = "#64748b"
FAINT   = "#94a3b8"
LINE    = "#cbd5e1"
PCB     = "#176b3a"
PCB_DK  = "#0e4a27"
SILK    = "#e2f5e9"
BLACK   = "#1e293b"
GOLD    = "#d9a520"
SILVER  = "#c3ccd8"
RED     = "#dc2626"
GND     = "#0f172a"
BLUE    = "#2563eb"
ORANGE  = "#ea580c"
GREY_W  = "#94a3b8"
NEW     = "#16a34a"
NEW_DK  = "#15803d"
WARN    = "#b45309"
LCDBLUE = "#1e3a8a"
LCDTEXT = "#7dd3fc"

F = "ui-sans-serif,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
M = "ui-monospace,'SF Mono',Menlo,Consolas,monospace"

out = []
def a(s): out.append(s)

def txt(x, y, s, size=12, fill=INK, anchor="start", weight="400", font=F):
    a(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{fill}" '
      f'text-anchor="{anchor}" font-weight="{weight}">{s}</text>')

def rect(x, y, w, h, fill="none", stroke="none", rx=0, sw=1):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
      f'stroke="{stroke}" stroke-width="{sw}"/>')

def poly(pts, stroke, sw=2.6, fill="none"):
    d = " ".join(f"{x},{y}" for x, y in pts)
    a(f'<polyline points="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
      f'stroke-linecap="round" stroke-linejoin="round"/>')

def dot(x, y, fill, r=4.5):
    a(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>')

def brk(x, y, w=16, h=16):
    """White break where one wire passes over another."""
    a(f'<rect x="{x-w/2}" y="{y-h/2}" width="{w}" height="{h}" fill="{BG}"/>')

a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
rect(0, 0, W, H, fill=BG)

txt(56, 58, "Attendance Kiosk — WS2812B LED strip wiring", 30, INK, weight="700")
txt(56, 88, "Raspberry Pi 3B  ·  LED strip path in colour, rest of the kiosk in grey  ·  "
            "50 LEDs, as running on the kiosk", 15, MUTED)
txt(56, 110, "Data on GPIO21 / physical pin 40 (PCM).  Buzzer moved to GPIO20 / pin 38 to make room.  "
             "Strip power is external — never from the header.",
    14, NEW_DK, weight="600")

# ------------------------------------------------------------- Pi board
BX, BY, BW, BH = 56, 140, 324, 230
rect(BX, BY, BW, BH, fill=PCB, rx=10)
rect(BX+6, BY+6, BW-12, BH-12, stroke=PCB_DK, rx=7)
txt(BX+18, BY+30, "Raspberry Pi 3B", 15, SILK, weight="700")
txt(BX+18, BY+48, "top view", 11, "#8fd3ab")
rect(BX+96, BY+66, 200, 26, fill=BLACK, rx=3)
for i in range(20):
    px = BX + 102 + i * 9.7
    a(f'<rect x="{px:.1f}" y="{BY+70}" width="5" height="5" fill="{GOLD}"/>')
    a(f'<rect x="{px:.1f}" y="{BY+81}" width="5" height="5" fill="{GOLD}"/>')
txt(BX+96, BY+108, "40-pin GPIO header", 10, SILK)
txt(BX+96, BY+122, "↓ detail below", 10, "#8fd3ab", weight="600")
rect(BX+232, BY+140, 84, 62, fill=SILVER, rx=3)
txt(BX+274, BY+176, "ETH", 10, MUTED, anchor="middle", weight="600")
rect(BX+236, BY+112, 76, 22, fill=SILVER, rx=2)
txt(BX+274, BY+127, "USB", 9, MUTED, anchor="middle", weight="600")
rect(BX+306, BY+34, 14, 62, fill="#f8fafc", rx=2)
txt(BX+298, BY+110, "CSI", 9, SILK, anchor="middle")
rect(BX+10, BY+186, 46, 16, fill=SILVER, rx=2)
txt(BX+14, BY+199, "microSD", 8, MUTED)

# --------------------------------------------------------------- camera
CX, CY, CW, CH = 420, 148, 178, 132
rect(CX, CY, CW, CH, fill="#14532d", rx=8)
a(f'<circle cx="{CX+CW/2}" cy="{CY+62}" r="30" fill="#0b1220"/>')
a(f'<circle cx="{CX+CW/2}" cy="{CY+62}" r="20" fill="#1e293b"/>')
a(f'<circle cx="{CX+CW/2}" cy="{CY+62}" r="9" fill="#334155"/>')
txt(CX+CW/2, CY+118, "Pi Camera Module", 11, SILK, anchor="middle", weight="600")
txt(CX+CW/2, CY+20, "no header pins used", 10, "#8fd3ab", anchor="middle")
poly([(CX, CY+70), (BX+320, CY+70)], GREY_W, sw=9)

# ------------------------------------------------------------------ LCD
LX, LY, LW, LH = 680, 130, 470, 238
rect(LX, LY, LW, LH, fill="#0f766e", rx=8)
rect(LX+26, LY+44, LW-52, 108, fill=LCDBLUE, rx=4)
txt(LX+46, LY+86, "Van Loo, Mr.", 20, LCDTEXT, font=M)
txt(LX+46, LY+124, "at 14:32:07", 20, LCDTEXT, font=M)
txt(LX+26, LY+30, "16×2 character LCD (HD44780, 4-bit)", 13, "#ccfbf1", weight="700")
txt(LX+26, LY+186, "RS · E · D4 · D5 · D6 · D7 + 5 V + GND — unchanged", 12, "#99f6e4")
txt(LX+26, LY+208, "R/W tied to GND (write-only, so no 5 V reaches the Pi)", 11, "#5eead4")

PX, PY = 1200, 178
rect(PX, PY, 122, 128, fill="#1e293b", rx=8)
a(f'<circle cx="{PX+61}" cy="{PY+50}" r="32" fill="#3b82f6"/>')
a(f'<circle cx="{PX+61}" cy="{PY+50}" r="24" fill="#1d4ed8"/>')
poly([(PX+61, PY+50), (PX+61, PY+28)], "#e2e8f0", sw=4)
txt(PX+61, PY+96, "10 kΩ trimmer", 11, "#cbd5e1", anchor="middle", weight="600")
txt(PX+61, PY+114, "wiper → LCD V0", 10, "#94a3b8", anchor="middle")
poly([(LX+LW, LY+120), (PX, PY+50)], GREY_W, sw=2.2)

# --------------------------------------------------------------- legend
GX, GY, GW, GH = 1400, 130, 340, 366
rect(GX, GY, GW, GH, fill="#f8fafc", stroke=LINE, rx=10)
txt(GX+20, GY+32, "Legend", 16, INK, weight="700")
for i, (c, lbl) in enumerate([
        (RED,    "+5 V  (external supply only)"),
        (GND,    "Ground / common return"),
        (BLUE,   "Data — 3.3 V logic (Pi → shifter)"),
        (ORANGE, "Data — 5 V logic (shifter → strip)"),
        (GREY_W, "Rest of the kiosk — LCD, buzzer, camera")]):
    y = GY + 62 + i * 30
    poly([(GX+20, y), (GX+64, y)], c, sw=4)
    txt(GX+76, y+5, lbl, 12, INK)
y0 = GY + 226
txt(GX+20, y0, "Header pin key", 13, INK, weight="700")
for i, (f_, s_, lbl) in enumerate([
        (NEW,       NEW_DK,    "LED strip"),
        ("#cbd5e1", "#64748b", "LCD / buzzer"),
        ("#fef3c7", "#d97706", "keep free (PWM0 fallback)"),
        ("#ffffff", "#94a3b8", "unused"),
        ("#fecaca", "#dc2626", "reserved — HAT EEPROM")]):
    y = y0 + 26 + i * 24
    a(f'<circle cx="{GX+32}" cy="{y-4}" r="9" fill="{f_}" stroke="{s_}" stroke-width="1.6"/>')
    txt(GX+50, y, lbl, 12, INK)

# -------------------------------------------------------- header detail
HX, HY, HW, HH = 56, 420, 544, 784
rect(HX, HY, HW, HH, fill="#f8fafc", stroke=LINE, rx=10)
txt(HX+20, HY+34, "40-pin GPIO header — pin detail", 16, INK, weight="700")
txt(HX+20, HY+54, "pin 1 top-left, viewed from above", 11, MUTED)

COL_O, COL_E = 288, 342
ROW0, STEP, R = 505, 34, 10
rect(COL_O-24, ROW0-20, (COL_E-COL_O)+48, 19*STEP+40, fill=BLACK, rx=6)

PINS = [
    ("3V3", "free", "5V", "lcd"), ("GPIO2", "free", "5V", "free"),
    ("GPIO3", "free", "GND", "free"), ("GPIO4", "free", "GPIO14", "free"),
    ("GND", "free", "GPIO15", "free"), ("GPIO17", "lcd", "GPIO18", "lcd"),
    ("GPIO27", "free", "GND", "lcd"), ("GPIO22", "lcd", "GPIO23", "lcd"),
    ("3V3", "free", "GPIO24", "lcd"), ("GPIO10", "lcd", "GND", "free"),
    ("GPIO9", "free", "GPIO25", "free"), ("GPIO11", "free", "GPIO8", "free"),
    ("GND", "free", "GPIO7", "free"), ("ID_SD", "rsvd", "ID_SC", "rsvd"),
    ("GPIO5", "free", "GND", "free"), ("GPIO6", "free", "GPIO12", "spare"),
    ("GPIO13", "free", "GND", "new"), ("GPIO19", "free", "GPIO16", "free"),
    ("GPIO26", "free", "GPIO20", "buzz"), ("GND", "buzz", "GPIO21", "new"),
]
STYLE = {
    "free":  ("#ffffff", "#94a3b8", INK,       FAINT,     "400"),
    "lcd":   ("#cbd5e1", "#64748b", INK,       "#334155", "600"),
    "buzz":  ("#cbd5e1", "#64748b", INK,       "#334155", "600"),
    "new":   (NEW,       NEW_DK,    "#ffffff", NEW_DK,    "700"),
    "spare": ("#fef3c7", "#d97706", INK,       WARN,      "600"),
    "rsvd":  ("#fecaca", "#dc2626", INK,       "#b91c1c", "600"),
}
cy_of = lambda i: ROW0 + i * STEP
for i, (ol, os_, el, es) in enumerate(PINS):
    cy = cy_of(i)
    of, ost, ot, olc, olw = STYLE[os_]
    ef, est, et, elc, elw = STYLE[es]
    a(f'<circle cx="{COL_O}" cy="{cy}" r="{R}" fill="{of}" stroke="{ost}" stroke-width="1.6"/>')
    a(f'<circle cx="{COL_E}" cy="{cy}" r="{R}" fill="{ef}" stroke="{est}" stroke-width="1.6"/>')
    txt(COL_O, cy+3.5, str(2*i+1), 9.5, ot, anchor="middle", weight="700", font=M)
    txt(COL_E, cy+3.5, str(2*i+2), 9.5, et, anchor="middle", weight="700", font=M)
    txt(COL_O-32, cy+4, ol, 11.5, olc, anchor="end", weight=olw, font=M)
    txt(COL_E+42, cy+4, el, 11.5, elc, anchor="start", weight=elw, font=M)
txt(HX+20, HY+HH-18, "PCM route: no config.txt change, no I2S audio", 11, MUTED)
txt(HX+20, HY+HH-4, "SPI must stay disabled — LCD RS sits on GPIO10", 11, MUTED)

odd_lane  = lambda i: cy_of(i) - 20
even_lane = lambda i: cy_of(i) + 20
EJOG = COL_E + 18

# ------------------------------------------------- existing: LCD harness
LOOM_X, LOOM_W = 520, 38
rect(LOOM_X, 496, LOOM_W, 312, fill="#e2e8f0", stroke=GREY_W, rx=10)
for i in (5, 7, 9):                       # pins 11, 15, 19
    poly([(COL_O, cy_of(i)), (COL_O, odd_lane(i)), (LOOM_X, odd_lane(i))], GREY_W, sw=2)
for i in (0, 5, 6, 7, 8):                 # pins 2, 12, 14, 16, 18
    poly([(COL_E, cy_of(i)), (EJOG, cy_of(i)), (EJOG, even_lane(i)), (LOOM_X, even_lane(i))], GREY_W, sw=2)
poly([(LOOM_X+LOOM_W, 652), (622, 652), (622, 250), (LX, 250)], GREY_W, sw=10)
txt(636, 470, "LCD harness", 11, MUTED, weight="600")
txt(636, 486, "8 wires, unchanged", 10, FAINT)

# --------------------------------------------------------------- buzzer
BZX, BZY, BZW, BZH = 648, 1088, 164, 132
rect(BZX, BZY, BZW, BZH, fill="#0f172a", rx=8)
a(f'<circle cx="{BZX+BZW/2}" cy="{BZY+56}" r="33" fill="#1e293b" stroke="#334155" stroke-width="2"/>')
a(f'<circle cx="{BZX+BZW/2}" cy="{BZY+56}" r="7" fill="#020617"/>')
txt(BZX+BZW/2, BZY+112, "passive piezo", 11, "#cbd5e1", anchor="middle", weight="600")
# pin 38 jogs up into the free lane above it, so it stays clear of pin 39's lane
BZ_PLUS_Y = cy_of(18) - 17
poly([(COL_E, cy_of(18)), (EJOG, cy_of(18)), (EJOG, BZ_PLUS_Y), (BZX, BZ_PLUS_Y)], GREY_W, sw=2.2)
poly([(COL_O, cy_of(19)), (COL_O, odd_lane(19)), (BZX, odd_lane(19))], GREY_W, sw=2.2)
txt(BZX+BZW/2, BZY+BZH+18, "pin 38 · GPIO20 (+)   ·   pin 39 · GND", 10, MUTED, anchor="middle")

# ---------------------------------------------------- 74AHCT125 shifter
SX0, SY0, SX1, SY1 = 700, 612, 1100, 790
PIN_X = [730, 785, 840, 895, 950, 1005, 1060]
rect(SX0, SY0, SX1-SX0, SY1-SY0, fill="#1e293b", rx=6)
a(f'<path d="M {(SX0+SX1)/2-16} {SY0} a 16 16 0 0 0 32 0" fill="{BG}"/>')
txt((SX0+SX1)/2, SY0+82, "74AHCT125", 20, "#f1f5f9", anchor="middle", weight="700", font=M)
txt((SX0+SX1)/2, SY0+104, "quad buffer — 3.3 V → 5 V level shifter", 11, "#94a3b8", anchor="middle")
txt((SX0+SX1)/2, SY0+124, "HCT family is essential: TTL input thresholds", 10, "#fbbf24", anchor="middle")
for x, l in zip(PIN_X, ["1·1OE", "2·1A", "3·1Y", "4·2OE", "5·2A", "6·2Y", "7·GND"]):
    a(f'<rect x="{x-5}" y="{SY1}" width="10" height="12" fill="{GOLD}"/>')
    txt(x, SY1-10, l, 9.5, "#cbd5e1", anchor="middle", font=M)
for x, l in zip(PIN_X, ["14·VCC", "13·4OE", "12·4A", "11·4Y", "10·3OE", "9·3A", "8·3Y"]):
    a(f'<rect x="{x-5}" y="{SY0-12}" width="10" height="12" fill="{GOLD}"/>')
    txt(x, SY0+20, l, 9.5, "#cbd5e1", anchor="middle", font=M)

# tie-off callout, parked in clear space above the chip
TX0, TY0, TX1, TY1 = 760, 486, 1190, 584
rect(TX0, TY0, TX1-TX0, TY1-TY0, fill="#fffbeb", stroke="#fcd34d", rx=8)
txt(TX0+16, TY0+24, "Tie off the three unused buffers — never leave CMOS inputs floating",
    11.5, "#92400e", weight="700")
txt(TX0+16, TY0+46, "pins 4 · 10 · 13   (OE)  →  +5 V", 11, "#78350f", font=M)
txt(TX0+16, TY0+64, "pins 5 · 9 · 12    (A)   →  GND", 11, "#78350f", font=M)
txt(TX0+16, TY0+84, "pin 1 (1OE) → GND, or buffer 1 stays tri-stated", 11, "#b45309", font=M)

# ------------------------------------------------------------- resistor
RX0, RY0, RX1, RY1 = 1140, 830, 1250, 880
rect(RX0, RY0, RX1-RX0, RY1-RY0, fill="#d6bfa0", stroke="#8b6f47", rx=8)
for i, c in enumerate(["#f59e0b", "#7c3aed", "#111827", "#a16207"]):
    a(f'<rect x="{RX0+18+i*20}" y="{RY0+3}" width="8" height="{RY1-RY0-6}" fill="{c}"/>')
txt((RX0+RX1)/2, RY1+22, "470 Ω", 13, INK, anchor="middle", weight="700")
txt((RX0+RX1)/2, RY1+38, "close to the source", 10, MUTED, anchor="middle")

# ------------------------------------------------------------ LED strip
STX0, STY0, STX1, STY1 = 1320, 590, 1750, 762
rect(STX0, STY0, STX1-STX0, STY1-STY0, fill="#f1f5f9", stroke="#94a3b8", rx=8)
rect(STX0+56, STY0+26, STX1-STX0-76, STY1-STY0-52, fill="#e2e8f0", rx=4)
for i in range(5):
    lx = STX0 + 88 + i * 66
    rect(lx, STY0+50, 42, 42, fill="#f8fafc", stroke="#cbd5e1", rx=5, sw=1.6)
    a(f'<circle cx="{lx+21}" cy="{STY0+71}" r="12" fill="#7c3aed"/>')
txt((STX0+STX1)/2+26, STY0+20, "WS2812B RGB strip · 50 LEDs", 13, INK, anchor="middle", weight="700")
txt((STX0+STX1)/2+26, STY0+118, "purple = ready  ·  green = logged  ·  red = unauthorized", 10.5, INK, anchor="middle")
txt((STX0+STX1)/2+26, STY1-12, "DOUT → DIN chains down the strip · 60 mA per LED at full white",
    11, MUTED, anchor="middle")
for lbl, py, c in [("DIN", 620, ORANGE), ("5V", 675, RED), ("GND", 730, GND)]:
    rect(STX0, py-11, 22, 22, fill=c, rx=3)
    txt(STX0+30, py+4, lbl, 11, INK, weight="700", font=M)

# ------------------------------------------------------------ capacitor
CPX, CPY, CPW, CPH = 1340, 830, 110, 120
rect(CPX, CPY, CPW, CPH, fill="#1e3a8a", rx=10)
rect(CPX+CPW-30, CPY+6, 24, CPH-12, fill="#93c5fd", rx=6)
txt(CPX+38, CPY+54, "1000", 15, "#dbeafe", anchor="middle", weight="700", font=M)
txt(CPX+38, CPY+74, "µF", 15, "#dbeafe", anchor="middle", weight="700", font=M)
txt(CPX+CPW-18, CPY+CPH/2+6, "–", 22, "#1e3a8a", anchor="middle", weight="700")
txt(CPX+CPW/2, CPY+CPH+20, "10 V electrolytic · stripe = –", 10, MUTED, anchor="middle")
rect(1365, CPY-12, 10, 12, fill=GOLD)
txt(1352, CPY-16, "+", 14, RED, anchor="middle", weight="700")
rect(1415, CPY+CPH, 10, 12, fill=GOLD)

# ------------------------------------------------------------------ PSU
PSX0, PSY0, PSX1, PSY1 = 1400, 1088, 1722, 1250
rect(PSX0, PSY0, PSX1-PSX0, PSY1-PSY0, fill="#0f172a", rx=10)
txt((PSX0+PSX1)/2, PSY0+52, "5 V DC supply", 19, "#f1f5f9", anchor="middle", weight="700")
txt((PSX0+PSX1)/2, PSY0+76, "separate from the Pi's own PSU", 12, "#94a3b8", anchor="middle")
txt((PSX0+PSX1)/2, PSY0+104, "size for 60 mA × LED count, +30 % headroom", 11, "#fbbf24", anchor="middle")
txt((PSX0+PSX1)/2, PSY0+126, "50 LEDs → 3 A worst case → buy 5 V 4 A", 11, "#cbd5e1", anchor="middle")
for x, lbl, c in ((1470, "+", RED), (1620, "–", "#e2e8f0")):
    rect(x-9, PSY0-14, 18, 14, fill=GOLD)
    txt(x, PSY0-20, lbl, 15, c, anchor="middle", weight="700")

# ---------------------------------------------------------------- notes
NX0, NY0, NX1, NY1 = 850, 1088, 1360, 1250
rect(NX0, NY0, NX1-NX0, NY1-NY0, fill="#fffbeb", stroke="#fcd34d", rx=10)
txt(NX0+20, NY0+28, "Rules for this build", 14, "#92400e", weight="700")
for i, n in enumerate([
        "1.  DMA must be 10.  dma=5 corrupts the SD card on a Pi 3",
        "2.  No I2S audio, no dtoverlay=pwm — the strip owns PCM",
        "3.  Don't switch gpiozero to PiGPIOFactory — pigpiod uses PCM",
        "4.  Shifter, resistor, cap: recommended — check the kiosk",
        "5.  Needs root — already covered by  sudo -E python3"]):
    txt(NX0+20, NY0+54 + i*22, n, 10.5, "#78350f", font=M)

# ----------------------------------------------------------- power rails
RAIL5, RAILG = 1000, 1045
poly([(655, RAIL5), (1740, RAIL5)], RED, sw=3.4)
txt(706, RAIL5-13, "+5 V rail", 12, RED, weight="700")
brk(1060, RAIL5); brk(1284, RAIL5); brk(1420, RAIL5)

poly([(830, RAILG), (1740, RAILG)], GND, sw=3.4)
txt(880, RAILG+22, "common ground", 12, GND, weight="700")

poly([(1060, SY1+12), (1060, RAILG)], GND, sw=2.8); dot(1060, RAILG, GND)
poly([(STX0, 730), (1284, 730), (1284, RAILG)], GND, sw=2.8); dot(1284, RAILG, GND)
poly([(1420, CPY+CPH+12), (1420, RAILG)], GND, sw=2.8); dot(1420, RAILG, GND)
poly([(1620, PSY0), (1620, RAILG)], GND, sw=2.8); dot(1620, RAILG, GND)
poly([(COL_E, cy_of(16)), (EJOG, cy_of(16)), (EJOG, even_lane(16)),
      (860, even_lane(16)), (860, RAILG)], GND, sw=2.8)
dot(860, RAILG, GND)
txt(644, even_lane(16)-8, "pin 34 · GND — common return", 11.5, GND, weight="700")

brk(1470, RAILG)

poly([(1470, PSY0), (1470, RAIL5)], RED, sw=2.8); dot(1470, RAIL5, RED)
poly([(730, SY0-12), (730, 565), (660, 565), (660, RAIL5)], RED, sw=2.8); dot(660, RAIL5, RED)
poly([(STX0, 675), (1306, 675), (1306, RAIL5)], RED, sw=2.8); dot(1306, RAIL5, RED)
poly([(1370, CPY), (1370, 800), (1306, 800)], RED, sw=2.8); dot(1306, 800, RED)

brk(660, 920)
brk(1060, 855)

# ------------------------------------------------------------- data path
# Pin 40 is the bottom-right pin, so the data line has to climb past the pin 34
# ground and both buzzer wires. It passes over them.
DATA_X = 630
for y in (even_lane(16), BZ_PLUS_Y, odd_lane(19)):
    brk(DATA_X, y, w=12, h=12)
poly([(COL_E, cy_of(19)), (EJOG, cy_of(19)), (EJOG, even_lane(19)),
      (DATA_X, even_lane(19)), (DATA_X, 920), (785, 920), (785, SY1+12)], BLUE, sw=3)
txt(384, even_lane(19)+17, "pin 40 · GPIO21 · PCM", 11.5, BLUE, weight="700")
txt(672, 912, "3.3 V data", 11, BLUE, weight="600")

poly([(840, SY1+12), (840, 855), (RX0, 855)], ORANGE, sw=3)
poly([(RX1, 855), (1262, 855), (1262, 620), (STX0, 620)], ORANGE, sw=3)
txt(856, 847, "5 V data", 11, ORANGE, weight="600")

a('</svg>')

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "led-strip-wiring.svg")
with open(path, "w") as fh:
    fh.write("\n".join(out) + "\n")
print("wrote", path)

# FRC1076 Attendance Kiosk

A Raspberry Pi QR-code kiosk that logs build-season attendance for FRC Team 1076
(PiHi Samurai). A team member holds their printed badge up to the camera; the Pi
decodes the QR code, resolves it against a roster, appends a timestamped row to
a Google Sheet, and confirms the scan on a small LCD, with a buzzer chirp and a
colour change on an LED strip.

This repository is meant to hold everything needed to set up, run, and maintain
the QR login system for all future seasons — the code the Pi runs, the badge
generator, and the instructions for starting the system at a build.

## How it works

1. **Scan** — a Pi Camera (`picamera2`) captures frames continuously; OpenCV
   converts each to grayscale and `pyzbar` decodes any QR codes in view.
2. **Parse** — each badge encodes an opaque ID such as `1076-A7F3`. No name or
   role is stored in the QR code itself.
3. **Resolve and authorize** — the ID is looked up in a map built at startup
   from the `master list of names` worksheet. An unknown ID is rejected.
4. **Log** — on a match, a row of `[name, title, YYYY-MM-DD, HH:MM:SS]` is
   appended to the `login logs` worksheet via `gspread`.
5. **Feedback** — a 16x2 character LCD shows the name and time (or
   `Unauthorized`), and a `gpiozero` `TonalBuzzer` plays a rising two-tone
   accept chime or a single low reject tone. A 50-LED strip, purple while
   idle, turns green or red. The loop then pauses ~15 seconds before accepting
   another scan, and the strip holds its colour until the pause ends — purple
   always means "scan now".

The team built and ran the LED strip on the Pi in spring 2026. Its code only
reached this repo on 2026-09-27, when it was brought over from the Pi's own copy
of `code.py`. See [LED status strip](#led-status-strip).

## Repository contents

| Path | What it is |
| --- | --- |
| [code.py](code.py) | The entire kiosk program — one file, one `while True` loop. Runs on the Pi. |
| [generate_badges.py](generate_badges.py) | Mints badge IDs into the roster sheet and renders printable PNGs into a local, gitignored `badges/`. Run on any machine with the service-account key. |
| [Use instructions](Use%20instructions) | Step-by-step operating procedure for starting and stopping the kiosk at a build session. |
| [hardware_tests/](hardware_tests) | One small script per part — LCD, buzzer, LED strip, camera, plus a live camera preview for aiming. Run one when a part misbehaves, to separate a wiring fault from a code fault. |
| [docs/led-strip-wiring.md](docs/led-strip-wiring.md) | Wiring for the WS2812B status strip: pin choice and why, what is and isn't known about the build, recommended parts, power budget, software traps, and a checklist. |
| [docs/led-strip-wiring.svg](docs/led-strip-wiring.svg) | The same wiring as a labelled diagram — every component and connection, strip path in colour and the rest of the kiosk in grey. |
| [docs/gen_led_wiring_svg.py](docs/gen_led_wiring_svg.py) | Generates the diagram. Edit it and rerun rather than editing the SVG by hand. |

## Hardware

### Core parts

| Part | Requirement | Why |
| --- | --- | --- |
| Raspberry Pi | **Pi 3B / 3B+ or newer.** This team runs a Pi 3. | |
| microSD card | 16 GB+ | OS, code, service-account key |
| Power supply | Official PSU for the board | |
| Camera | Pi Camera Module (v2, v3, or HQ) + standard 15-pin CSI ribbon | `Picamera2()` — a USB webcam will **not** work without rewriting the capture code |
| Network | Wi-Fi or Ethernet | `gspread` writes to Google Sheets live |
| Character LCD | 16x2 HD44780-compatible, parallel, wired in **4-bit mode** | |
| Contrast pot | ~10 kΩ trimmer on the LCD's V0 pin | |
| Buzzer | **Passive** piezo | `TonalBuzzer` drives it with PWM tones; an active buzzer only ever produces one pitch |
| LED strip | WS2812B **RGB**, 50 LEDs, with its own 5 V supply | See [LED status strip](#led-status-strip) |
| Breadboard + jumper wires | Male-to-female for the GPIO header | A PCB to replace this is on the next-steps list |

The LCD is write-only in this design — tie R/W to ground. The code never reads
back from it.

A Pi 3B or 3B+ runs this with no workarounds and no adapters: standard 15-pin
camera cable, populated 40-pin header, full-size HDMI, four USB-A ports. A Pi 4
behaves the same way. Compute is not a factor — the workload is one grayscale
conversion and one `pyzbar` decode per frame, with a 15-second sleep after every
successful scan.

Two exceptions to "or newer" are worth knowing if the board is ever swapped:
the **Pi 400** has no CSI camera port and cannot run this at all, and on a
**Pi 5** `RPi.GPIO` does not work against the RP1 I/O controller, so `RPLCD`
will not initialize until `rpi-lgpio` is installed as a drop-in replacement.
The Pi 5 also rules out the LED strip outright — `rpi_ws281x` has no Pi 5
support at all, and there is no drop-in fix for that one.

### Pin assignments

`RPLCD` is configured in BOARD numbering; `gpiozero` and `rpi_ws281x` use BCM.
Both are in play at once.

| Function | BOARD pin | BCM | Status |
| --- | --- | --- | --- |
| LCD RS | 19 | GPIO10 | wired |
| LCD E | 18 | GPIO24 | wired |
| LCD D4 | 16 | GPIO23 | wired |
| LCD D5 | 11 | GPIO17 | wired |
| LCD D6 | 12 | GPIO18 | wired |
| LCD D7 | 15 | GPIO22 | wired |
| Buzzer + | 38 | GPIO20 | wired — moved from pin 40 for the strip |
| Buzzer − | 39 | GND | wired |
| LED strip data | 40 | GPIO21 | wired |
| LED strip ground | any GND — 34 in the diagram | — | wired, **pin not recorded** |
| *(keep free — PWM0 fallback for the strip)* | 32 | GPIO12 | reserved |

No pins collide. LCD RS sits on GPIO10, which is SPI MOSI, so **SPI must stay
disabled** in `raspi-config`.

### LED status strip

The full write-up, with a diagram, is in
[docs/led-strip-wiring.md](docs/led-strip-wiring.md) — this is the summary.

A 50-LED WS2812B RGB strip shows scan results at a distance. It wipes purple at
startup, stays purple while idle, turns green for a logged badge and red for an
unauthorized one — held until the kiosk is ready for the next scan — and turns
off when the kiosk quits.

`rpi_ws281x` cannot bit-bang the WS2812B protocol from an arbitrary pin — it
hands timing to one of three peripherals, and each is hard-wired to specific
GPIOs:

| Route | Pins it can use | Status here |
| --- | --- | --- |
| PWM0 | GPIO18 (pin 12), GPIO12 (pin 32) | GPIO18 is LCD D6. GPIO12 is free — the fallback |
| PWM1 | GPIO13 (pin 33), GPIO19 (pin 35) | free |
| PCM | **GPIO21 (pin 40)** | **the strip** |
| SPI0 MOSI | GPIO10 (pin 19) | LCD RS, and SPI must stay disabled |

The team put the strip on PCM and moved the buzzer from GPIO21 to GPIO20. That
is a good choice: unlike the PWM routes, PCM does not share hardware with the
analog audio, so `config.txt` needs no changes.

The Pi's code doesn't record what sits between the Pi and the strip. Check the
kiosk for these parts, and fit them in the PCB design if they're missing:

| Part | Requirement | Why |
| --- | --- | --- |
| Level shifter | **74AHCT125** (or any `HCT` buffer) | The Pi drives 3.3 V; WS2812B needs ≥3.5 V. Works on the bench, fails on a longer cable. An `HC` part will **not** do — `HCT` is the load-bearing part of the name |
| Series resistor | 470 Ω, ¼ W | Damps the data line |
| Bulk capacitor | 1000 µF, 10 V | Inrush at power-on otherwise resets the first LEDs |
| 5 V supply | **Separate from the Pi's PSU**, 5 V 4 A | 50 LEDs: ~0.76 A at idle purple, 3 A worst case at full white |

Two rules that matter more than the parts list:

- **Never power the strip from header pins 2/4.** They are unfused pass-through
  from the Pi's own PSU. Idle purple alone is ~0.76 A, all day. It does not just
  dim the strip — it sags the 5 V rail and corrupts the SD card.
- **Tie the grounds together** — strip, supply, and a Pi GND pin. The data
  signal is referenced to that return.

Config, software, and known traps:

- **DMA must be 10.** The Pi's own copy of the code used `dma=5`, which on a
  Pi 3 collides with the SD card controller and corrupts the filesystem.
  [code.py](code.py) now sets 10 explicitly.
- Do **not** enable I2S audio (`dtparam=i2s=on`, audio-HAT overlays) or add
  `dtoverlay=pwm`. Both claim hardware `rpi_ws281x` drives directly.
- It needs root, which [Use instructions](Use%20instructions) already provides
  via `sudo -E`.
- **Do not switch `gpiozero` to `PiGPIOFactory`.** It looks like a free upgrade
  for cleaner buzzer tones, but `pigpiod` times itself off the PCM block by
  default and will break the strip. gpiozero's default factory drives the
  buzzer with *software* PWM, which is why the two coexist today.
- `LED_BRIGHTNESS` is 255, matching the look tuned on the kiosk. Dropping it to
  ~60 cuts current roughly fourfold if the supply is marginal.

### Needed only to start and stop it

Not part of the running kiosk, but the program can't be launched or quit
without them today:

- Monitor and a full-size HDMI cable
- USB keyboard — required to launch the script and to press `q` to quit
- Mouse — the instructions say "might be optional but I wouldn't push it"

Eliminating these is the first item on the improvement list.

### Badge production

- Printer, cardstock or adhesive label stock
- Optional laminator, badge holders, lanyards
- Badges are generated on demand — see [Roster and badges](#roster-and-badges)

## Software dependencies

Kiosk ([code.py](code.py), runs on the Pi): `opencv-python` · `pyzbar` ·
`gspread` · `google-auth` · `picamera2` · `RPLCD` · `RPi.GPIO` · `gpiozero` ·
`keyboard` · `rpi_ws281x`

For `rpi_ws281x`, prefer `sudo apt install python3-rpi-ws281x` — Bookworm blocks
system-wide `pip`, and the kiosk runs against system packages.

Badge generator ([generate_badges.py](generate_badges.py), runs anywhere):
`gspread` · `google-auth` · `qrcode` · `Pillow`

## Operating it

Per [Use instructions](Use%20instructions): power-cycle the Pi, attach a
monitor and keyboard, then run

```bash
sudo -E python3 -u ~/QR_reader/code.py
```

Peripherals can be unplugged once it's running. Press `q` (keyboard reattached)
to stop, then `sudo shutdown now`.

## Roster and badges

The roster lives in the `master list of names` worksheet and never enters this
repo. Three columns, and both scripts depend on this layout:

| A | B | C |
| --- | --- | --- |
| Name | Title/subteam | Badge ID |

Column C is filled in by [generate_badges.py](generate_badges.py). Existing IDs
are left alone, so badges printed in an earlier season keep working.

To print badges:

```bash
python3 generate_badges.py --dry-run
```

then drop `--dry-run` to mint IDs and render PNGs into `badges/`. Each PNG shows
the QR code above the person's name, subteam, and ID, so badges can be sorted
and handed out. `badges/` and its `_roster.csv` are gitignored — they contain
names and stay local. Regenerate rather than archiving them.

IDs look like `1076-A7F3`, using an alphabet with no `0`, `1`, `I`, `L`, `O`, or
`U` so they can be read aloud without ambiguity when debugging a bad badge.

For the 2026 season the roster ran to 69 people: roughly 14 Mechanical,
13 Mentor, 6 Software, 4 Electrical, 3 Imagery, 3 Design, 2 Finance, 2 Faculty,
2 Coach, plus one-off leadership and competition roles (Engineering Captain,
Chief Technical Director, Primary Driver, Human Player, and so on).

## Configuration

The same three values are hardcoded at the top of both [code.py](code.py) and
[generate_badges.py](generate_badges.py), and must agree:

- The Google service-account key path, under `/home/pihirobotics/QR_reader/`
  (the key itself is on the Pi, never in this repo — `*.json` is gitignored)
- The spreadsheet name, `PiHi samurai NEW attendance sheet QR test 61`
- The worksheet names, `login logs` and `master list of names`

The generator needs the read/write `spreadsheets` scope to write column C. The
kiosk only reads, but currently requests the same broad scopes as before.

[code.py](code.py) also has `ALLOW_LEGACY_NAME_BADGES`, default `False`. Set it
`True` only while old `Name,Subteam` badges are still in circulation, and turn
it off once everyone has been reprinted.

## Known issues

- **The old badge zip was purged from git history on 2026-08-13.**
  `PihiQRcodes_ready.zip` held the 2026 name-encoding badge set, where each PNG
  decoded to `Name,Subteam` — student data. It was removed with `git
  filter-repo --path PihiQRcodes_ready.zip --invert-paths` and force-pushed, so
  every SHA from the old `721c0c0` onward was rewritten and that commit, which
  contained only the zip, no longer exists. Two things this does **not** settle:
  GitHub keeps the old objects fetchable by direct SHA URL until Support purges
  the repo's cached views, so that request has to be made separately; and the
  archive was public in an org repo before the rewrite, so this limits future
  exposure rather than undoing past exposure. **Anyone holding a clone from
  before the rewrite must re-clone** — pulling will drag the old history back in.
- **`Elctrical` typo** in one subteam value. Now fixable in the roster sheet
  alone — subteams are resolved at scan time, so no badge needs reprinting.
- **The Pi may still be running its own older code.** Until the Pi is updated
  from this repo, it runs `dma=5` (see [LED status strip](#led-status-strip)) and
  the old name-encoding badges. Deploying this repo's [code.py](code.py) fixes
  the DMA, but also switches to badge IDs — plan the reprint first, or set
  `ALLOW_LEGACY_NAME_BADGES` for the transition.
- **The roster is read once at startup**, so adding a person, or minting their
  ID, requires restarting the kiosk.
- **The `q` quit check sits outside the scan loop** and only runs between
  frames; combined with the 15-second post-scan sleep, stopping can take a
  while. `keyboard` also requires root, which is why the run command uses
  `sudo -E`.
- **Neither script has been run end-to-end yet.** Both parse, but the ID scheme
  is untested against the live sheet — in particular, whether `master list of
  names` already has a header row and a subteam column in B.

## Next steps

- Simplify the starting sequence, so no monitor or keyboard is needed
- Design a PCB so a breadboard is not being used
- Make a better case that would house said PCB
- Have a system up so the status can be remotely altered — turn it on and off
  without needing to be there
- **Audit the LED strip wiring** against
  [docs/led-strip-wiring.md](docs/led-strip-wiring.md): which GND pin it uses,
  how it is powered, and whether it has a level shifter, series resistor, and
  bulk capacitor. Record the answers in that doc. Roll the pin 40 data line, the
  74AHCT125, and the separate 5 V input into the PCB design above

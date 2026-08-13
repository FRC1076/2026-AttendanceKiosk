# 2026 Attendance Kiosk

A Raspberry Pi QR-code kiosk that logs build-season attendance for FRC Team 1076
(PiHi Samurai). A team member holds their printed badge up to the camera; the Pi
decodes the QR code, resolves it against a roster, appends a timestamped row to
a Google Sheet, and confirms the scan on a small LCD with a buzzer chirp.

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
   accept chime or a single low reject tone. The loop then pauses ~15 seconds
   before accepting another scan.

## Repository contents

| Path | What it is |
| --- | --- |
| [code.py](code.py) | The entire kiosk program — one file, one `while True` loop. Runs on the Pi. |
| [generate_badges.py](generate_badges.py) | Mints badge IDs into the roster sheet and renders printable PNGs into a local, gitignored `badges/`. Run on any machine with the service-account key. |
| [Use instructions](Use%20instructions) | Step-by-step operating procedure for starting and stopping the kiosk at a build session. |
| [PihiQRcodes_ready.zip](PihiQRcodes_ready.zip) | **Superseded — pending removal.** The 2026 name-encoding badge set. Each PNG decodes to `Name,Subteam`, so the archive is student data and should be purged from git history. |

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

### Pin assignments

`RPLCD` is configured in BOARD numbering, `gpiozero` uses BCM. Both are in play
at once.

| Function | BOARD pin | BCM |
| --- | --- | --- |
| LCD RS | 19 | GPIO10 |
| LCD E | 18 | GPIO24 |
| LCD D4 | 16 | GPIO23 |
| LCD D5 | 11 | GPIO17 |
| LCD D6 | 12 | GPIO18 |
| LCD D7 | 15 | GPIO22 |
| Buzzer | 40 | GPIO21 |

No pins collide. LCD RS sits on GPIO10, which is SPI MOSI, so **SPI must stay
disabled** in `raspi-config`.

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
`keyboard`

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

- **The old badge zip is still in git history.** Removing the file in a new
  commit is not enough — the blob remains reachable from commit `721c0c0`.
  Purging it needs a history rewrite (`git filter-repo --path
  PihiQRcodes_ready.zip --invert-paths`), a force-push, and a heads-up to anyone
  holding a clone.
- **`Elctrical` typo** in one subteam value. Now fixable in the roster sheet
  alone — subteams are resolved at scan time, so no badge needs reprinting.
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

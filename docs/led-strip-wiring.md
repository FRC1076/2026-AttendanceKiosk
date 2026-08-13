# LED strip wiring plan — WS2812B status light

Adds an addressable RGB strip to the kiosk for at-a-glance scan feedback (green =
logged, red = unauthorized, amber = ready/waiting), without moving a single wire
that is already on the board.

**Companion diagram:** [led-strip-wiring.svg](led-strip-wiring.svg)

Target board is the Pi 3B the team runs today. See
[Pi 5 caveat](#pi-5-does-not-work-with-this-plan) before swapping boards.

---

## The short version

| | |
| --- | --- |
| Data pin | **GPIO12 — physical pin 32** |
| Ground reference | **Physical pin 34** (adjacent GND) |
| Peripheral used | Hardware PWM0, channel 0, via DMA |
| Library | `rpi_ws281x` |
| Pins that have to move | **None** |
| New `config.txt` line | `dtparam=audio=off` |
| New parts | 74AHCT125 level shifter, 470 Ω resistor, 1000 µF cap, separate 5 V supply |

The strip is **not** powered from the Pi's header.

---

## Why GPIO12

`rpi_ws281x` does not bit-bang the WS2812B protocol from a general GPIO. It hands
the job to one of three hardware peripherals, and each peripheral can only be
routed to specific pins. That is the entire constraint:

| Peripheral | Pins it can use | Status in this build |
| --- | --- | --- |
| PWM0 | GPIO12 (pin 32), GPIO18 (pin 12) | GPIO18 is **LCD D6**. GPIO12 is **free**. |
| PWM1 | GPIO13 (pin 33), GPIO19 (pin 35) | Both free — usable backup |
| PCM | GPIO21 (pin 40) | **Buzzer** |
| SPI0 MOSI | GPIO10 (pin 19) | **LCD RS**, and SPI must stay disabled |

So three of the four routes are already occupied by the LCD and the buzzer, which
is where the GPIO18 collision in the README comes from. GPIO12 is PWM0's
*primary* pin (ALT0) rather than the alternate, it is unused, and it maps to
`rpi_ws281x` channel 0 — the default, best-tested path in the library.

**Backup if GPIO12 is ever needed for something else:** GPIO13 (pin 33), with
`channel=1` passed to the library. Keep pin 33 unpopulated for that reason.

---

## Full header map after the change

Physical pin numbers. `RPLCD` is configured in BOARD numbering and `gpiozero`
in BCM, so both are shown.

| Pin | BCM | Assigned to | State |
| --- | --- | --- | --- |
| 2 | 5V | LCD VDD | existing |
| 11 | GPIO17 | LCD D5 | existing |
| 12 | GPIO18 | LCD D6 | existing — *this is why PWM0-alt is unavailable* |
| 14 | GND | LCD VSS + R/W + backlight cathode | existing |
| 15 | GPIO22 | LCD D7 | existing |
| 16 | GPIO23 | LCD D4 | existing |
| 18 | GPIO24 | LCD E | existing |
| 19 | GPIO10 | LCD RS | existing — *SPI0 must stay off* |
| **32** | **GPIO12** | **WS2812B data → level shifter** | **new** |
| **34** | **GND** | **Common ground → level shifter, strip, PSU** | **new** |
| 33 | GPIO13 | *reserved as PWM1 backup* | keep free |
| 39 | GND | Buzzer − | existing |
| 40 | GPIO21 | Buzzer + | existing |
| 27, 28 | ID_SD / ID_SC | HAT EEPROM | never use |

Everything else on the header is unused and stays that way.

GPIO current draw across all pins is **24 mA of the 50 mA budget** — the strip
draws nothing from the header, only the data pin does, and that sinks into a
buffer input.

---

## Parts to add

| Part | Spec | Why it is not optional |
| --- | --- | --- |
| Level shifter | **74AHCT125** (quad buffer, DIP-14) | Pi outputs 3.3 V. WS2812B wants V<sub>IH</sub> ≥ 0.7 × 5 V = **3.5 V**. 3.3 V is out of spec — it often works on the bench and then fails on a longer cable in the shop. `HCT` is the key part of the part number: TTL input thresholds, so 3.3 V reads as a solid high while the chip runs on 5 V. |
| Series resistor | **470 Ω**, ¼ W (330–500 Ω fine) | Damps reflections on the data line and limits current into the first LED's input diode on power-up. |
| Bulk capacitor | **1000 µF, 10 V** electrolytic | The strip's inrush at power-on can sag the rail enough to reset the first LEDs. Fit it across the strip's V+/GND at the strip end. **Polarity matters** — stripe goes to GND. |
| 5 V supply | Separate PSU, sized below | See [Power budget](#power-budget). |
| Strip | WS2812B or SK6812 | SK6812 (RGBW) is protocol-compatible; pass `strip_type=ws.SK6812_STRIP_GRBW`. |

Alternatives to the 74AHCT125 if that is what the parts bin has: 74HCT245,
SN74LV1T34, or a 74HCT14. Any `HCT`-family buffer works. A `HC`-family part does
**not** — it has CMOS thresholds and 3.3 V will be marginal.

### The cheap fallback, and why it is a fallback

Dropping the *first LED's* supply to ~4.4 V through a 1N4001 diode in series with
its V+ lowers that LED's logic threshold to ~3.1 V, so the Pi's 3.3 V clears it.
It works, it costs ten cents, and it is what a lot of tutorials do. It also means
the first LED runs dimmer and slightly off-colour from the rest of the strip, and
it gives you no margin. Use the level shifter for a kiosk that has to work
unattended during build season.

---

## Power budget

WS2812B draws up to **60 mA per LED** at full white, 100 % brightness — that is
20 mA per colour channel.

| LEDs | Worst case (white, full) | Typical (one colour, 40 % bright) | Supply to buy |
| --- | --- | --- | --- |
| 8 | 0.48 A | ~0.15 A | 5 V 1 A |
| 16 | 0.96 A | ~0.3 A | 5 V 2 A |
| 30 | 1.8 A | ~0.6 A | 5 V 3 A |
| 60 | 3.6 A | ~1.2 A | 5 V 5 A |

Size the supply for the **worst case plus ~30 % headroom**, even if the code
never shows full white — a bug that writes `(255,255,255)` to every pixel should
not brown out the kiosk.

Two rules that matter more than the numbers:

1. **Do not feed the strip from header pins 2/4 (5 V).** Those are unfused
   pass-through from the Pi's own PSU. A strip pulling an amp through them will
   sag the 5 V rail, and the usual symptom is not a dark strip — it is SD card
   corruption and a kiosk that will not boot on Saturday morning.
2. **Tie the grounds together.** Strip GND, PSU GND, and Pi header pin 34 must be
   common. The data signal is referenced to ground; without a shared return the
   strip sees garbage or nothing.

Set a brightness ceiling in software (`brightness=60` out of 255 is a good
starting point). It cuts current by roughly three quarters and stops the strip
being blinding in a lit shop.

For strips over ~30 LEDs, inject 5 V and GND again at the far end from the same
supply — the strip's own copper traces are thin and the far end will go brown.

---

## Wiring, connection by connection

Physical pin numbers on the Pi. 74AHCT125 pin numbers are the DIP-14 pinout
(pin 1 at the notch, counting counter-clockwise).

### Data path

| From | To | Notes |
| --- | --- | --- |
| Pi pin 32 (GPIO12) | 74AHCT125 pin 2 (`1A`) | 3.3 V logic in |
| 74AHCT125 pin 3 (`1Y`) | 470 Ω resistor | 5 V logic out |
| 470 Ω resistor | Strip `DIN` | Keep this leg short |

### Level shifter power and housekeeping

| From | To | Notes |
| --- | --- | --- |
| 74AHCT125 pin 14 (`VCC`) | +5 V rail | From the external PSU, not the Pi |
| 74AHCT125 pin 7 (`GND`) | Common GND | |
| 74AHCT125 pin 1 (`1OE`) | GND | Active-low output enable — **must** be pulled low or the buffer stays tri-stated |
| 74AHCT125 pins 4, 10, 13 (`2OE`, `3OE`, `4OE`) | +5 V | Disables the three unused buffers |
| 74AHCT125 pins 5, 9, 12 (`2A`, `3A`, `4A`) | GND | Never leave CMOS inputs floating — they oscillate and draw current |

### Power and ground

| From | To | Notes |
| --- | --- | --- |
| PSU +5 V | Strip `+5V` | |
| PSU GND | Strip `GND` | |
| PSU GND | Pi pin 34 (GND) | **The common-ground link. Do not skip.** |
| 1000 µF cap `+` | Strip `+5V` | At the strip end |
| 1000 µF cap `−` (stripe) | Strip `GND` | |

### Unchanged

| Component | Connection |
| --- | --- |
| LCD | Pins 2, 11, 12, 14, 15, 16, 18, 19 + contrast pot on V0, R/W tied to GND |
| Buzzer | Pins 39, 40 |
| Camera | CSI ribbon — uses no header pins |

### Order of assembly

1. Wire and verify grounds first, with the PSU **off**.
2. Level shifter power and the three tie-offs (`1OE` low, unused `OE` high,
   unused `A` low).
3. Data path last.
4. Power the PSU before, or at the same time as, the Pi — never the other way
   round with the data line connected. Driving 5 V-referenced data into an
   unpowered strip can push current through its input protection diodes.

---

## Software configuration

### `/boot/config.txt`

On the Pi 3, the file is at `/boot/config.txt`. (Pi 4/5 on Bookworm:
`/boot/firmware/config.txt`.)

```
dtparam=audio=off
```

That single line is required. The PWM block is shared with the analog audio path,
and leaving audio enabled makes the LED timing jitter — the symptom is random
pixels flashing the wrong colour.

**Do not add `dtoverlay=pwm`.** `rpi_ws281x` programs the PWM peripheral directly
through `/dev/mem` and DMA; the kernel overlay would claim the same hardware and
the two fight. This is a common wrong answer from pin-assignment tooling, and the
LED output will be silently broken if you take it.

SPI stays disabled, exactly as today — LCD RS is on GPIO10.

Reboot after editing.

### Install

Bookworm blocks system-wide `pip`, and the kiosk runs against system packages
(`picamera2` is installed that way), so prefer apt:

```bash
sudo apt install python3-rpi-ws281x
```

If that package is unavailable on the installed OS:

```bash
sudo pip3 install --break-system-packages rpi_ws281x
```

### Permissions

`rpi_ws281x` needs `/dev/mem` and DMA access, so it must run as root. The kiosk
already does — [Use instructions](../Use%20instructions) launches it with
`sudo -E python3`. No change needed, but the script will now fail with a
permissions error rather than just not lighting up if that ever changes.

### DMA channel

Leave it at the library default, **DMA 10**.

Older examples and blog posts pass `dma=5`. On a Pi 3 that channel is used by the
SD card controller, and the result is filesystem corruption. If you copy code
from a tutorial, check this line.

### Initialization

```python
from rpi_ws281x import PixelStrip, Color

LED_COUNT      = 16      # match the strip actually fitted
LED_PIN        = 12      # BCM 12 = physical pin 32, hardware PWM0
LED_FREQ_HZ    = 800000  # WS2812B bit rate
LED_DMA        = 10      # library default -- do NOT use 5 on a Pi 3
LED_BRIGHTNESS = 60      # 0-255. Caps current draw and shop glare.
LED_INVERT     = False   # True only if the level shifter inverts (74AHCT125 does not)
LED_CHANNEL    = 0       # PWM0 -> channel 0. GPIO13/19 would be channel 1.

strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                   LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

READY        = Color(40, 25, 0)   # amber
ACCEPTED     = Color(0, 120, 0)   # green
UNAUTHORIZED = Color(140, 0, 0)   # red

def fill(color):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()

fill(READY)
```

`Color()` takes RGB and reorders to the strip's native GRB internally — do not
pre-swap the channels yourself.

### One thing to watch in `code.py`

[code.py:105](../code.py) sleeps 15 seconds inside the `for qr` loop after every
scan. Any LED animation written as a blocking `for`/`sleep` loop will stack on top
of that and make the kiosk feel even less responsive, and the `q` quit check —
already noted as sluggish in the README's known issues — gets worse.

Set a **static colour** on each scan result (`fill(ACCEPTED)` / `fill(UNAUTHORIZED)`),
let it hold through the existing sleep, and return to `READY` at the top of the
loop. If an animated effect is wanted later, run it on a `threading.Thread` with a
flag rather than inlining it.

---

## Warnings

### The buzzer and the strip do not conflict — unless the pin factory changes

`gpiozero`'s default pin factory (`RPi.GPIO`) drives `TonalBuzzer` with **software**
PWM, so it never claims the hardware PWM0 block that `rpi_ws281x` needs. They
coexist fine as configured today.

If anyone ever switches gpiozero to `PiGPIOFactory` — a reasonable-looking change,
since pigpio gives much cleaner tones — **it will break the LEDs**. `pigpiod` also
uses DMA and the PWM peripheral, and the two libraries will fight over them.
Symptoms are glitching colours, a hung `pigpiod`, or both. If cleaner buzzer tones
are wanted, move the buzzer to a hardware PWM pin under `rpi_ws281x`-free control,
or accept the software PWM.

### Pi 5 does not work with this plan

The README already notes that `RPi.GPIO` breaks on the Pi 5's RP1 I/O controller
and needs `rpi-lgpio`. `rpi_ws281x` is worse off: it has **no Pi 5 support at
all**. It reaches the PWM/DMA hardware through the SoC's memory map, and on the
Pi 5 those peripherals live behind RP1 where that approach does not work.

If the board is ever moved to a Pi 5, the options are an SPI-driven strip library,
or an external microcontroller doing the timing. Neither is a drop-in. This is a
new reason to stay on Pi 3/4 beyond the ones already listed.

### Pre-existing: the buzzer has no driver transistor

Not caused by this change, but worth fixing on the same bench session. A passive
piezo is an inductive load driven straight off GPIO21. Per-pin limit on the Pi is
16 mA and there is no flyback path. A small NPN (2N3904) with a base resistor and
a flyback diode is the correct drive. It has presumably been fine so far; it is
still on the wrong side of the spec.

### 5 V never touches a GPIO

The Pi's pins are not 5 V tolerant and have no protection. In this design the
only 5 V-referenced signal is the level shifter's *output*, which faces the
strip. The LCD is write-only with R/W tied to ground for the same reason. Keep it
that way.

---

## Verification

Before wiring the strip, confirm the pin can be driven:

```bash
sudo python3 -c "from rpi_ws281x import PixelStrip, Color; s=PixelStrip(1,12,800000,10,False,60,0); s.begin(); s.setPixelColor(0,Color(0,80,0)); s.show()"
```

Then, in order:

1. **Grounds** — continuity between Pi pin 34, PSU −, strip GND, and 74AHCT125
   pin 7 with the PSU off.
2. **Level shifter output** — scope or meter on pin 3 while running the snippet
   above; it should swing to ~5 V, not ~3.3 V. A 3.3 V swing means the chip is an
   `HC` part, not `HCT`, or `VCC` is on 3.3 V.
3. **First LED only** — set `LED_COUNT = 1` and confirm colour accuracy before
   lighting the whole strip. Wrong colours here mean a strip-type mismatch
   (RGB vs GRB), not a wiring fault.
4. **Full strip at low brightness**, then measure current at full white to check
   the supply.
5. **Run the kiosk end to end** and confirm the LCD still initializes. If the LCD
   goes blank after adding the strip, the cause is almost always a shared-ground
   or supply problem, not a pin conflict — nothing on the header moved.

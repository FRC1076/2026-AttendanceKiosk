# LED strip wiring — WS2812B status light

The kiosk has a 50-LED WS2812B RGB strip for feedback you can see from across
the shop: purple while it's ready, a green flash when a badge is logged, and a
red flash for an unauthorized one. The team built and ran it on the Pi in spring
2026. That code never reached this repo until 2026-09-27, when it was brought
over from the Pi's own copy of `code.py`.

**Companion diagram:** [led-strip-wiring.svg](led-strip-wiring.svg)

Target board is the Pi 3B the team runs today. See
[Pi 5 caveat](#pi-5-cannot-drive-this-strip) before swapping boards.

> An earlier version of this doc planned the strip on GPIO12 / pin 32, written
> before anyone knew the strip already existed. The real kiosk uses GPIO21 /
> pin 40, and this doc now describes that.

---

## What is known and what isn't

The Pi's code confirms the data pin, the buzzer move, the LED count, and the
colours. It says nothing about the parts between the Pi and the strip. **Check
the kiosk against the list below and correct this doc where it differs.**

| | Status |
| --- | --- |
| Strip data on GPIO21, physical pin 40 | confirmed from code |
| Buzzer moved to GPIO20, physical pin 38 | confirmed from code |
| 50 LEDs, RGB (not RGBW) | confirmed |
| Which GND pin the strip uses | **not recorded.** Any GND works; the diagram shows pin 34 |
| Level shifter, series resistor, bulk capacitor | **not recorded.** Recommended below |
| How the strip is powered | **not recorded.** Must not be the Pi's header 5 V (see [Power budget](#power-budget)) |

---

## The short version

| | |
| --- | --- |
| Data pin | **GPIO21 — physical pin 40** |
| Ground reference | Any GND pin — **pin 34** shown in the diagram |
| Peripheral used | PCM, channel 0, via DMA |
| Library | `rpi_ws281x` |
| Moved to make room | Buzzer, from GPIO21 (pin 40) to **GPIO20 (pin 38)** |
| `config.txt` changes | **None** |
| Recommended parts | 74AHCT125 level shifter, 470 Ω resistor, 1000 µF cap, separate 5 V supply |

The strip is **not** powered from the Pi's header.

---

## Why GPIO21

`rpi_ws281x` does not bit-bang the WS2812B protocol from a general GPIO. It hands
the job to one of three hardware peripherals, and each peripheral can only be
routed to specific pins:

| Peripheral | Pins it can use | Status in this build |
| --- | --- | --- |
| PWM0 | GPIO12 (pin 32), GPIO18 (pin 12) | GPIO18 is **LCD D6**. GPIO12 is free — the fallback |
| PWM1 | GPIO13 (pin 33), GPIO19 (pin 35) | Both free |
| PCM | GPIO21 (pin 40) | **The strip** |
| SPI0 MOSI | GPIO10 (pin 19) | **LCD RS**, and SPI must stay disabled |

GPIO21 used to be the buzzer. The team moved the buzzer to GPIO20. That was
easy because a buzzer can run from any pin: gpiozero drives it with software
PWM.

PCM is a good route for this kiosk. The two PWM routes share hardware with the
Pi's analog audio, so they need `dtparam=audio=off`. PCM doesn't, and there is
nothing to add to `config.txt`. The cost is that PCM is also the Pi's I2S
digital-audio block, so no I2S audio HAT or overlay can be used alongside the
strip.

**Fallback if PCM is ever needed for something else:** GPIO12 (pin 32) on PWM0,
channel 0. Moving there means adding `dtparam=audio=off`. Keep pin 32 unpopulated
so that option stays open.

---

## Full header map

Physical pin numbers. `RPLCD` is configured in BOARD numbering, and
`gpiozero` and `rpi_ws281x` use BCM, so both are shown.

| Pin | BCM | Assigned to | Notes |
| --- | --- | --- | --- |
| 2 | 5V | LCD VDD | |
| 11 | GPIO17 | LCD D5 | |
| 12 | GPIO18 | LCD D6 | *this is why PWM0's GPIO18 pin is unavailable* |
| 14 | GND | LCD VSS + R/W + backlight cathode | |
| 15 | GPIO22 | LCD D7 | |
| 16 | GPIO23 | LCD D4 | |
| 18 | GPIO24 | LCD E | |
| 19 | GPIO10 | LCD RS | *SPI0 must stay off* |
| 32 | GPIO12 | *keep free — PWM0 fallback for the strip* | |
| **34** | **GND** | **Strip common ground** | shown in the diagram; confirm on the kiosk |
| **38** | **GPIO20** | **Buzzer +** | moved from pin 40 |
| 39 | GND | Buzzer − | |
| **40** | **GPIO21** | **Strip data → level shifter** | PCM |
| 27, 28 | ID_SD / ID_SC | HAT EEPROM | never use |

Everything else on the header is unused.

---

## Recommended parts

These are what the strip *should* have between it and the Pi. The kiosk may not
have all of them — see [What is known](#what-is-known-and-what-isnt). A WS2812B
often works straight from a 3.3 V pin on the bench, which is why a strip can run
for a whole season without them. It stops working when a cable gets longer, the
supply sags, or the shop is cold.

| Part | Spec | Why it is not optional |
| --- | --- | --- |
| Level shifter | **74AHCT125** (quad buffer, DIP-14) | Pi outputs 3.3 V. WS2812B wants V<sub>IH</sub> ≥ 0.7 × 5 V = **3.5 V**. 3.3 V is out of spec. `HCT` is the key part of the part number: TTL input thresholds, so 3.3 V reads as a solid high while the chip runs on 5 V. |
| Series resistor | **470 Ω**, ¼ W (330–500 Ω fine) | Damps reflections on the data line and limits current into the first LED's input diode on power-up. |
| Bulk capacitor | **1000 µF, 10 V** electrolytic | The strip's inrush at power-on can sag the rail enough to reset the first LEDs. Fit it across the strip's V+/GND at the strip end. **Polarity matters** — stripe goes to GND. |
| 5 V supply | Separate PSU, **5 V 4 A** for 50 LEDs | See [Power budget](#power-budget). |
| Strip | WS2812B RGB, 50 LEDs | Confirmed RGB. The Pi's old `lighttest.py` set the pixel order to `GRBW` — that was wrong for this strip. Use the library's default GRB type. |

Alternatives to the 74AHCT125 if that is what the parts bin has: 74HCT245,
SN74LV1T34, or a 74HCT14. Any `HCT`-family buffer works. An `HC`-family part does
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

What this kiosk actually shows, at 50 LEDs and full brightness:

| State | Colour | Per LED | Whole strip |
| --- | --- | --- | --- |
| Idle — most of the time | purple `(75, 0, 120)` | ~15 mA | **~0.76 A, continuous** |
| Accepted flash | green `(0, 255, 0)` | 20 mA | 1.0 A |
| Unauthorized flash | red `(255, 0, 0)` | 20 mA | 1.0 A |
| Worst case (a bug writes full white) | `(255, 255, 255)` | 60 mA | **3.0 A** |

Size the supply for the **worst case plus ~30 % headroom** — **5 V 4 A** for this
strip — even though the code never shows full white.

| LEDs | Worst case (white, full) | Supply to buy |
| --- | --- | --- |
| 16 | 0.96 A | 5 V 2 A |
| 30 | 1.8 A | 5 V 3 A |
| **50** | **3.0 A** | **5 V 4 A** |
| 60 | 3.6 A | 5 V 5 A |

Two rules that matter more than the numbers:

1. **Do not feed the strip from header pins 2/4 (5 V).** Those are unfused
   pass-through from the Pi's own PSU. Even the idle purple alone is ~0.76 A
   around the clock, on top of the Pi and camera. The usual symptom is not a
   dark strip — it is SD card corruption and a kiosk that will not boot on
   Saturday morning.
2. **Tie the grounds together.** Strip GND, PSU GND, and a Pi GND pin must be
   common. The data signal is referenced to ground; without a shared return the
   strip sees garbage or nothing.

`LED_BRIGHTNESS` in [code.py](../code.py) is 255 to match the look the team
tuned on the kiosk. Dropping it to ~60 cuts every figure above by roughly three
quarters, and is the first thing to try if the supply is marginal.

At 50 LEDs, inject 5 V and GND again at the far end from the same supply — the
strip's own copper traces are thin and the far end goes brown at full green.

---

## Wiring, connection by connection

Physical pin numbers on the Pi. 74AHCT125 pin numbers are the DIP-14 pinout
(pin 1 at the notch, counting counter-clockwise).

### Data path

| From | To | Notes |
| --- | --- | --- |
| Pi pin 40 (GPIO21) | 74AHCT125 pin 2 (`1A`) | 3.3 V logic in |
| 74AHCT125 pin 3 (`1Y`) | 470 Ω resistor | 5 V logic out |
| 470 Ω resistor | Strip `DIN` | Keep this leg short |

Without a level shifter, pin 40 goes through the 470 Ω resistor straight to
`DIN`.

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
| PSU GND | Pi pin 34 (GND) | **The common-ground link. Do not skip.** Any Pi GND pin works |
| 1000 µF cap `+` | Strip `+5V` | At the strip end |
| 1000 µF cap `−` (stripe) | Strip `GND` | |

### Rest of the kiosk

| Component | Connection |
| --- | --- |
| LCD | Pins 2, 11, 12, 14, 15, 16, 18, 19 + contrast pot on V0, R/W tied to GND |
| Buzzer | Pins 38 (+) and 39 (−) |
| Camera | CSI ribbon — uses no header pins |

### Order of assembly

When rebuilding the strip wiring, or fitting the protection parts:

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

Nothing to add for the PCM route.

Do **not** enable I2S audio — no `dtparam=i2s=on`, and no audio-HAT overlays such
as `hifiberry-dac`. They claim the PCM block the strip runs on.

Do **not** add `dtoverlay=pwm` either, even if pin-assignment tooling suggests it.
`rpi_ws281x` programs the hardware directly through `/dev/mem`, and a kernel
driver on the same block fights it.

SPI stays disabled — LCD RS is on GPIO10.

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
`sudo -E python3`. If that ever changes, the script fails at `strip.begin()`
with a permissions error.

### DMA channel

**DMA 10.** [code.py](../code.py) sets it explicitly.

The Pi's own copy of `code.py`, and its `ws281test.py`, passed `dma=5` — copied
from older tutorials. On a Pi 3, channel 5 is used by the SD card controller,
and the result is filesystem corruption. If the kiosk has had unexplained SD
card trouble, this is the first suspect. Replace those files on the Pi with the
ones in this repo.

### Initialization

As in [code.py](../code.py):

```python
from rpi_ws281x import PixelStrip, Color

LED_COUNT      = 50
LED_PIN        = 21      # BCM 21 = physical pin 40, PCM
LED_FREQ_HZ    = 800000  # WS2812B bit rate
LED_DMA        = 10      # not 5 -- on a Pi 3 channel 5 belongs to the SD card
LED_INVERT     = False   # True only if the level shifter inverts (74AHCT125 does not)
LED_BRIGHTNESS = 255     # 0-255. Lower it to cut current and glare.
LED_CHANNEL    = 0       # PCM and PWM0 are channel 0; PWM1 would be 1

strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                   LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

IDLE         = Color(75, 0, 120)   # purple
ACCEPTED     = Color(0, 255, 0)
UNAUTHORIZED = Color(255, 0, 0)
OFF          = Color(0, 0, 0)
```

`Color()` takes RGB and the library reorders it to the strip's native GRB — do
not pre-swap the channels yourself.

### Behaviour, and one thing to know about it

- **Startup:** a purple wipe down the strip, once the sheet is reachable and the
  roster is loaded.
- **Scan:** green or red for as long as the chime plays (~0.5 s), then back to
  purple.
- **Quit:** the strip turns off.

The flash returns to purple *before* the 15-second pause in
[code.py](../code.py) that follows every scan. So for those 15 seconds the strip
says "ready" while the kiosk is ignoring badges. That is how it ran on the Pi,
and it was kept as-is. If it confuses people, drop the `fill(IDLE)` at the end
of `show_accepted` and `show_unauthorized`, and call it after the
`time.sleep(15)` instead. The strip then holds the result colour until the kiosk
is ready again.

Keep effects static. A blocking animation loop stacks on top of the 15-second
pause, and the already-sluggish `q` quit gets worse. If an animated effect is
wanted, run it on a `threading.Thread` rather than inline.

---

## Warnings

### Do not switch gpiozero to `PiGPIOFactory`

It looks like a free upgrade for cleaner buzzer tones. But `pigpiod` times its
PWM with a hardware peripheral, and its default choice is PCM — the block the
strip runs on. The two will fight: glitching colours, a hung `pigpiod`, or
both. gpiozero's default factory drives the buzzer with software PWM, which is
why the buzzer and strip coexist today.

### Pi 5 cannot drive this strip

`rpi_ws281x` has **no Pi 5 support at all**. It reaches the PCM/PWM/DMA hardware
through the SoC's memory map, and on the Pi 5 those peripherals sit behind the
RP1 I/O controller, where that approach does not work. Unlike the `RPi.GPIO`
problem in the README, there is no drop-in fix.

If the board is ever moved to a Pi 5, the options are an SPI-driven strip
library, or an external microcontroller doing the timing. Neither is a drop-in.

### Pre-existing: the buzzer has no driver transistor

A passive piezo is driven straight off GPIO20. Per-pin limit on the Pi is 16 mA
and there is no flyback path. A small NPN (2N3904) with a base resistor and a
flyback diode is the correct drive. It has been fine so far; it is still on the
wrong side of the spec.

### 5 V never touches a GPIO

The Pi's pins are not 5 V tolerant and have no protection. In this design the
only 5 V-referenced signal is the level shifter's *output*, which faces the
strip. The LCD is write-only with R/W tied to ground for the same reason. Keep it
that way.

---

## Verification

[hardware_tests/led_strip_test.py](../hardware_tests/led_strip_test.py) wipes
the strip purple, holds 5 seconds, and turns it off:

```bash
sudo python3 hardware_tests/led_strip_test.py
```

When checking or rebuilding the wiring, in order:

1. **Grounds** — continuity between the Pi GND pin, PSU −, strip GND, and
   74AHCT125 pin 7, with the PSU off.
2. **Level shifter output** — scope or meter on pin 3 while running the test; it
   should swing to ~5 V, not ~3.3 V. A 3.3 V swing means the chip is an `HC`
   part, not `HCT`, or `VCC` is on 3.3 V.
3. **Colours** — the wipe should be purple, not green-ish or teal. Wrong colours
   mean a strip-type mismatch, not a wiring fault.
4. **Current** — measure the supply current at idle purple. ~0.76 A at full
   brightness is expected; much more means the LED count or brightness is not
   what the code says.
5. **Run the kiosk end to end** and confirm the LCD still initializes and the
   buzzer still sounds on pin 38. A blank LCD after strip work is almost always a
   shared-ground or supply problem, not a pin conflict.

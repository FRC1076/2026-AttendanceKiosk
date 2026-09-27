# Test badges

Scan these to check the kiosk end to end: camera, decode, LCD, buzzer, and LED
strip. They hold no student data, need no roster entry, and are safe to share.

| Badge | Encodes | What the kiosk should do |
| --- | --- | --- |
| [1_accept.png](1_accept.png) | `TEST-OK` | LCD `Test: not logged`, rising chime, strip **green**. Nothing written to the sheet |
| [2_accept_and_log.png](2_accept_and_log.png) | `TEST-LOG` | LCD `TEST BADGE`, rising chime, strip **green**, and a `TEST BADGE, Test` row appended to `login logs` |
| [3_reject.png](3_reject.png) | `TEST-REJECT` | LCD `Unauthorized`, low tone, strip **red** |

After each scan, the strip holds its colour for the 15-second pause, then goes
back to purple. Wait for purple before the next badge.

Print [all_test_badges.png](all_test_badges.png) for all three on one page, and
**cut them apart before scanning.** The kiosk reads every code in view, so the
whole sheet would run all three in a row — 45 seconds of pauses, and a logged
row you may not have wanted.

## What a failure tells you

- **Nothing happens at all** — the camera isn't seeing the badge. Check focus
  and distance with `python3 hardware_tests/camera_preview.py`.
- **`TEST-OK` works but `TEST-LOG` stalls or crashes** — the sheet write is
  failing. Check the network and the service-account key.
- **`TEST-REJECT` goes green** — someone added `TEST-REJECT` to the roster.
  Take it out.
- **Real badges fail but `TEST-OK` works** — the kiosk is fine; the roster or
  the badge IDs are the problem.
- **One output is missing** (no sound, no LCD text, no strip) — run that part's
  script in [hardware_tests/](../hardware_tests).

Delete the `TEST BADGE` rows from `login logs` after testing.

## How they work

`TEST-OK` and `TEST-LOG` are built into `TEST_BADGES` in [code.py](../code.py),
so they work without touching the roster. `TEST-REJECT` is deliberately in
neither place, so it takes the same path as any unknown badge. Real badge IDs
always start with `1076-`, so a test ID can never collide with one.

Regenerate with:

```bash
python3 generate_badges.py --test
```

This needs only `qrcode` and `Pillow`, not the Sheets libraries or the key. The
IDs are listed in `TEST_BADGES` in both [generate_badges.py](../generate_badges.py)
and [code.py](../code.py), and the two lists must agree.

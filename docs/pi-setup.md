# Pi setup — the repo clone and the key

The kiosk Pi runs [code.py](../code.py) straight from a clone of this repo at
`~/2026-AttendanceKiosk`. The service-account key never goes in the repo; it
stays outside the clone at `~/QR_reader/service_account.json`, where code.py
looks for it. So:

- **New code** is a `git pull` on the Pi.
- **A new key** goes over once by USB stick.

The repo is public, so the Pi clones and pulls without a GitHub login. Don't
put one on it.

## Rules for the clone

- **Don't edit code on the Pi.** Change it on a laptop, push to `main`, then
  pull on the Pi. Edits made on the Pi block the next pull.
- **Pull only when you mean to update.** A pull takes whatever is on `main`,
  so scan the test badges after every pull.
- **Keep the key out of the clone.** `*.json` is gitignored, but a key inside
  the clone is one `git add -f` from being public, and `git clean -x` deletes
  it.

## First time: moving the Pi to the clone

Attach a monitor and keyboard, power the Pi on, and open a terminal.

**1. Check for git.** If this prints a version, skip the install.

```bash
git --version
```

```bash
sudo apt install git
```

**2. Clone the repo.**

```bash
git clone https://github.com/FRC1076/2026-AttendanceKiosk.git ~/2026-AttendanceKiosk
```

**3. Move the Pi's old files aside.** `~/QR_reader` should end up holding only
the key, so the old `~/QR_reader/code.py` can't be run by habit. Look first,
then move the old code.py and old key into a backup folder.

```bash
ls ~/QR_reader
```

```bash
mkdir -p ~/QR_reader/old
```

```bash
mv ~/QR_reader/code.py ~/QR_reader/*.json ~/QR_reader/old/
```

Move anything else the old setup used, such as `ws281test.py`, into `old/` as
well — the repo's versions replace it (see
[led-strip-wiring.md](led-strip-wiring.md#dma-channel)).

**4. Install the key**, following [Installing a new key](#installing-a-new-key)
from step 2.

**5. Start the kiosk and test it**, as in
[Starting and testing](#starting-and-testing).

**6. Clean up.** After a few good sessions, delete the backup:

```bash
rm -r ~/QR_reader/old
```

## Updating the code

**1. Check the clone is clean.** It should say `nothing to commit, working
tree clean`.

```bash
cd ~/2026-AttendanceKiosk
```

```bash
git status
```

If it lists changed files, someone edited on the Pi. `git diff` shows what
changed. Set the edits aside, and copy them to a laptop if they're worth
keeping:

```bash
git stash
```

**2. Pull and note the version.**

```bash
git pull
```

```bash
git log -1 --oneline
```

**3. Start the kiosk and test it**, as in
[Starting and testing](#starting-and-testing).

## Installing a new key

Do this when the key is replaced — not on every code update.

**1. On the laptop, copy the key to a USB stick**, renamed to
`service_account.json`. Replace `KEY.json` with the key's downloaded name and
`STICK` with the stick's name as Finder shows it. Eject the stick afterwards.

```bash
cp ~/Downloads/KEY.json /Volumes/STICK/service_account.json
```

**2. On the Pi, find the stick.** Plug it in and list the mounted drives. The
folder shown is the stick's name — use it for `STICK` below.

```bash
ls /media/pihirobotics
```

**3. Set the current key aside**, if there is one.

```bash
mkdir -p ~/QR_reader/old
```

```bash
mv ~/QR_reader/service_account.json ~/QR_reader/old/
```

**4. Copy in the new key.** `chmod 600` keeps it readable only by the Pi's
user; the kiosk runs under `sudo`, so it can still read it.

```bash
cp /media/pihirobotics/STICK/service_account.json ~/QR_reader/
```

```bash
chmod 600 ~/QR_reader/service_account.json
```

**5. Start the kiosk and test it**, as in
[Starting and testing](#starting-and-testing).

**6. Delete the key from the USB stick** — it works like a password for the
sheet. Once the new key has worked for a few sessions, delete the old one from
`~/QR_reader/old`, then retire it in its Google Cloud project (service account
→ Keys → delete).

## Starting and testing

```bash
sudo -E python3 -u ~/2026-AttendanceKiosk/code.py
```

The terminal should print `LED ready`, `Buzzer ready`, `LCD ready`,
`Connected to sheet`, then `Loaded N badge IDs`, where N is the number of
roster rows with a badge ID in column C. The strip wipes purple and the LCD
shows `Scanner ready`.

Scan the three badges in [test_badges/](../test_badges): one accepts, one
accepts and logs, one is rejected. Then scan one real badge. The `login logs`
tab should gain a `TEST BADGE` row and a row for the real badge.

The scripts in [hardware_tests/](../hardware_tests) run from the clone too —
`cd ~/2026-AttendanceKiosk` first.

## Going back

**To an earlier version of the code**, find the last good commit and check it
out. Git warns about a "detached HEAD"; that's expected.

```bash
cd ~/2026-AttendanceKiosk
```

```bash
git log --oneline -10
```

```bash
git checkout COMMIT
```

Return to the latest code with:

```bash
git checkout main
```

**To the previous key**, put it back from `old/`:

```bash
mv ~/QR_reader/old/service_account.json ~/QR_reader/
```

**To the Pi's setup from before the clone**, move the old files back and run
the old file. It logs to whichever sheet its own code.py names, and the badge-ID
badges won't scan on it.

```bash
mv ~/QR_reader/old/* ~/QR_reader/
```

```bash
sudo -E python3 -u ~/QR_reader/code.py
```

## If something goes wrong

| What you see | Likely cause |
| --- | --- |
| `Could not resolve host: github.com` | The Pi is offline. It needs the network for the sheet too. |
| `git pull` refuses: local changes would be overwritten | Someone edited on the Pi. See [Updating the code](#updating-the-code), step 1. |
| `FileNotFoundError` | The key isn't at `~/QR_reader/service_account.json`. Check the name with `ls ~/QR_reader`. |
| `No such file or directory: …/QR_reader/code.py` | The old run command. Start it from `~/2026-AttendanceKiosk/code.py`. |
| `invalid_grant` or `Invalid JWT` | The Pi's clock is wrong. Connect it to the network so it sets the time, then try again. |
| `403` or `PermissionError` | The sheet isn't shared with this key's service account, or the wrong key was copied. `generate_badges.py --creds KEY --dry-run` on a laptop checks both. |
| `WorksheetNotFound` | A tab was renamed. The tabs must be `login logs` and `master list of names`. |
| `Loaded 0 badge IDs` | Column C is empty — run `generate_badges.py` — or code.py points at a different sheet. |
| Every real badge is `Unauthorized` | The badges were printed from a different sheet, or they're old name badges. `ALLOW_LEGACY_NAME_BADGES` in code.py accepts those during a changeover. |

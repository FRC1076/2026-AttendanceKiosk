# Plan — check-out, live views, and faster scanning

Status: plan, not yet built. Written 2026-10-29 from the head coach's feature
requests, with the answers to the follow-up questions folded in. Revised
2026-10-30 after the coach's second round of feedback: the 2-hour timer is
gone, the end of a Build is now estimated from the cluster of check-outs, and
every row gets a Note column saying whether it was explicit or automatic.

## What the coach asked for

1. See who is checked in at a Build, any time, by walking up to a screen and
   clicking a few times.
2. See who left a Build early, the same way.
3. Students who forget to badge out get checked out automatically.
4. A spreadsheet or CSV with check-in and check-out date/times per student.
5. All of the above from a phone, even if less usable.
6. Three or more students can check in at almost the same time, so there are no
   lines in the ten minutes around the start and end of a Build.

Second round:

7. The 2-hour timer won't work in practice.
8. Most Builds end on the hour or half hour. Find the cluster of explicit
   check-outs, round it to the nearest hour or half hour, and use that time
   for the automatic check-outs.
9. Add a note column saying whether each record was automatic or explicit.

## Decisions already made

| Question | Answer |
| --- | --- |
| What screen does the coach use? | A regular monitor, keyboard, and mouse stay on the kiosk. |
| What is a Build? | **One per calendar day.** It starts at the first check-in that day. There's no timer and no schedule to keep. |
| When is a Build closed? | **After midnight**, or at the Pi's next boot if it was unplugged. Closing is when the automatic check-outs get written. |
| How does a student check out? | Scan again. First scan checks in, the next checks out. A repeat scan within 10 minutes of the last one says "Already in" / "Already out" and does nothing. |
| What time does an automatic check-out get? | **The Build's estimated end**: the centre of the main cluster of explicit check-outs, rounded to the **nearest** :00 or :30. Never always-down: 5:47 becomes 6:00, not 5:30. |
| How are rows marked? | A **Note** column on every row: `Explicit` (scanned), `Automatic` (auto check-out), or `Manual` (typed in by a person as a correction). |
| What counts as leaving early? | Checking out 30+ minutes before the Build's estimated end. |
| Who can open the views on the kiosk? | Anyone. Big buttons, no login. |
| How does the coach use a phone? | The Google Sheets app, on read-only tabs that update live. |

The first draft used "a Build ends 2 hours after the last check-out, once
nobody is checked in". That needed someone to have checked out, broke on long
Builds with quiet stretches, and gave forgetters the time of whoever happened
to scan last. Grouping by day and estimating the end from everyone's
check-outs avoids all three.

## Working out when a Build ended

When a Build is closed, the kiosk works out its end time from the explicit
check-outs:

1. Take each person's **last explicit check-out** of the day. Someone who
   stepped out and came back counts once, at their final check-out.
   Automatic, manual, and test-badge rows are left out.
2. Find the **30-minute window holding the most check-outs**. If two windows tie,
   take the later one, since the end of a Build is the last big group to
   leave.
3. If that window has **fewer than 3** check-outs, there's no real cluster. Use
   the estimated end of the most recent Build on the **same weekday** instead.
   If there isn't one, leave the out time blank (see below).
4. Take the **median** of the check-outs in the window, and **round it to the
   nearest :00 or :30**. That is the Build's estimated end.
5. Everyone still checked in gets an `OUT` row at that time with Note
   `Automatic`. If someone checked in *after* the estimated end, for example a
   late arrival who never scanned out, their out time is left blank, since any
   time would be invented. The Note still says `Automatic`.

How the estimate was made goes in the `builds` tab: how many check-outs were in
the cluster, their median, and whether it fell back to an earlier Build. If an
estimate looks wrong, the coach can see why.

The median ignores a few stragglers: one person leaving at 4:15, or a mentor
staying until 7:00, doesn't move it. The 3-check-out minimum stops a single
early leaver from becoming the end of the Build.

### How it plays out

Checked against a prototype of the rule above. These become unit tests:

| What happens | Estimated end | Result |
| --- | --- | --- |
| Weekday: one person leaves at 4:15, eight leave 5:52–6:10, two forget | **6:00** (8 in cluster, median 6:00) | The two forgetters get 6:00, `Automatic`. The 4:15 leaver is on the left-early list. |
| Saturday: one leaves at 11:00, six leave 2:50–3:08 | **3:00** (6, median 2:59) | The 11:00 leaver is left early. Quiet stretches mid-Build don't matter. |
| A Build that ends on the half hour: five leave 5:24–5:41 | **5:30** (5, median 5:31) | |
| Four leave at 4:30 for a bus, seven leave 5:55–6:07 | **6:00** | The bigger group wins, so the bus group is left early, which is accurate. |
| Five leave 5:40–5:52 | **6:00** (median 5:47) | Rounds up here: it's the nearest half hour, not always the one before. |
| Only two people scan out; everyone else forgets | The last same-weekday Build's end, e.g. Tuesday's 6:00 | `Automatic`, and `builds` says it came from last Tuesday. |
| Nobody scans out, and it's the first Build on that weekday | None | Out times blank, Note `Automatic`. Shows up as missing hours, which is honest. |
| Someone checks out at 4:00 and back in at 4:30, then forgets | 6:00 | First visit `Explicit` 4:00, second visit `Automatic` 6:00. Not left early. |
| Late arrival at 6:20 after a 6:00 end, never scans out | 6:00 | Out time blank, `Automatic`. |
| Pi unplugged at 6:05, booted the next day | Same as if it had stayed on | The old Build is closed at boot, before scans are accepted. Rows written late show that in the Written column. |
| A test badge is scanned before anyone arrives | — | Doesn't start a Build, doesn't count toward the cluster, and is left out of every view. |

The kiosk works this out, not the Sheet. It stamps every row with its Build
and writes the automatic rows itself, so the Sheet's formulas only read
finished data.

## Why there are lines today

[code.py](../code.py) sleeps **15 seconds after every scan**, and if several
badges are in one frame it handles them one at a time, 15 seconds each. That
caps the kiosk at about four people a minute, so 40 people take about 10
minutes. Each scan also waits on a live Google Sheets write, and a Wi-Fi blip
raises an exception that stops the kiosk.

## Design

### The pieces

`code.py` stays the program you run, so the run command doesn't change. The
logic moves out into small files next to it, so the parts that decide who is in
and when a Build ended can be tested on a laptop with no Pi:

| File | Job | Needs the Pi? |
| --- | --- | --- |
| `code.py` | Starts everything: hardware, camera loop, screen, sync thread | yes |
| `attendance.py` *(new)* | Check in/out toggle, 10-minute lockout, one Build per day, closing a Build, the end-of-Build estimate, automatic check-outs, left early. Takes the time as an argument, with no hardware or network imports | no |
| `journal.py` *(new)* | Local SQLite record of every scan on the Pi, plus a background thread that sends rows to the Sheet | no |
| `screen.py` *(new)* | The full-screen window on the monitor | Tk only |
| `setup_sheet.py` *(new)* | Creates the Sheet's tabs, headers, formulas, and protection, so next season's sheet can be rebuilt from git | no |
| `tests/test_attendance.py` *(new)* | The table above, plus double scans and three badges in one frame | no |

Four threads in one process: the camera loop, the Tk window (Tk has to run on
the main thread), the Sheet sync, and short LED and buzzer effects. They share
one `attendance` state object behind a lock.

### Data: an append-only log, with the views as formulas

The kiosk only ever **appends**. It never edits or deletes a row, so a coach
sorting or filtering a tab can't break it, and the log stays a complete record.
That's also why automatic check-outs are new rows rather than edits.

**`scan log`** — new tab, written by the kiosk:

| Column | Example | Notes |
| --- | --- | --- |
| Time | 2026-10-29 15:32:10 | A real date-time value, written with `USER_ENTERED`, so formulas can do math on it. Blank for an automatic check-out with no estimate |
| Badge ID | 1076-A7F3 | The stable key. Names can change in the roster |
| Name | Ana Ruiz | Copied in at scan time, so the log can be read on its own |
| Subteam | Mechanical | |
| Action | `IN` / `OUT` | |
| Note | `Explicit` / `Automatic` / `Manual` | Explicit = scanned at the kiosk. Automatic = written when the Build closed. Manual = a correction typed in by a person, and anyone adding a row by hand should put `Manual` |
| Build | 2026-10-29 | The date, which is the Build's ID |
| Visit | 1076-A7F3 15:32 | Pairs an `IN` with its `OUT` |
| Written | 2026-10-30 15:01:44 | When the row actually reached the Sheet. Shows up for rows that were queued offline and for automatic rows written at boot |

The Note column holds only those three words so it can be filtered and counted.
The detail of *how* an automatic time was estimated lives once per Build in
`builds`.

**`builds`** — one row per Build, written by the kiosk when it closes it:

| Column | Example |
| --- | --- |
| Build | 2026-10-29 |
| First check-in | 15:21 |
| Estimated end | 18:00 |
| How estimated | `cluster` / `same weekday (2026-10-22)` / `none` |
| Check-outs in cluster | 8 |
| Cluster median | 18:00:30 |
| People | 31 |
| Left early | 3 |
| Automatic check-outs | 2 |
| Closed | `after midnight` / `at boot 2026-10-30 15:01` |

**Formula tabs**, made by `setup_sheet.py` and protected so only the owner can
edit them:

- **`here now`** — everyone with an `IN` and no `OUT` in today's Build, sorted
  by name, with a count at the top.
- **`left early`** — for today's Build, everyone who has checked out so far,
  since the end isn't known yet. For each closed Build, people whose last
  explicit check-out was 30+ minutes before its estimated end. One row per
  person per Build, not per visit.
- **`sessions`** — one row per visit: name, subteam, Build, check-in,
  check-out, minutes, **Note** (`Explicit` / `Automatic` / `Manual`, taken from
  the check-out row, or `Still here`), and left early. **This is the coach's
  CSV**: on a laptop, File → Download → CSV with that tab open. Filtering Note
  to `Automatic` and counting by name shows who forgets most often.

The existing `login logs` tab is left alone and renamed `login logs (old)`. The
new sheet has only test rows in it, since the kiosk hasn't logged with badge IDs
yet, so nothing needs migrating.

### The local journal and offline sync

Every scan is written to SQLite on the Pi first, at `~/QR_reader/attendance.db`,
outside the clone (it holds names; `*.db` gets added to `.gitignore` as a
backstop). A background thread sends queued rows with one `append_rows` call
every few seconds:

- A scan never waits on the network, so Wi-Fi going down no longer stops the
  kiosk. Rows queue up and go out when it comes back.
- Batching keeps the kiosk well under Google's 60-writes-a-minute limit, even
  with 30 people arriving in one minute.
- After a restart, the kiosk rebuilds who is in from the journal. If the journal
  is missing, for example on a new SD card, it rebuilds today's state from
  `scan log`.
- The same-weekday fallback reads past Build ends from the journal, or from
  `builds` if the journal is new.

### Throughput (request 6)

- **No more 15-second pause.** Each badge gets its own short ignore window
  (about 3 s) so the same badge in consecutive frames counts once, plus the
  10-minute "Already in" lockout. Other badges are never blocked.
- **Every QR code in a frame is handled.** `pyzbar` already returns all of
  them, so three badges held up together are all logged from one frame.
- **Feedback doesn't block.** The strip flashes for about 1.5 s and drops back
  to idle purple, with a different colour for each result: green in, cyan out,
  amber already, red unknown. Pick these against the real strip. The buzzer
  plays rising for in and falling for out. The LCD shows the latest scan, and
  the monitor shows the last ~10, which is how each of three students sees their
  own confirmation.
- **Camera settings tuned for decoding:** lower resolution and a higher frame
  rate, measured on the Pi 3.
- **Goal:** three different badges logged in under 3 seconds, and 20+ people a
  minute. To test it, `generate_badges.py --test` grows several distinct
  non-logging test badges (`TEST-1` … `TEST-4`), since identical copies of one
  badge would be de-duplicated.

### The kiosk screen (requests 1 and 2)

A full-screen Tk window with no title bar, drawn large enough to read from a few
steps away:

- **Main screen** (always the default): "Scan your badge", the Build's status
  ("Build started 3:21 pm · 23 here"), and a list of recent scans, newest first,
  coloured by result.
- **Here now** button: everyone checked in, by name, with subteam and check-in
  time. One click.
- **Left** button: today, everyone who has checked out, with the time and how
  long they stayed. Below that, the last closed Build's left-early list.
- **Last Build** button: first check-in, estimated end and how it was
  estimated, headcount, left early, and the automatic check-outs.
- With no clicks for 60 seconds, it goes back to the main screen.

With a keyboard left on the kiosk, the `q` quit is now a problem: any student
could stop it. The `keyboard` library and the `q` check go away. Quitting moves
to Ctrl+Shift+Q plus a confirm button, and Tk handles keys itself.

### Smaller changes that come along

- **Roster refresh:** reload the roster every 10 minutes, and once on an unknown
  badge (rate limited) before showing "Unauthorized". A newly minted badge then
  works without a restart, which fixes a known issue.
- **Clock check:** a Pi 3 has no clock battery. At startup, wait until the clock
  has synced (`timedatectl show -p NTPSynchronized`) before accepting scans, and
  show "Waiting for clock" until then. Otherwise check-in times could be wrong
  without anyone noticing, and a wrong date would also put scans in the wrong
  Build.
- **Test badges:** they never start a Build, never count toward the end
  estimate, and their rows carry Build `TEST` so the views skip them.

## Steps

Each step ends with something that can be checked.

**0. Get today's code running on the Pi, and test the risky parts.** The Pi
still runs its own older code, so finish the move in
[pi-setup.md](pi-setup.md) first. Then, on the Pi itself:
   - Open a full-screen Tk window **under `sudo -E`**. The LED strip needs root,
     and Raspberry Pi OS may be running Wayland, where a GUI started as root can
     fail to reach the display. This is the biggest unknown, and if it fails
     the screen design changes: the LEDs would move to a small helper process.
   - Hold up three badges at once, and measure decode rate and CPU with a Tk
     window open.
   - Check the clock-sync command works.

**1. `attendance.py` and its tests.** Pure logic, written and tested on a laptop
with `pytest`, covering every row of the table plus the double scan, the
10-minute lockout, three badges in one frame, and rebuilding state after a
restart. The end-of-Build estimate is its own function, `estimate_end(checkouts,
earlier_builds)`, so its window, minimum, and rounding can be tuned without
touching the rest. *Done when* all of it passes.

**2. Journal and Sheet sync.** `journal.py` and `setup_sheet.py`. Build the tabs
in a **copy** of the sheet first, feed it a fake week of scans from a script,
and check every formula tab by hand, including from a phone. *Done when* the
formula tabs match what `attendance.py` says for the same scans.

**3. Fast scanning in `code.py`.** Remove the 15-second pause, handle multiple
QR codes per frame, add non-blocking feedback and the new test badges. *Done
when* three test badges log in under 3 seconds with Wi-Fi unplugged, and the
rows reach the Sheet once it's plugged back in.

**4. The screen.** `screen.py`, with the main screen and the three views, the
idle timeout, and the quit shortcut. *Done when* a coach who hasn't seen it
can find who's here without help.

**5. Phone and docs.** Share the sheet with the head coach as a **Viewer**, or
Editor if they'll fix records by hand with the `Manual` note. Write a short "on
your phone" note: open the Sheets app, star the sheet, swipe to the `here now`
tab. Update the [README](../README.md) (how it works, sheet layout, known
issues), [Use instructions](../Use%20instructions) (keyboard stays, `q` no
longer quits, how to read the screen), and [pi-setup.md](pi-setup.md)
(`python3-tk`).

**6. Trial at real Builds.** Run it alongside the current sign-in for two Builds.
Time the line at the start, compare the `sessions` tab against what actually
happened, and write down when each Build really ended so it can be checked
against the estimate. Get the coach's notes before switching over fully.

## Not in this plan, but next in line

- **Check someone in or out from the screen**, for a forgotten badge or a
  correction, written with Note `Manual`. The coach didn't ask for it, but it
  will come up. For now, corrections are a row added to `scan log` by hand.
- **Start on power-up** (systemd or desktop autostart). Less pressing now that
  the monitor and keyboard stay on the kiosk, but it's already on the
  next-steps list.
- **A phone-friendly web page** (Apps Script, limited to school accounts) if the
  Sheets app turns out to be too clumsy.
- **Students only:** mentors and coaches are on the roster and get tracked too.
  Their subteam column makes them easy to spot, and the views can filter them
  out later if the coach wants.

## Defaults to confirm with the coach

Each of these is one constant, easy to change later:

- **One Build per day.** A day with two separate sessions, such as Saturday
  morning and an evening event, is treated as one Build, and its end is the
  bigger check-out cluster.
- **The cluster rule:** a 30-minute window, at least 3 check-outs, and the
  biggest group wins, with ties going to the later one.
- **With no cluster, fall back to the same weekday's last end.** The
  alternative is always leaving the time blank.
- **Late arrivals after the estimated end get a blank out time**, not 0 minutes.
- The 10-minute "Already in" lockout, applied after check-out as well.
- Left early measured per person per Build, by their last explicit check-out.
- LED colours for out and "already", once seen on the real strip next to idle
  purple.

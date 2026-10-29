#!/usr/bin/env python3
"""Generate printable QR attendance badges from the team roster.

Each badge encodes an opaque ID such as ``1076-A7F3`` -- never a name -- so the
QR payload carries no student data. The kiosk resolves the ID back to a name at
scan time from the same roster sheet.

The roster worksheet is expected to have four columns:

    A: Name        B: Title/subteam        C: Badge ID        D: Role

Column C is filled in by this script. Rows that already have an ID keep it, so
badges printed in an earlier season stay valid. Column D is free text, printed
as typed under the name; a blank D prints nothing. Column B may be blank.

Output lands in badges/, which is gitignored: one PNG per person, _roster.csv,
and badges.pdf -- fold-over badges laid out on US Letter for single-sided
printing on cardstock. Cut each strip out on the crop marks and fold it on the
dashed line: the front shows the name and role, the back the QR code. All of it
carries names, which makes it student data -- it stays local and is never
committed.

Each run also compares against the _roster.csv the previous run left behind and
writes changed_badges.pdf with only the new people and anyone whose name or role
now prints differently -- the badges to hand out after a roster update. Print it
before running again: the next run compares against this one.

--from-csv re-lays out badges.pdf from badges/_roster.csv with no sheet access,
for reprinting or after a layout change. --sample lays out made-up people, for
checking the layout without touching real data.

--test writes the test badges into test_badges/ instead. They hold no student
data, need no sheet access, and are committed so anyone can check the kiosk.

Usage:
    python3 generate_badges.py              # mint missing IDs, write PNGs + PDFs
    python3 generate_badges.py --dry-run    # report what would change
    python3 generate_badges.py --creds KEY  # use a key file other than the Pi's
    python3 generate_badges.py --from-csv   # rebuild badges.pdf from _roster.csv
    python3 generate_badges.py --sample     # badges/sample_badges.pdf, no sheet
    python3 generate_badges.py --test       # rewrite test_badges/
"""

import argparse
import csv
import re
import secrets
import sys
from itertools import combinations
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

CREDS_PATH = "/home/pihirobotics/QR_reader/service_account.json"
# From the sheet's URL, between /d/ and /edit. Must match code.py.
SPREADSHEET_ID = "16D6Pkm7vp8U_9SqY9FmqPHRO8bcyeU0PoaMDQ_4Jv_Y"
ROSTER_WORKSHEET = "master list of names"

# Writing badge IDs back to column C needs the read/write spreadsheets scope.
# Opening by ID means no Drive scope is needed.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# 1-indexed to match gspread's update_cell.
COL_NAME = 1
COL_SUBTEAM = 2
COL_ID = 3
COL_ROLE = 4

ID_PREFIX = "1076"
# Crockford-style alphabet: no 0/1/I/L/O/U, so IDs are easy to read aloud and
# hard to transcribe wrong when someone is troubleshooting a bad badge.
ID_ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"
ID_LENGTH = 4

# (badge ID, filename, what the kiosk should do). TEST-OK and TEST-LOG must
# match TEST_BADGES in code.py. TEST-REJECT is in neither on purpose -- it takes
# the reject path like any unknown ID. None of these can collide with a minted
# ID, which always starts with ID_PREFIX.
TEST_BADGES = [
    ("TEST-OK", "1_accept", "green · not logged"),
    ("TEST-LOG", "2_accept_and_log", "green · logs a row"),
    ("TEST-REJECT", "3_reject", "red · Unauthorized"),
]
TEST_DIR = "test_badges"

# Made-up people for --sample: the short, long, hyphenated, and accented names
# the auto-shrink has to handle, and a role long enough to shrink too. The kiosk
# rejects the IDs.
SAMPLE_BADGES = [
    ("SAMPLE-01", "Avery Example", "Student"),
    ("SAMPLE-02", "Li Wu", "Mechanical Lead"),
    ("SAMPLE-03", "Bartholomew Montgomery-Fitzgerald", ""),
    ("SAMPLE-04", "José Ñúñez", "Mentor"),
    ("SAMPLE-05", "Sam Placeholder", "Faculty Mentor"),
    ("SAMPLE-06", "Alexandria Konstantinopoulou-Vanderbilt",
     "Chief Technical Director and Engineering Captain"),
]

# Fold-over badge sheet. Sizes are in inches. Each badge prints as one strip --
# front and back panels end to end -- so single-sided printing gives a
# two-sided badge.
BADGE_W = 3.5  # finished badge
BADGE_H = 2.25
PAGE_W = 8.5  # US Letter
PAGE_H = 11.0
# "top": panels stacked, folded along the badge's top edge, back printed upside
# down so it reads upright once folded. "side": panels side by side, folded
# like a greeting card. A 3.5x2.25 badge fits three to a page folded on the side
# but only one folded on the top.
FOLD_EDGE = "side"
CROP_GAP = 1 / 8  # crop marks start this far outside the cut line
CROP_LEN = 1 / 4
PAGE_MARGIN = 0.25  # most printers can't reach the last quarter inch
TOP_MARGIN = 0.1  # no ink closer than this to the badge's top edge

# Front panel, after last year's design: the name in bold caps at top left,
# the role in smaller regular caps right under it, all black on white for a
# black-and-white printer. The role's baseline marks off the sticker area --
# the bottom STICKER_ZONE of the front stays blank for skill-badge stickers.
STICKER_ZONE = 2 / 3
TEXT_X = 0.2  # left edge of the name and role
ROLE_PT = 15
NAME_MAX_PT = 30
NAME_MIN_PT = 12  # smaller than this and it warns
NAME_MAX_LINES = 3
NAME_LINE_SPACING = 1.1
NAME_GAP = 0.12  # between the top of the role's caps and the name's baseline
# Height of an all-caps line above its baseline, as a fraction of the point
# size: cap height plus room for accents such as the one on É, which sit high
# in Lexend.
CAPS_TOP = 0.96

# Lexend is the team font. It ships in fonts/ (SIL Open Font License, see
# fonts/OFL.txt) so badges look the same on any machine; the system fonts after
# it are fallbacks in case fonts/ goes missing.
FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONT_CANDIDATES = [
    str(FONT_DIR / "Lexend-Bold.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]
# Regular weight, for the role on the PDF badge.
FONT_REGULAR_CANDIDATES = [
    str(FONT_DIR / "Lexend-Regular.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]

_font_cache = {}


def load_font(size):
    if size not in _font_cache:
        for path in FONT_CANDIDATES:
            if Path(path).exists():
                _font_cache[size] = ImageFont.truetype(path, size)
                break
        else:
            _font_cache[size] = ImageFont.load_default()
    return _font_cache[size]


def mint_id(taken):
    """Return a badge ID not already in `taken`."""
    while True:
        suffix = "".join(secrets.choice(ID_ALPHABET) for _ in range(ID_LENGTH))
        badge_id = f"{ID_PREFIX}-{suffix}"
        if badge_id not in taken:
            taken.add(badge_id)
            return badge_id


def safe_filename(name):
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return slug or "unnamed"


def make_badge(badge_id, name, subteam, out_dir, filename=None):
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(badge_id)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    lines = [(name, 22), (subteam, 17), (badge_id, 15)]
    caption_h = sum(size + 6 for text, size in lines if text) + 8
    canvas = Image.new("RGB", (qr_img.width, qr_img.height + caption_h), "white")
    canvas.paste(qr_img, (0, 0))

    draw = ImageDraw.Draw(canvas)
    y = qr_img.height + 4
    for text, size in lines:
        if not text:
            continue
        font = load_font(size)
        width = draw.textlength(text, font=font)
        draw.text(((canvas.width - width) / 2, y), text, fill="black", font=font)
        y += size + 6

    path = out_dir / (filename or f"{safe_filename(name)}_{badge_id}.png")
    canvas.save(path)
    return path


def make_test_badges(out_dir):
    """Write each test badge, plus all of them on one page for printing."""
    out_dir.mkdir(exist_ok=True)
    paths = [
        make_badge(badge_id, "TEST BADGE", expect, out_dir, f"{stem}.png")
        for badge_id, stem, expect in TEST_BADGES
    ]
    badges = [Image.open(path) for path in paths]

    margin, gap, title_h = 40, 40, 70
    width = 2 * margin + sum(b.width for b in badges) + gap * (len(badges) - 1)
    height = 2 * margin + title_h + max(b.height for b in badges)
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((margin, margin), "Attendance kiosk test badges", fill="black",
              font=load_font(24))
    draw.text((margin, margin + 34), "Cut apart before scanning -- the kiosk "
              "reads every code in view.", fill="black", font=load_font(15))

    x = margin
    for badge in badges:
        sheet.paste(badge, (x, margin + title_h))
        x += badge.width + gap
    sheet.save(out_dir / "all_test_badges.png")
    return paths


def pdf_fonts():
    """Register the first available TTFs for the PDF; fall back to Helvetica.

    Returns (bold, regular) font names.
    """
    fonts = []
    for name, candidates, fallback in (
        ("BadgeBold", FONT_CANDIDATES, "Helvetica-Bold"),
        ("BadgeRegular", FONT_REGULAR_CANDIDATES, "Helvetica"),
    ):
        for path in candidates:
            if Path(path).exists():
                if name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(name, path))
                fonts.append(name)
                break
        else:
            fonts.append(fallback)
    return tuple(fonts)


def fit_size(lines, font, max_w, max_h, max_pt):
    """Largest point size, at most max_pt, at which all-caps `lines` fit the box."""
    widest = max(pdfmetrics.stringWidth(line, font, 1) for line in lines)
    by_width = max_w / widest
    by_height = max_h / (CAPS_TOP + (len(lines) - 1) * NAME_LINE_SPACING)
    return min(max_pt, by_width, by_height)


def layout_name(name, font, max_w, max_h):
    """Return (lines, size): the name on up to NAME_MAX_LINES lines, whichever
    split prints it largest.

    Lines break at a space or after a hyphen. Ties go to fewer lines.
    """
    cuts = [i + 1 if ch == "-" else i
            for i, ch in enumerate(name) if ch in " -" and 0 < i < len(name) - 1]
    best = None
    for count in range(NAME_MAX_LINES):
        for chosen in combinations(cuts, count):
            bounds = [0, *chosen, len(name)]
            lines = [name[a:b].strip() for a, b in zip(bounds, bounds[1:])]
            size = fit_size(lines, font, max_w, max_h, NAME_MAX_PT)
            if best is None or size > best[1]:
                best = (lines, size)
    return best


def draw_centered(c, text, font, size, cx, cy):
    """Draw one line of text centred on (cx, cy), ascender to descender."""
    ascent, descent = pdfmetrics.getAscentDescent(font, size)
    c.setFont(font, size)
    c.drawCentredString(cx, cy - (ascent + descent) / 2, text)


def draw_front(c, name, role, fonts):
    """Front panel in local inches-as-points coordinates, origin bottom-left.

    `fonts` is (bold, regular).
    """
    bold, regular = fonts
    w, h = BADGE_W * inch, BADGE_H * inch
    x = TEXT_X * inch
    # Everything below h * STICKER_ZONE stays blank. The role sits a point above
    # it, because round letters such as O and S dip just under the baseline.
    role_y = h * STICKER_ZONE + 1
    max_w = w - x - 0.15 * inch
    # Column D is free text, so a long role shrinks to stay on one line. A
    # blank role prints nothing, and the name stays where it would be anyway.
    role = role.upper()
    role_pt = min(ROLE_PT, ROLE_PT * max_w
                  / max(pdfmetrics.stringWidth(role, regular, ROLE_PT), 1))
    c.setFillColor("#000000")
    c.setFont(regular, role_pt)
    c.drawString(x, role_y, role)

    # The name sits above the role, bottom line first, and may grow up to the
    # top margin.
    cap_h = pdfmetrics.getFont(regular).face.capHeight / 1000 * ROLE_PT
    baseline = role_y + cap_h + NAME_GAP * inch
    # Collapse stray double spaces from pasted rosters.
    name = " ".join(name.split())
    lines, size = layout_name(name.upper(), bold, max_w,
                              h - TOP_MARGIN * inch - baseline)
    if size < NAME_MIN_PT:
        print(f"  warning: {name!r} only fits at {size:.1f}pt")
    c.setFont(bold, size)
    for n, line in enumerate(reversed(lines)):
        c.drawString(x, baseline + n * size * NAME_LINE_SPACING, line)


def draw_back(c, badge_id, font):
    """Back panel: QR code with its quiet zone, and the ID under or beside it.

    Whichever arrangement gives the bigger code wins: under suits a tall badge,
    beside a wide one.
    """
    w, h = BADGE_W * inch, BADGE_H * inch
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4)
    qr.add_data(badge_id)
    qr.make(fit=True)
    matrix = qr.get_matrix()  # includes the 4-module quiet zone
    n = len(matrix)

    id_size = 16
    id_w = pdfmetrics.stringWidth(badge_id, font, id_size)
    margin = 0.05 * inch
    # The top quiet zone may run into the clear strip; the dark modules may not.
    # side * (n - 4) / n is the code's height without that top quiet zone.
    clear_top = h - TOP_MARGIN * inch
    under = min(w - 2 * margin,
                h - 2 * margin - id_size,
                (clear_top - margin - id_size) * n / (n - 4))
    beside = min(w - 2 * margin - id_w,
                 h - 2 * margin,
                 (clear_top - margin) * n / (n - 4))

    if under >= beside:
        side = under
        x0 = (w - side) / 2
        y0 = min((h - side + id_size) / 2, clear_top - side * (n - 4) / n)
        id_x, id_y = w / 2, y0 - id_size / 2
    else:
        side = beside
        x0 = (w - side - id_w) / 2
        y0 = min((h - side) / 2, clear_top - side * (n - 4) / n)
        id_x, id_y = x0 + side + id_w / 2, y0 + side / 2
    module = side / n
    qr_top = y0 + side

    c.setFillColor("#000000")
    for r, row in enumerate(matrix):
        y = qr_top - (r + 1) * module
        col = 0
        while col < len(row):
            if not row[col]:
                col += 1
                continue
            run = col
            while run < len(row) and row[run]:
                run += 1
            # Overlap each run slightly so viewers don't show hairline seams.
            c.rect(x0 + col * module, y - 0.1, (run - col) * module, module + 0.2,
                   stroke=0, fill=1)
            col = run
    draw_centered(c, badge_id, font, id_size, id_x, id_y)


def draw_marks(c, x0, y0, x1, y1, fold):
    """Crop marks outside each corner of the strip, and ticks at the fold."""
    gap, length = CROP_GAP * inch, CROP_LEN * inch
    c.setStrokeColor("#000000")
    c.setLineWidth(0.5)
    c.setDash()
    for x, dx in ((x0, -1), (x1, 1)):
        for y, dy in ((y0, -1), (y1, 1)):
            c.line(x + dx * gap, y, x + dx * (gap + length), y)
            c.line(x, y + dy * gap, x, y + dy * (gap + length))
    if FOLD_EDGE == "top":
        for x, dx in ((x0, -1), (x1, 1)):
            c.line(x + dx * gap, fold, x + dx * (gap + length), fold)
    else:
        for y, dy in ((y0, -1), (y1, 1)):
            c.line(fold, y + dy * gap, fold, y + dy * (gap + length))


def write_badge_pdf(entries, path):
    """Lay out [(badge_id, name, role)] as fold-over strips on US Letter.

    Returns the number of pages.
    """
    fonts = pdf_fonts()
    font = fonts[0]
    w, h = BADGE_W * inch, BADGE_H * inch
    if FOLD_EDGE == "top":
        strip_w, strip_h = w, 2 * h
    else:
        strip_w, strip_h = 2 * w, h

    # Each strip needs room for its crop marks; neighbours don't share them.
    mark = (CROP_GAP + CROP_LEN) * inch
    cell_w, cell_h = strip_w + 2 * mark, strip_h + 2 * mark
    usable_w = (PAGE_W - 2 * PAGE_MARGIN) * inch
    footer = (PAGE_MARGIN + 0.3) * inch
    usable_h = PAGE_H * inch - PAGE_MARGIN * inch - footer
    cols, rows = int(usable_w // cell_w), int(usable_h // cell_h)
    if not cols or not rows:
        sys.exit(f"A {BADGE_W}x{BADGE_H} in badge folded on the {FOLD_EDGE} "
                 f"edge doesn't fit on a {PAGE_W}x{PAGE_H} in page.")
    per_page = cols * rows
    # Spread the spare room between the strips too, so neighbouring crop marks
    # don't run together into one line.
    col_gap = (PAGE_W * inch - cols * cell_w) / (cols + 1)
    row_gap = (PAGE_H * inch - footer - rows * cell_h) / (rows + 1)

    c = canvas.Canvas(str(path), pagesize=(PAGE_W * inch, PAGE_H * inch))
    c.setTitle("Attendance badges")
    pages = 0
    for start in range(0, len(entries), per_page):
        pages += 1
        for slot, (badge_id, name, role) in enumerate(entries[start:start + per_page]):
            col, row = slot % cols, slot // cols
            x0 = col_gap + col * (cell_w + col_gap) + mark
            y0 = PAGE_H * inch - (row + 1) * (cell_h + row_gap) + mark
            x1, y1 = x0 + strip_w, y0 + strip_h

            c.saveState()
            if FOLD_EDGE == "top":
                fold = y0 + h
                c.translate(x0, y0)
                draw_front(c, name, role, fonts)
                c.restoreState()
                c.saveState()
                c.translate(x1, y1)
                c.rotate(180)
                draw_back(c, badge_id, font)
            else:
                fold = x0 + w
                c.translate(x0, y0)
                draw_front(c, name, role, fonts)
                c.restoreState()
                c.saveState()
                c.translate(fold, y0)
                draw_back(c, badge_id, font)
            c.restoreState()

            c.setStrokeColor("#888888")
            c.setLineWidth(0.5)
            c.setDash(4, 3)
            if FOLD_EDGE == "top":
                c.line(x0, fold, x1, fold)
            else:
                c.line(fold, y0, fold, y1)
            draw_marks(c, x0, y0, x1, y1, fold)

        # Footer, with a 1 in bar to check the printer didn't scale the page.
        c.setDash()
        c.setFillColor("#000000")
        c.setFont(font, 8)
        foot_y = PAGE_MARGIN * inch + 4
        c.drawString(PAGE_MARGIN * inch + 1.1 * inch, foot_y,
                     "Print at 100% / Actual size. Cut on the crop marks, fold on "
                     "the dashed line. The bar should measure 1 inch.")
        c.rect(PAGE_MARGIN * inch, foot_y, inch, 4, stroke=0, fill=1)
        c.showPage()
    c.save()
    return pages


def tidy_roles(entries, label):
    """Collapse stray spaces from a pasted roster in each entry's role.

    `entries` is [(badge_id, name, role)]. Roles are free text, so nothing is
    rejected, and a blank role leaves that line of the badge empty.
    """
    tidied, blank = [], 0
    for badge_id, name, role in entries:
        role = " ".join(role.split())
        blank += not role
        tidied.append((badge_id, name, role))
    if blank:
        print(f"  {blank} with no role in {label} -- their badges show just the name.")
    return tidied


def read_roster(worksheet):
    """Return [(row_number, name, subteam, badge_id, role)] for every populated row."""
    rows = worksheet.get_all_values()
    if rows and rows[0] and rows[0][0].strip().lower() in ("name", "names"):
        start = 2
        rows = rows[1:]
    else:
        start = 1

    roster = []
    for offset, row in enumerate(rows):
        row = list(row) + [""] * (4 - len(row))
        name = row[COL_NAME - 1].strip()
        subteam = row[COL_SUBTEAM - 1].strip()
        badge_id = row[COL_ID - 1].strip().upper()
        role = row[COL_ROLE - 1].strip()
        if name:
            roster.append((start + offset, name, subteam, badge_id, role))
    return roster


def read_roster_csv(path):
    """Return [(badge_id, name, role)] from a _roster.csv written by this script."""
    with open(path, newline="") as handle:
        return [
            (row["badge_id"].strip(), row["name"].strip(), (row.get("role") or "").strip())
            for row in csv.DictReader(handle)
            if row.get("badge_id") and row.get("name")
        ]


def changed_badges(entries, previous):
    """Return the entries whose printed badge differs from the last run.

    `entries` is [(badge_id, name, role)]; `previous` maps badge_id to
    (name, role) from that run's _roster.csv. A badge counts as changed if its
    ID is new or its name or role would print differently. Case and spacing
    alone don't count, since the front prints both in caps with single spaces.
    """
    def front(name, role):
        return " ".join(name.split()).upper(), " ".join(role.split()).upper()

    return [
        (badge_id, name, role)
        for badge_id, name, role in entries
        if badge_id not in previous or front(*previous[badge_id]) != front(name, role)
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="badges", help="output directory")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would change without writing IDs or PNGs",
    )
    parser.add_argument(
        "--creds",
        default=CREDS_PATH,
        help="service-account key file (default: the Pi's copy, %(default)s)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--from-csv",
        nargs="?",
        const="",
        metavar="CSV",
        help="rebuild badges.pdf from a roster CSV (default: OUT/_roster.csv); "
        "no sheet access",
    )
    mode.add_argument(
        "--sample",
        action="store_true",
        help="lay out made-up people in OUT/sample_badges.pdf; no sheet access",
    )
    mode.add_argument(
        "--test",
        action="store_true",
        help=f"write the test badges into {TEST_DIR}/ and exit; no sheet access",
    )
    args = parser.parse_args()
    out_dir = Path(args.out)

    if args.test:
        paths = make_test_badges(Path(TEST_DIR))
        print(f"Wrote {len(paths)} test badges and all_test_badges.png to {TEST_DIR}/.")
        return

    if args.sample:
        out_dir.mkdir(exist_ok=True)
        path = out_dir / "sample_badges.pdf"
        pages = write_badge_pdf(tidy_roles(SAMPLE_BADGES, "the samples"), path)
        print(f"Wrote {len(SAMPLE_BADGES)} sample badges on {pages} pages to {path}.")
        return

    if args.from_csv is not None:
        csv_path = Path(args.from_csv) if args.from_csv else out_dir / "_roster.csv"
        if not csv_path.exists():
            sys.exit(f"No roster CSV at {csv_path} -- run once with sheet access first.")
        entries = tidy_roles(read_roster_csv(csv_path), csv_path)
        out_dir.mkdir(exist_ok=True)
        pages = write_badge_pdf(entries, out_dir / "badges.pdf")
        print(f"Wrote {len(entries)} badges on {pages} pages to {out_dir}/badges.pdf "
              "(local only -- do not commit).")
        return

    if not Path(args.creds).exists():
        sys.exit(f"No key file at {args.creds} -- pass --creds PATH, or use "
                 "--from-csv to re-lay out badges without the sheet.")

    # Imported here so the modes above work on a machine without the Sheets
    # libraries.
    import gspread
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_file(args.creds, scopes=SCOPES)
    client = gspread.authorize(creds)
    worksheet = client.open_by_key(SPREADSHEET_ID).worksheet(ROSTER_WORKSHEET)

    roster = read_roster(worksheet)
    if not roster:
        sys.exit(f"No names found in '{ROSTER_WORKSHEET}' column A.")

    existing = [entry for entry in roster if entry[3]]
    taken = {entry[3] for entry in existing}
    if len(taken) != len(existing):
        sys.exit("Duplicate badge IDs in column C -- resolve them before running.")

    roles = tidy_roles([(e[3], e[1], e[4]) for e in roster], "column D")
    role_by_row = {e[0]: role for e, (_, _, role) in zip(roster, roles)}

    missing = [entry for entry in roster if not entry[3]]
    print(f"{len(roster)} people, {len(existing)} with IDs, {len(missing)} to mint.")

    # The last run's _roster.csv says what's already printed, so
    # changed_badges.pdf can hold just the new and changed badges. Read it
    # before this run overwrites it.
    roster_csv = out_dir / "_roster.csv"
    previous = None
    if roster_csv.exists():
        previous = {badge_id: (name, role)
                    for badge_id, name, role in read_roster_csv(roster_csv)}

    if args.dry_run:
        for _, name, _, _, _ in missing:
            print(f"  would mint an ID for {name}")
        if previous is not None:
            changed = changed_badges(
                [(e[3], e[1], role_by_row[e[0]]) for e in existing], previous)
            for badge_id, name, _ in changed:
                reason = ("name or role changed" if badge_id in previous
                          else "not in the last run")
                print(f"  would reprint {name} ({reason})")
            print(f"Would put {len(missing) + len(changed)} new or changed badges "
                  "in changed_badges.pdf.")
        print(f"Would write {len(roster)} badges and badges.pdf to {args.out}/.")
        return

    minted = []
    for row_number, name, subteam, _, role in missing:
        badge_id = mint_id(taken)
        worksheet.update_cell(row_number, COL_ID, badge_id)
        minted.append((row_number, name, subteam, badge_id, role))
        print(f"  minted {badge_id} for {name}")

    out_dir.mkdir(exist_ok=True)

    final = [entry for entry in roster if entry[3]] + minted
    for _, name, subteam, badge_id, _ in final:
        make_badge(badge_id, name, subteam, out_dir)

    with open(roster_csv, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["badge_id", "name", "subteam", "role"])
        for row_number, name, subteam, badge_id, _ in final:
            writer.writerow([badge_id, name, subteam, role_by_row[row_number]])

    entries = [(badge_id, name, role_by_row[row])
               for row, name, _, badge_id, _ in final]
    pages = write_badge_pdf(entries, out_dir / "badges.pdf")
    print(f"Wrote {len(final)} badges and badges.pdf ({pages} pages) to {out_dir}/ "
          "(local only -- do not commit).")

    # Remove the last batch first, so an old changed_badges.pdf is never
    # mistaken for this run's.
    changed_path = out_dir / "changed_badges.pdf"
    changed_path.unlink(missing_ok=True)
    if previous is None:
        print("No earlier _roster.csv to compare with, so no changed_badges.pdf -- "
              "print badges.pdf.")
        return
    changed = changed_badges(entries, previous)
    if changed:
        pages = write_badge_pdf(changed, changed_path)
        print(f"Wrote {len(changed)} new or changed badges to changed_badges.pdf "
              f"({pages} page{'s' if pages != 1 else ''}).")
    else:
        print("No new or changed badges since the last run, so no changed_badges.pdf.")


if __name__ == "__main__":
    main()

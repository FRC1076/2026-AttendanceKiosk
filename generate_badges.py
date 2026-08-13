#!/usr/bin/env python3
"""Generate printable QR attendance badges from the team roster.

Each badge encodes an opaque ID such as ``1076-A7F3`` -- never a name -- so the
QR payload carries no student data. The kiosk resolves the ID back to a name at
scan time from the same roster sheet.

The roster worksheet is expected to have three columns:

    A: Name        B: Title/subteam        C: Badge ID

Column C is filled in by this script. Rows that already have an ID keep it, so
badges printed in an earlier season stay valid.

Output lands in badges/, which is gitignored. The PNGs are captioned with the
person's name so they can be handed out, which makes them student data -- they
stay local and are never committed.

Usage:
    python3 generate_badges.py            # mint missing IDs, write PNGs
    python3 generate_badges.py --dry-run  # report what would change
"""

import argparse
import csv
import re
import secrets
import sys
from pathlib import Path

import gspread
import qrcode
from google.oauth2.service_account import Credentials
from PIL import Image, ImageDraw, ImageFont

CREDS_PATH = "/home/pihirobotics/QR_reader/service_account.json"
SPREADSHEET = "PiHi samurai NEW attendance sheet QR test 61"
ROSTER_WORKSHEET = "master list of names"

# Writing badge IDs back to column C needs the read/write spreadsheets scope.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# 1-indexed to match gspread's update_cell.
COL_NAME = 1
COL_SUBTEAM = 2
COL_ID = 3

ID_PREFIX = "1076"
# Crockford-style alphabet: no 0/1/I/L/O/U, so IDs are easy to read aloud and
# hard to transcribe wrong when someone is troubleshooting a bad badge.
ID_ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"
ID_LENGTH = 4

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
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


def make_badge(badge_id, name, subteam, out_dir):
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

    path = out_dir / f"{safe_filename(name)}_{badge_id}.png"
    canvas.save(path)
    return path


def read_roster(worksheet):
    """Return [(row_number, name, subteam, badge_id)] for every populated row."""
    rows = worksheet.get_all_values()
    if rows and rows[0] and rows[0][0].strip().lower() in ("name", "names"):
        start = 2
        rows = rows[1:]
    else:
        start = 1

    roster = []
    for offset, row in enumerate(rows):
        row = list(row) + [""] * (3 - len(row))
        name = row[COL_NAME - 1].strip()
        subteam = row[COL_SUBTEAM - 1].strip()
        badge_id = row[COL_ID - 1].strip().upper()
        if name:
            roster.append((start + offset, name, subteam, badge_id))
    return roster


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="badges", help="output directory")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would change without writing IDs or PNGs",
    )
    args = parser.parse_args()

    creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
    client = gspread.authorize(creds)
    worksheet = client.open(SPREADSHEET).worksheet(ROSTER_WORKSHEET)

    roster = read_roster(worksheet)
    if not roster:
        sys.exit(f"No names found in '{ROSTER_WORKSHEET}' column A.")

    existing = [entry for entry in roster if entry[3]]
    taken = {entry[3] for entry in existing}
    if len(taken) != len(existing):
        sys.exit("Duplicate badge IDs in column C -- resolve them before running.")

    missing = [entry for entry in roster if not entry[3]]
    print(f"{len(roster)} people, {len(existing)} with IDs, {len(missing)} to mint.")

    if args.dry_run:
        for _, name, _, _ in missing:
            print(f"  would mint an ID for {name}")
        print(f"Would write {len(roster)} badges to {args.out}/.")
        return

    minted = []
    for row_number, name, subteam, _ in missing:
        badge_id = mint_id(taken)
        worksheet.update_cell(row_number, COL_ID, badge_id)
        minted.append((row_number, name, subteam, badge_id))
        print(f"  minted {badge_id} for {name}")

    out_dir = Path(args.out)
    out_dir.mkdir(exist_ok=True)

    final = [entry for entry in roster if entry[3]] + minted
    for _, name, subteam, badge_id in final:
        make_badge(badge_id, name, subteam, out_dir)

    with open(out_dir / "_roster.csv", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["badge_id", "name", "subteam"])
        for _, name, subteam, badge_id in final:
            writer.writerow([badge_id, name, subteam])

    print(f"Wrote {len(final)} badges to {out_dir}/ (local only -- do not commit).")


if __name__ == "__main__":
    main()

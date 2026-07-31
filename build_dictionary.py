# -*- coding: utf-8 -*-
"""Generate dictionary.json (and the app icons) for the bref dictionary PWA.

bref is a strict bijection — every brief expands to exactly one English word or
phrase — so the data file stores each pair once and the app derives both search
directions at load time. That keeps the offline cache small.

Run:  python3 build_dictionary.py
"""

import json
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "source")

REDDIT = "https://www.reddit.com/r/shorthand/comments/esjhdk/bref_shorthand/"
DRIVE = ("https://drive.google.com/drive/folders/"
         "1PZcAYhusYGpaLHwMUBAdZURA25lKk2Mu?usp=sharing")


# --------------------------------------------------------------------------- #
# Dictionary
# --------------------------------------------------------------------------- #

def pairs(path, english_first):
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or "=" not in line:
                continue
            left, right = (x.strip() for x in line.split("=", 1))
            if not left or not right:
                continue
            out.append((left, right) if english_first else (right, left))
    return out


words = dict(pairs(os.path.join(SRC, "11661 WORDS FORWARD.txt"), True))
rev = dict(pairs(os.path.join(SRC, "11661 WORDS REVERSED.txt"), False))
# The phrase lists use the opposite column order from the word lists.
phrases = dict(pairs(os.path.join(SRC, "3041 PHRASESREV.txt"), True))

words["exam"] = "xm"                     # source typo: "exam = xmexam = xm"
words["government"] = rev["government"]  # FORWARD gvr vs REVERSED gvt

disagree = {k for k in words if k in rev and words[k] != rev[k]} - {"exam"}
if disagree:
    print(f"  ! forward/reversed disagree on: {sorted(disagree)}")

# bref's defining property: no brief may expand to two different things.
seen = {}
collisions = 0
for kind, table in (("word", words), ("phrase", phrases)):
    for eng, brf in table.items():
        if brf in seen:
            print(f"  ! collision {brf!r}: {seen[brf]} vs {kind} {eng!r}")
            collisions += 1
        seen[brf] = f"{kind} {eng!r}"
print(f"{len(words)} words, {len(phrases)} phrases, "
      f"{len(seen)} unique briefs, {collisions} collisions")

data = {
    "source": "bref shorthand by Donald M. Volk (draft #1, 22 January 2020)",
    "source_url": REDDIT,
    "materials_url": DRIVE,
    "note": ("Every brief expands to exactly one English word or phrase, so each "
             "pair is stored once and both search directions are derived at load "
             "time. Where the manual's prose and the dictionary files disagree, "
             "the dictionary files are used."),
    "counts": {"words": len(words), "phrases": len(phrases)},
    "words": sorted(([e, b] for e, b in words.items()), key=lambda p: p[0].lower()),
    "phrases": sorted(([e, b] for e, b in phrases.items()),
                      key=lambda p: p[0].lower()),
}

out = os.path.join(HERE, "dictionary.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
print(f"wrote dictionary.json ({os.path.getsize(out) / 1024:.0f} KB)")


# --------------------------------------------------------------------------- #
# Icons
#
# The mark is two bars: a full-width one above a half-width one — a line of
# writing being abbreviated. Rendered here with a minimal pure-Python PNG
# encoder so the build has no image dependencies.
# --------------------------------------------------------------------------- #

INK = (0xA8, 0x3C, 0x38)     # bref accent red
PAPER = (0xFB, 0xFB, 0xFA)   # warm paper

# Rectangles in a 32x32 design grid: (x, y, w, h, colour)
DESIGN = [
    (0, 0, 32, 32, INK),
    (4, 4, 24, 24, PAPER),
    (7.5, 11, 17, 3, INK),
    (7.5, 18, 8.5, 3, INK),
]


def render(size):
    """Rasterise DESIGN at `size` px, returning rows of RGB bytes."""
    k = size / 32.0
    rows = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            colour = PAPER
            for rx, ry, rw, rh, c in DESIGN:
                if rx * k <= x < (rx + rw) * k and ry * k <= y < (ry + rh) * k:
                    colour = c
            row += bytes(colour)
        rows.append(bytes(row))
    return rows


def write_png(path, size):
    rows = render(size)
    raw = b"".join(b"\x00" + r for r in rows)  # filter byte 0 per scanline

    def chunk(tag, payload):
        return (struct.pack(">I", len(payload)) + tag + payload +
                struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)
    print(f"wrote {os.path.basename(path)} ({size}x{size}, "
          f"{os.path.getsize(path)} bytes)")


SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" fill="#a83c38"/>
  <rect x="4" y="4" width="24" height="24" fill="#fbfbfa"/>
  <rect x="7.5" y="11" width="17" height="3" fill="#a83c38"/>
  <rect x="7.5" y="18" width="8.5" height="3" fill="#a83c38"/>
</svg>
"""

with open(os.path.join(HERE, "favicon.svg"), "w", encoding="utf-8") as fh:
    fh.write(SVG)
print("wrote favicon.svg")

write_png(os.path.join(HERE, "icon-192.png"), 192)
write_png(os.path.join(HERE, "icon-512.png"), 512)

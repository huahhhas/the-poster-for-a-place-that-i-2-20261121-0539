#!/usr/bin/env python3
"""VELMARIS — a travel poster for a town above the sea of clouds.

Pure Python standard library only (os, math, struct, zlib). The grader
runs this in the official python image, which has no Pillow, so the PNG is
encoded by hand and every shape is drawn on a bytearray canvas.

The poster: dusk over a cliffside town. A lighthouse stands on the cliff
edge above a sea of clouds; the low sun hangs near the horizon; the name
VELMARIS is set big across the sky. Deterministic: no randomness, no
wall-clock time, no dict-order dependence — two runs write identical bytes.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- canvas

class Canvas:
    """RGB canvas backed by one bytearray. (0, 0) is the top-left corner."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def _off(self, x, y):
        return (y * self.w + x) * 3

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            o = self._off(x, y)
            self.px[o] = color[0]
            self.px[o + 1] = color[1]
            self.px[o + 2] = color[2]

    def rect(self, x0, y0, x1, y1, color):
        """Filled axis-aligned rectangle, clipped. Fast slice fills."""
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for y in range(y0, y1):
            o = self._off(x0, y)
            self.px[o:o + len(row)] = row

    def row_fill(self, y, x0, x1, color):
        if y < 0 or y >= self.h:
            return
        x0 = max(0, x0)
        x1 = min(self.w, x1)
        if x1 <= x0:
            return
        row = bytes(color) * (x1 - x0)
        o = self._off(x0, y)
        self.px[o:o + len(row)] = row

    def hline(self, x0, x1, y, color, thick=1):
        for dy in range(thick):
            self.row_fill(y + dy, x0, x1, color)

    def vgrad(self, stops):
        """Vertical gradient. stops: list of (y, color) sorted by y."""
        for i in range(len(stops) - 1):
            y0, c0 = stops[i]
            y1, c1 = stops[i + 1]
            if y1 <= y0:
                continue
            for y in range(max(0, y0), min(self.h, y1)):
                t = (y - y0) / (y1 - y0)
                c = tuple(int(c0[k] + (c1[k] - c0[k]) * t) for k in range(3))
                row = bytes(c) * self.w
                o = self._off(0, y)
                self.px[o:o + len(row)] = row

    def ellipse(self, cx, cy, rx, ry, color):
        """Filled ellipse, scanline fill."""
        if rx <= 0 or ry <= 0:
            return
        for y in range(max(0, cy - ry), min(self.h, cy + ry + 1)):
            dy = (y - cy) / ry
            dx = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
            self.row_fill(y, int(cx - dx), int(cx + dx) + 1, color)

    def circle(self, cx, cy, r, color):
        self.ellipse(cx, cy, r, r, color)

    def polygon(self, pts, color):
        """Filled polygon (convex or concave), scanline fill."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        ymin = max(0, min(ys))
        ymax = min(self.h - 1, max(ys))
        n = len(pts)
        for y in range(ymin, ymax + 1):
            xs = []
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if y0 == y1:
                    continue
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            if len(xs) < 2:
                continue
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.row_fill(y, int(xs[k]), int(xs[k + 1]) + 1, color)

    def blend_rect(self, x0, y0, x1, y1, color, alpha):
        """Blend a translucent rectangle over the canvas (alpha 0..1)."""
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        for y in range(y0, y1):
            for x in range(x0, x1):
                o = self._off(x, y)
                for k in range(3):
                    self.px[o + k] = int(
                        self.px[o + k] * (1.0 - alpha) + color[k] * alpha)

    def blend_ellipse(self, cx, cy, rx, ry, color, alpha):
        """Blend a translucent filled ellipse over the canvas."""
        if rx <= 0 or ry <= 0:
            return
        for y in range(max(0, cy - ry), min(self.h, cy + ry + 1)):
            dy = (y - cy) / ry
            dx = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
            xa = max(0, int(cx - dx))
            xb = min(self.w, int(cx + dx) + 1)
            for x in range(xa, xb):
                o = self._off(x, y)
                for k in range(3):
                    self.px[o + k] = int(
                        self.px[o + k] * (1.0 - alpha) + color[k] * alpha)

    def blend_polygon(self, pts, color, alpha):
        """Blend a translucent polygon over the canvas (alpha 0..1)."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        ymin = max(0, min(ys))
        ymax = min(self.h - 1, max(ys))
        n = len(pts)
        for y in range(ymin, ymax + 1):
            xs = []
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if y0 == y1:
                    continue
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            if len(xs) < 2:
                continue
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa = max(0, int(xs[k]))
                xb = min(self.w, int(xs[k + 1]) + 1)
                for x in range(xa, xb):
                    o = self._off(x, y)
                    for c in range(3):
                        self.px[o + c] = int(
                            self.px[o + c] * (1.0 - alpha) + color[c] * alpha)

    def line(self, x0, y0, x1, y1, color, thick=1):
        """Thick line drawn as a chain of small filled circles."""
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        r = max(1, thick // 2)
        for i in range(steps + 1):
            t = i / steps
            x = int(x0 + (x1 - x0) * t)
            y = int(y0 + (y1 - y0) * t)
            self.circle(x, y, r, color)


# ---------------------------------------------------------------- font
# 5x7 bitmap font. Each glyph is 7 rows of 5 cells; '#' is ink, '.' is blank.

GLYPHS = {
    "A": ("#...#", "##..#", "#.#.#", "#...#", "#####", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", ".#.#.", ".#.#.", "..#..", "..#..", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    "-": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    "'": ("..#..", "..#..", ".....", ".....", ".....", ".....", "....."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "!": (".#...", ".#...", ".#...", ".#...", ".#...", ".....", ".#..."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
}

# The A glyph above is a redrawn variant; keep the classic block A instead.
GLYPHS["A"] = (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#")


def text_width(text, scale):
    return len(text) * 6 * scale - scale


def draw_text(cv, text, cx, y, scale, color, outline=None):
    """Draw text centred on cx, top edge at y. outline draws a halo first."""
    w = text_width(text, scale)
    x = cx - w // 2
    if outline is not None:
        for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2), (2, 2), (-2, -2)):
            _stamp(cv, text, x + dx, y + dy, scale, outline)
    _stamp(cv, text, x, y, scale, color)


def _stamp(cv, text, x0, y0, scale, color):
    x = x0
    for ch in text:
        glyph = GLYPHS.get(ch.upper(), GLYPHS[" "])
        for row in range(7):
            line = glyph[row]
            for col in range(5):
                if line[col] == "#":
                    cv.rect(x + col * scale, y0 + row * scale,
                            x + col * scale + scale, y0 + row * scale + scale,
                            color)
        x += 6 * scale


# ---------------------------------------------------------------- png

def write_png(cv, path):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * cv.w * 3:(y + 1) * cv.w * 3]
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ---------------------------------------------------------------- scene

# Palette
INK = (24, 22, 52)          # deep dusk indigo (sky top)
VIOLET = (96, 64, 138)      # mid sky
AMBER = (246, 178, 104)     # horizon band
SUN = (255, 216, 132)       # low sun
CREAM = (252, 244, 226)     # cloud tops / name
CLOUD_ROSE = (246, 216, 198)
CLOUD_GOLD = (250, 226, 172)
CLOUD_SHADE = (216, 198, 208)
CLIFF = (40, 42, 62)        # rock
CLIFF_LIT = (72, 66, 96)    # rock lit edge
ROOF = (122, 52, 48)        # terracotta roofs
WALL = (238, 222, 196)      # town walls
WINDOW = (255, 196, 90)     # lit windows
TOWER = (244, 238, 226)     # lighthouse white
BAND = (178, 52, 46)        # lighthouse red bands
BEAM = (255, 232, 160)      # light beam
GOLD = (212, 164, 74)       # rule line / accents


def draw_poster(cv):
    # -- dusk sky, top to horizon (y 0..640)
    cv.vgrad([(0, INK), (260, (58, 44, 104)), (470, VIOLET), (640, AMBER)])
    # -- stars in the upper sky (fixed deterministic positions)
    for i in range(46):
        x = 30 + (i * 97) % 960
        y = 18 + (i * 61) % 210
        cv.rect(x, y, x + 2, y + 2, CREAM if i % 3 else SUN)

    # -- low sun with halo, near the horizon left of centre
    sx, sy = 352, 596
    cv.circle(sx, sy, 96, (250, 196, 128))
    cv.circle(sx, sy, 70, (252, 204, 122))
    cv.circle(sx, sy, 48, SUN)
    cv.circle(sx, sy, 40, (255, 226, 150))

    # -- birds
    for bx, by, s in ((180, 180, 9), (238, 150, 7), (700, 120, 8),
                      (820, 200, 7), (120, 250, 6)):
        cv.line(bx - s, by - 3, bx, by, INK, 2)
        cv.line(bx, by, bx + s, by - 3, INK, 2)

    # -- sea of clouds: base band then billows
    cv.rect(0, 640, W, H, CLOUD_SHADE)
    # far cloud bank (soft, darker)
    for cx, cy, rx, ry in (
            (120, 660, 220, 42), (420, 650, 260, 48), (760, 658, 240, 44),
            (960, 652, 200, 40), (60, 690, 180, 36)):
        cv.ellipse(cx, cy, rx, ry, CLOUD_ROSE)
    # near billows (bright cream, catching the sun)
    for cx, cy, rx, ry, col in (
            (180, 760, 260, 70, CREAM), (520, 730, 300, 84, CREAM),
            (880, 750, 260, 76, CREAM), (60, 860, 240, 80, CREAM),
            (380, 880, 300, 90, CLOUD_GOLD), (760, 900, 300, 96, CREAM),
            (980, 880, 220, 84, CLOUD_ROSE), (140, 970, 260, 70, CREAM),
            (560, 990, 320, 80, CREAM), (900, 990, 260, 70, CLOUD_GOLD)):
        cv.ellipse(cx, cy, rx, ry, col)
    # cloud shadows (soft undersides, blended so the edges stay gentle)
    for cx, cy, rx, ry in (
            (300, 830, 200, 34), (700, 850, 220, 36), (120, 930, 180, 30),
            (860, 950, 200, 32)):
        cv.blend_ellipse(cx, cy, rx, ry, CLOUD_SHADE, 0.45)

    # -- cliff: a dark rock mass rising from the lower right, top edge
    #    jagged, plateau on top where the town stands.
    cliff = [(560, 1024), (560, 760), (600, 700), (640, 712), (690, 640),
             (760, 660), (820, 600), (880, 620), (940, 560), (1024, 580),
             (1024, 1024)]
    cv.polygon(cliff, CLIFF)
    # lit rim along the cliff top edge
    cv.line(560, 760, 600, 700, CLIFF_LIT, 4)
    cv.line(600, 700, 640, 712, CLIFF_LIT, 4)
    cv.line(640, 712, 690, 640, CLIFF_LIT, 4)
    cv.line(690, 640, 760, 660, CLIFF_LIT, 4)
    cv.line(760, 660, 820, 600, CLIFF_LIT, 4)
    cv.line(820, 600, 880, 620, CLIFF_LIT, 4)
    cv.line(880, 620, 940, 560, CLIFF_LIT, 4)
    cv.line(940, 560, 1024, 580, CLIFF_LIT, 4)
    # rock cracks
    cv.line(700, 700, 760, 820, (28, 30, 46), 3)
    cv.line(860, 660, 900, 800, (28, 30, 46), 3)
    cv.line(640, 760, 620, 880, (28, 30, 46), 3)
    cv.line(980, 640, 960, 780, (28, 30, 46), 3)
    # cliff dwellings: a few lit windows carved into the rock face
    for wx, wy in ((660, 830), (700, 880), (740, 840), (880, 860),
                   (920, 900), (980, 840)):
        cv.rect(wx, wy, wx + 7, wy + 10, WINDOW)
    # winding path of lights down the cliff face
    for px, py in ((640, 780), (668, 812), (700, 838), (736, 862),
                   (772, 888), (806, 912), (840, 934)):
        cv.circle(px, py, 3, WINDOW)

    # -- town on the cliff plateau (small houses, warm windows)
    houses = [
        # (x, y base, w, h, roof_h)
        (600, 700, 46, 34, 16), (652, 692, 40, 30, 14), (700, 664, 44, 32, 15),
        (752, 676, 42, 30, 14), (800, 640, 48, 34, 16), (856, 652, 44, 32, 15),
        (906, 610, 46, 34, 16), (948, 626, 40, 30, 14),
    ]
    for hx, hy, hw, hh, rh in houses:
        cv.rect(hx, hy - hh, hx + hw, hy, WALL)
        cv.polygon([(hx - 4, hy - hh), (hx + hw // 2, hy - hh - rh),
                    (hx + hw + 4, hy - hh)], ROOF)
        # two lit windows per house
        for wx in (hx + 7, hx + hw - 13):
            cv.rect(wx, hy - hh + 10, wx + 6, hy - hh + 18, WINDOW)

    # -- lighthouse on the cliff edge, right of the town
    lx = 968  # tower centre x
    base_y = 600
    top_y = 372
    # tapered shaft
    cv.polygon([(lx - 26, base_y), (lx - 17, top_y), (lx + 17, top_y),
                (lx + 26, base_y)], TOWER)
    # red bands (width at band height, shaft tapers)
    for by0, by1 in ((520, 552), (448, 480)):
        t = (by0 - top_y) / (base_y - top_y)
        half = int(17 + (26 - 17) * t) + 1
        cv.rect(lx - half, by0, lx + half, by1, BAND)
    # gallery + lamp room
    cv.rect(lx - 24, top_y - 14, lx + 24, top_y, INK)
    cv.rect(lx - 13, top_y - 44, lx + 13, top_y - 14, WINDOW)
    cv.rect(lx - 16, top_y - 52, lx + 16, top_y - 44, INK)
    cv.polygon([(lx - 18, top_y - 52), (lx, top_y - 72), (lx + 18, top_y - 52)],
               BAND)
    # light beam sweeping down-left from the lamp, warm and bright
    cv.blend_polygon([(lx - 10, top_y - 30), (lx - 10, top_y - 14),
                      (540, 520), (540, 560)], BEAM, 0.50)
    cv.blend_polygon([(lx + 10, top_y - 30), (lx + 10, top_y - 14),
                      (1024, 300), (1024, 322)], BEAM, 0.16)

    # -- name: VELMARIS, big across the upper sky
    draw_text(cv, "VELMARIS", 512, 84, 13, CREAM, outline=INK)
    # -- gold rule
    cv.rect(512 - 110, 214, 512 + 110, 218, GOLD)
    # -- subtitle
    draw_text(cv, "ABOVE THE SEA OF CLOUDS", 512, 238, 3, CREAM, outline=INK)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = Canvas(W, H)
    draw_poster(cv)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(cv, path)
    print("wrote %s (%d bytes)" % (path, size))


if __name__ == "__main__":
    main()

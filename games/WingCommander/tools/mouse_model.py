#!/usr/bin/env python3
"""Expected mouse flight pointer for the checks (src/mouse.s): the pointer
moves with the mouse, two counts a pixel, anywhere on the screen from the
gunsight; the stick and the ramps follow from its place in the PC version's
steps. Also a synthetic cockpit and the masked image lines."""

APERTURE = (320, 105, 159, 62, 0, 10)      # width, height, centre x, y, left, top (Nav-1)
POINTER = (0x1c00, 0x6b00, 0x4900, 0x8080, 0xeb80, 0x8080, 0x4900, 0x6b00, 0x1c00)
KEY = 17
STICK_LEVEL = 9         # stick units per PC step
STEPS_X = (10, 37, 52, 57, 62)     # WC.EXE: a step more from each distance
STEPS_Y = (5, 18, 27, 35, 38)
SCREEN = (319, 199)


def toward_zero(a, b):
    q = abs(a)//b
    return q if a >= 0 else -q


def level(pixel, centre, first, last, steps):
    """The PC's stick step for a pointer pixel: 8 within 4 pixels of the
    aperture's edges, else the steps reached by the distance from the centre."""
    if pixel-4 <= first:
        return -8
    if pixel+4 >= last:
        return 8
    d = pixel-centre
    n = sum(1 for t in steps if abs(d) >= t)
    return n if d >= 0 else -n


class Pointer:
    """The pointer's offset from the gunsight in half pixels."""

    def __init__(self, ap=APERTURE):
        self.ap, self.x, self.y = ap, 0, 0

    def move(self, dx, dy):
        cx, cy = self.ap[2], self.ap[3]
        self.x = min(max(self.x+dx, -2*cx), 2*(SCREEN[0]-cx)+1)
        self.y = min(max(self.y+dy, -2*cy), 2*(SCREEN[1]-cy)+1)
        return self

    def centre(self):
        self.x = self.y = 0
        return self

    def stick(self):
        w, h, cx, cy, x0, y0 = self.ap
        px, py = self.at()
        return (STICK_LEVEL*level(px, cx, x0, x0+w-1, STEPS_X),
                STICK_LEVEL*level(py, cy, y0, y0+h-1, STEPS_Y))

    def ramps(self):
        """(pitch, yaw): mouse right is yaw +, mouse down pitch - (stick back)."""
        sx, sy = self.stick()
        return -toward_zero(sy, 8), toward_zero(sx, 8)

    def at(self):
        """The pointer's centre pixel."""
        cx, cy = self.ap[2], self.ap[3]
        return cx+(self.x >> 1), cy+(self.y >> 1)

    def sprite(self):
        """MoveSprite's position: sprite pixel 0 is at x+1."""
        px, py = self.at()
        return px-5, py-4

    def lines(self):
        """The image lines: the pointer's pixels over the cockpit's key pixels."""
        px, py = self.at()
        out = []
        for r, bits in enumerate(POINTER):
            y = py-4+r; line = 0
            for c in range(9):
                x = px-4+c
                if 0 <= x < 320 and 0 <= y < 200 and cockpit(x, y) == KEY:
                    line |= 1 << (15-c)
            out.append(line & bits)
        return out


def cockpit(x, y):
    """Synthetic cockpit: its key colour where the view shows through, on
    rows 10-114 as in the Nav-1 cockpit."""
    solid = (y < 10 or y > 114 or (x < 24 and y > 44) or (100 <= x < 220 and y >= 72)
             or (x, y) in ((158, 58), (156, 64)) or (200 <= x < 204 and y < 40))
    return 5 if solid else KEY

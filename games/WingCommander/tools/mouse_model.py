#!/usr/bin/env python3
"""Expected mouse flight pointer for the checks (src/mouse.s): the pointer
moves with the mouse, two counts a pixel, within its limits around the
gunsight; the stick and the ramps follow from its place. Also a synthetic
cockpit and the masked image lines."""

APERTURE = (320, 105, 159, 62, 0, 10)      # width, height, centre x, y, left, top (Nav-1)
POINTER = (0x1c00, 0x6b00, 0x4900, 0x8080, 0xeb80, 0x8080, 0x4900, 0x6b00, 0x1c00)
KEY = 17
STICK_RANGE = 72
REACH_BELOW = 13        # pixels past the aperture's last row: the pointer one height under it


def toward_zero(a, b):
    q = abs(a)//b
    return q if a >= 0 else -q


def limits(ap=APERTURE):
    """Pixels from the gunsight to the pointer's left, right, top and bottom limits."""
    w, h, cx, cy, x0, y0 = ap
    return tuple(max(v, 1) for v in (cx-x0, x0+w-1-cx, cy-y0, y0+h-1+REACH_BELOW-cy))


class Pointer:
    """The pointer's offset from the gunsight in half pixels."""

    def __init__(self, ap=APERTURE):
        self.ap, self.x, self.y = ap, 0, 0

    def move(self, dx, dy):
        left, right, up, down = limits(self.ap)
        self.x = min(max(self.x+dx, -2*left), 2*right)
        self.y = min(max(self.y+dy, -2*up), 2*down)
        return self

    def centre(self):
        self.x = self.y = 0
        return self

    def stick(self):
        left, right, up, down = limits(self.ap)
        return (toward_zero(self.x*STICK_RANGE, 2*(right if self.x >= 0 else left)),
                toward_zero(self.y*STICK_RANGE, 2*(down if self.y >= 0 else up)))

    def ramps(self):
        """(pitch, yaw): mouse right is yaw +, mouse down pitch - (stick back)."""
        sx, sy = self.stick()
        return -toward_zero(sy, 8), toward_zero(sx, 8)

    def at(self):
        """The pointer's centre pixel."""
        cx, cy = self.ap[2], self.ap[3]
        return min(max(cx+(self.x >> 1), 0), 319), min(max(cy+(self.y >> 1), 0), 199)

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

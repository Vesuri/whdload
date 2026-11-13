#!/usr/bin/env python3
"""Expected mouse flight pointer for the native checks (src/mouse.s): its
position from the stick, a synthetic cockpit and the masked image lines."""

APERTURE = (320, 105, 159, 62, 0, 10)      # width, height, centre x, y, left, top (Nav-1)
POINTER = (0x1c00, 0x6b00, 0x4900, 0x8080, 0xeb80, 0x8080, 0x4900, 0x6b00, 0x1c00)
KEY = 17


def toward_zero(a, b):
    q = abs(a)//b
    return q if a >= 0 else -q


def pointer_at(stick, ap=APERTURE):
    """The pointer centre for a stick position: from the aperture centre to
    its edges horizontally, 23 pixels vertically, at full deflection."""
    w, h, cx, cy, x0, y0 = ap
    sx, sy = stick
    reach = cx-x0 if sx < 0 else x0+w-1-cx
    return min(max(cx+toward_zero(sx*reach, 72), 0), 319), min(max(cy+toward_zero(sy*23, 72), 0), 199)


def cockpit(x, y):
    """Synthetic cockpit: its key colour where the view shows through. Key
    rows 10-114 put the native centre row at 62, as in the Nav-1 cockpit."""
    solid = (y < 10 or y > 114 or (x < 24 and y > 44) or (100 <= x < 220 and y >= 72)
             or (x, y) in ((158, 58), (156, 64)) or (200 <= x < 204 and y < 40))
    return 5 if solid else KEY


def lines(stick, ap=APERTURE):
    """The masked pointer image lines at a stick position."""
    px, py = pointer_at(stick, ap)
    cy = ap[3]
    out = []
    for r, bits in enumerate(POINTER):
        y = py-4+r; line = 0
        for c in range(9):
            x = px-4+c
            if 0 <= x < 320 and abs(y-cy) <= 27 and cockpit(x, y) == KEY:
                line |= 1 << (15-c)
        out.append(line & bits)
    return out

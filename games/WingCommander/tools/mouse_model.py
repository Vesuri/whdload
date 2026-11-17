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


# Left button in flight (mouse_flight_fire). One entry per field: the button
# down or up. The game's flight poll fires on record +8 (held after a double
# click) or +7 (a click's release; the read clears it) and takes the modifier
# on +5 (held past the threshold) without +8. CD32 also fires on +13.
FIRE_SEQUENCE = [1]*30 + [0]*100 + [1]*60 + [0]*20 + [1] + [0]*20 + [1]*3 + [0]*20


def fire_poll(record):
    """(fire, modifier) the flight poll takes from a decoded port-1 record."""
    fire = bool(record[8] or record[7] or (len(record) > 13 and record[13]))
    return fire, bool(record[5] and not record[8])


def fire_expected(sequence=FIRE_SEQUENCE, threshold=15):
    """In flight: fire on every held field and on the release of a hold
    shorter than the threshold; never the modifier."""
    want, run = [], 0
    for i, down in enumerate(sequence):
        if down:
            run += 1
            want.append((True, False))
        else:
            want.append((0 < run < threshold, False))
            run = 0
    return want


def fire_native_holds(sequence, polled):
    """Native control: no hold of the threshold or longer fired after its
    first fields (a hold alone is the modifier)."""
    run, stuck = 0, 0
    for down, (fire, modifier) in zip(sequence, polled):
        run = run+1 if down else 0
        if run > 15 and modifier and not fire:
            stuck += 1
    return stuck


# Mouse buttons in flight (mouse_buttons, mouse_poll). One entry per field:
# (left, right, middle, dx, dy), the motion arriving before that field's VBL.
def _fields(n, left=0, right=0, middle=0, dx=0, dy=0):
    return [(left, right, middle, dx, dy)]*n


BUTTON_SEQUENCE = (
    _fields(10)
    + _fields(20, right=1, dy=-3) + _fields(10, right=1, dx=3)        # faster, roll right
    + _fields(10, right=1, dx=-3, dy=3) + _fields(5, right=1) + _fields(20)  # slower, roll left, still
    + _fields(5, right=1) + _fields(5) + _fields(30, right=1) + _fields(20)  # double click held: afterburner
    + _fields(5, right=1) + _fields(20) + _fields(10, right=1) + _fields(20)  # clicks too far apart
    + _fields(20, right=1) + _fields(5) + _fields(10, right=1) + _fields(20)  # a long first press
    + _fields(10, left=1) + _fields(10, left=1, right=1) + _fields(20)  # left, then both: a missile
    + _fields(10, right=1) + _fields(5, left=1, right=1) + _fields(20)  # right, then both: a missile
    + _fields(3, middle=1) + _fields(10)                               # middle: a missile
    + _fields(10, dx=-3, dy=3))                                        # motion alone: nothing
BUTTON_KEYS = b'\t'*6 + b'\r'*3      # what the sequence queues: six Tabs, three Enters


def buttons_expected(sequence=BUTTON_SEQUENCE, flight=True, lines=True, step=4, click=15, gap=15, repeat=5):
    """Per field, the flight poll's flags (left, right, up, down, modifier,
    fire) and the keys queued, with native flags zero but fire = the left
    button. The right button held: the modifier, no fire, and the last four
    fields' motion beyond step as directions (forward is up). A right press
    within gap fields of a click's release (a press under click fields) is
    the afterburner: Tab at once and every repeat fields while held. Both
    buttons going down together, or a middle press: Enter. Without a flight
    nothing changes; lines that never read up (lines False) are never down."""
    prev, seen = (1, 1, 1), [False, False]
    held = gapc = short = burn = sent = tab = missile = 0
    ring = [(0, 0)]*4
    rows = []
    for i, (left, right, middle, dx, dy) in enumerate(sequence):
        if lines:
            seen = [seen[0] or not right, seen[1] or not middle]
        now = (left, right and seen[0], middle and seen[1])
        ring = ring[1:]+[(dx, dy)]
        if not flight:
            burn = missile = short = 0
        else:
            if now[1]:
                if not prev[1]:
                    held = 0
                    if short and gapc <= gap:
                        burn = 1
                held = min(held+1, click)
            else:
                if prev[1]:
                    short = int(0 < held < click and not burn)
                    gapc = 0
                    burn = 0
                gapc = min(gapc+1, gap+1)
            if (now[0] and now[1] and not (prev[0] and prev[1])) or (now[2] and not prev[2]):
                missile = 1
        prev = now
        flags = [0, 0, 0, 0, 0, left]
        keys = b''
        if flight:
            if now[1]:
                flags[4], flags[5] = 1, 0
                sx, sy = sum(x for x, _ in ring), sum(y for _, y in ring)
                flags[0], flags[1] = int(sx <= -step), int(sx >= step)
                flags[2], flags[3] = int(sy <= -step), int(sy >= step)
            if missile:
                keys += b'\r'
                missile = 0
            if not burn:
                sent = 0
            elif not sent or i-tab >= repeat:
                sent, tab = 1, i
                keys += b'\t'
        else:
            missile = 0
        rows.append((tuple(bool(f) for f in flags), keys))
    return rows

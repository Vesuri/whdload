#!/usr/bin/env python3
"""In-flight profile of the AGA version: profile_flight.py OUT

Boots the AGA slave (gunship2000.Session: warp, deterministic, MACHINE default a1200-030 without
its MMU model, which aprof needs) and clicks through the front end to the cockpit:
DUTY ROSTER (the whiteboard), right click on the WOC ERASE-ME record, name "test" + Return,
Return (unit patch), unit "test" + Return, click the record, MISSION BRIEFING (the door), click
the photo, BEGIN MISSION (the map), five clicks on the keypad, the Aux Power Unit tab, its switch.
When the cockpit appears: `monitor aprof start`, F5 (chase view), 3 s, F6 (tactical view), 3 s.
The window is profiled as two aprof files of 150 fields each, OUT/f5.prof and OUT/f6.prof (one
unprofiled field between them for a screenshot). Also writes OUT/route/*.png (a screenshot at
every step), OUT/layout.json (where gs2.run's hunks and the memory lists are) and
OUT/state.json (game clocks at the window's ends). Summarise with aprof_report.py OUT.

Each step waits for its screen by colour (screen()), so the route holds on slower machines.
"""
import json
import os
import sys
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gunship2000 import Session  # noqa: E402
import gs2  # noqa: E402

# Screenshot coordinates (754x576 shots; the pointer is Intuition's, at shot - SHOT_ORIGIN).
SHOT_ORIGIN = (78, 37)
WHITEBOARD = (443, 177)
RECORD = (240, 240)          # the first squadron record, WOC ERASE-ME
DOOR = (560, 215)
PHOTO = (400, 250)           # the briefing tent picture shown first after the door
MAP = (200, 150)
KEYPAD_5 = (491, 236)
APU_TAB = (645, 280)
APU_SWITCH = (645, 298)
SEGMENT = 150                # fields: 3 s


def mean(a, box):
    x0, y0, x1, y1 = box
    return a[y0:y1, x0:x1].reshape(-1, 3).mean(axis=0)


def screen(a):
    """Which front-end screen a shot shows, by the mean colour of one region each."""
    r, g, b = mean(a, (90, 80, 150, 260))            # the office window
    if b > r + 10 and r > 150 and mean(a, (74, 420, 714, 436)).max() < 40:
        return 'office'
    if mean(a, (120, 50, 600, 170)).min() > 210:      # the white squadron board
        return 'records'
    if mean(a, (90, 385, 500, 412)).min() > 230:      # the briefing's white orders bar
        return 'briefing'
    r, g, b = mean(a, (80, 40, 700, 120))             # the tent roof
    if g > r + 10 and g > b + 10 and g > 90:
        return 'photo'
    r, g, b = mean(a, (632, 258, 660, 300))           # the red APU cover
    if r > 150 and g < 50:
        return 'keypad'
    return None


def black(a):
    return (a[36:418, 74:714].max(axis=2) > 24).mean() < 0.02


def lit(a):
    return (a[36:418, 74:714].max(axis=2) > 24).mean() > 0.5


class Flight:
    def __init__(self, s):
        self.s = s
        self.step = 0
        (s.out / 'route').mkdir(exist_ok=True)

    def intuition(self):
        """IntuitionBase: the pointer position is MouseX at +$46, MouseY at +$44."""
        if not hasattr(self, 'ibase'):
            self.ibase = gs2.library(self.s, 'intuition.library')
        b = self.s.read(self.ibase + 0x44, 4)
        return int.from_bytes(b[2:], 'big'), int.from_bytes(b[:2], 'big')

    def move_to(self, target, tol=1):
        tx, ty = target[0] - SHOT_ORIGIN[0], target[1] - SHOT_ORIGIN[1]
        for _ in range(60):
            x, y = self.intuition()
            dx, dy = tx - x, ty - y
            if abs(dx) <= tol and abs(dy) <= tol:
                return
            self.s.cmd(f'monitor mouse {max(-64, min(64, dx))} {max(-64, min(64, dy))}')
            self.s.fields(2)
        raise TimeoutError(f'pointer did not reach {target}: {self.intuition()}')

    def click_at(self, target, button=1, after=4):
        # The front end polls the buttons once per animation frame: hold for 10 fields.
        self.move_to(target)
        self.s.fields(4)
        self.s.click(button, hold=10, after=after)

    def type(self, text):
        for c in text:
            self.s.tap(c, hold=4, after=10)

    def shot(self, name):
        self.step += 1
        return self.s.shot(f'route/{self.step:02d}-{name}.png')

    def wait_for(self, name, limit=4000, every=10, test=None):
        """Run fields until two screenshots in a row show screen `name` (or pass `test`); keep
        the second as the step's shot."""
        test = test or (lambda a: screen(a) == name)
        seen = 0
        poll = self.s.out / 'route/poll.png'
        for _ in range(0, limit, every):
            self.s.fields(every - 1)
            self.s.shot('route/poll.png')
            seen = seen + 1 if test(np.asarray(Image.open(poll).convert('RGB'))) else 0
            if seen == 2:
                self.step += 1
                return poll.rename(poll.with_name(f'{self.step:02d}-{name}.png'))
        raise TimeoutError(f'{name}: not on screen after {limit} fields (last: route/poll.png)')


def route(f):
    s = f.s
    f.wait_for('office', every=50)
    f.click_at(WHITEBOARD)
    f.wait_for('records')
    f.click_at(RECORD, button=2)
    s.fields(50)
    f.type('test')
    s.tap('ret', hold=4, after=30)
    f.shot('patch')
    s.tap('ret', hold=4, after=30)
    f.type('test')
    s.tap('ret', hold=4, after=50)
    f.shot('unit')
    f.click_at(RECORD)
    f.wait_for('office')
    f.click_at(DOOR)
    f.wait_for('photo')
    f.click_at(PHOTO)
    f.wait_for('briefing')
    f.click_at(MAP)
    f.wait_for('keypad')
    s.fields(50)
    f.move_to(KEYPAD_5)
    s.fields(4)
    for _ in range(5):
        s.click(1, hold=10, after=10)
    s.fields(20)
    f.shot('code')
    f.click_at(APU_TAB)
    s.fields(50)
    f.shot('apu')
    f.click_at(APU_SWITCH)
    # The flight loads behind a black screen (seconds); the cockpit is the next lit picture.
    # Which helicopter and cockpit it is depends on the mission the front end picked.
    f.wait_for('loading', every=5, test=black)
    return f.wait_for('cockpit', every=5, test=lit)


def main(out):
    s = Session(out)
    try:
        f = Flight(s)
        t0 = time.time()
        route(f)
        print(f'cockpit at field {s.field} ({time.time() - t0:.0f} s)', flush=True)
        layout = gs2.locate(s)
        (s.out / 'layout.json').write_text(json.dumps(layout, indent=1))
        state = {'start': gs2.clocks(s, layout)}
        s.aprof_start()
        s.tap('f5', hold=10, after=SEGMENT - 10)
        s.aprof_stop(s.out / 'f5.prof')
        state['f5'] = gs2.clocks(s, layout)
        f.shot('chase')
        state['f5_shot'] = gs2.clocks(s, layout)
        s.aprof_start()
        s.tap('f6', hold=10, after=SEGMENT - 10)
        s.aprof_stop(s.out / 'f6.prof')
        state['f6'] = gs2.clocks(s, layout)
        f.shot('tactical')
        state['fields'] = s.field
        state['env'] = {k: s.env.get(k) for k in ('SETUP', 'EXTRA_ARGS', 'VARIANT', 'SLAVE')}
        (s.out / 'state.json').write_text(json.dumps(state, indent=1))
        print(json.dumps(state), flush=True)
    finally:
        s.quit()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])

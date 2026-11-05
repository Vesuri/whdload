#!/usr/bin/env python3
"""F4: build the edited game directories from pinned inputs with F1GP-Ed, and check them.

  python3 tools/f4_inputs.py build OUT [VARIANT...]   (OUT normally tmp/f4/inputs)
  python3 tools/f4_inputs.py verify OUT

Each VARIANT (default all) boots tools/ed.sh on a fresh copy of the pinned game's data
directory, drives F1GP-Ed 3.44 with the keyboard and the homed pointer (the window and
gadget positions of its default Workbench 2.04 screen), and copies the result into
OUT/VARIANT, a copy of the verified stock game directory with the edited data/f1gp and
backdrops:
  datafile  2002.f1gp, F1GP-Ed's supplied datafile, saved to the binary (F1's df-2002)
  graphics  the stock settings with Graphics/MattCockpit.settings saved to the binary
            (Matthias Fisch's cockpit) and Graphics/c_champ_ferrari.ilbm replacing
            c_champ.bkg (Backdrops, a palette-change backdrop: it also writes the binary)
  combined  2002.f1gp, then the cockpit and the backdrop, in one session
  mclaren   the supplied McLaren-D2 cockpit on the stock settings, for the collision
            checks (it moves more parts); its settings name the image without its
            drawer, so the full path is typed into the Image gadget. The third supplied
            cockpit, JBCPIT99F, is left out: the same steps left the binary unchanged
            (not investigated)
OUT/VARIANT/shots holds a screenshot after each step. verify compares the edited files
with manifest/f4-inputs.json (SHA-256 of each file that differs from the stock game).
"""
import filecmp
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slave_inputs import ROOT, verify as verify_game  # noqa: E402

STOCK = ROOT/'tmp/game/FormulaOneGrandPrix4Disk'
DATAFILE = ROOT/'tmp/game/F1GP-Ed/2002.f1gp'
RUN = ROOT/'tmp/run/ed/.run/dh1'
PINS = ROOT/'manifest/f4-inputs.json'
VARIANTS = {'datafile': ('save',), 'graphics': ('cockpit', 'backdrop'),
            'combined': ('save', 'cockpit', 'backdrop'),
            'mclaren': ('cockpit:mclaren-d2:mclaren-d2.ilbm',)}
R_AMIGA, L_AMIGA, SHIFT, RETURN = 0x67, 0x66, 0x60, 0x44
KEYS = (dict(zip('qwertyuiop', range(0x10, 0x1a))) | dict(zip('asdfghjkl', range(0x20, 0x29)))
        | dict(zip('zxcvbnm', range(0x31, 0x38))) | dict(zip('123456789', range(1, 10)))
        | {'0': 0x0a, '-': 0x0b, '.': 0x39, '/': 0x3a})
SHIFTED = {'_': 0x0b, ':': 0x29}
# Screenshot pixels: the main window's Other list, the windows' close gadget, the file
# requester's Load/Save button and F1GP-Ed's "modify your F1GP binary" OK.
GRAPHICS, BACKDROPS, CLOSE, REQUEST_OK, CONFIRM = (470, 145), (470, 193), (83, 68), (150, 421), (103, 189)
LOAD_SETTINGS, TO_BINARY, IMAGE = (530, 280), (268, 376), (375, 115)
LOAD_IMAGE, C_CHAMP, REPLACE, DRAWER_SAVE = (225, 110), (140, 349), (455, 333), (150, 418)


def Input(g):
    from amigaxdev.input import Input
    return Input(g)


class Session:
    def __init__(self, server, g, shots):
        self.s, self.g, self.shots, self.step = server, g, shots, 0

    def fields(self, n):
        with Input(self.g) as c:
            c.fields(n)

    def click(self, at, wait=100):
        self.s.handle(self.g, f'click {at[0]} {at[1]}')
        self.fields(wait)

    def chord(self, qualifier, key):
        with Input(self.g) as c:
            c.key(qualifier, True); c.fields(5)
            c.key(key, True); c.fields(5)
            c.key(key, False); c.key(qualifier, False); c.fields(50)

    def type(self, text):
        with Input(self.g) as c:
            for ch in text:
                if ch in SHIFTED:
                    c.key(SHIFT, True); c.fields(2)
                    c.key(SHIFTED[ch], True); c.fields(3); c.key(SHIFTED[ch], False)
                    c.key(SHIFT, False)
                else:
                    c.key(KEYS[ch], True); c.fields(3); c.key(KEYS[ch], False)
                c.fields(2)

    def shot(self, name):
        self.step += 1
        self.s.handle(self.g, f'shot {self.shots/f"{self.step:02d}-{name}.png"}')

    def changed(self, paths, before):
        """Wait until every path differs from its copy in before and has settled."""
        for _ in range(60):
            self.fields(50)
            if all(not filecmp.cmp(p, before/p.name, shallow=False) for p in paths):
                break
        else:
            raise RuntimeError(f'F1GP-Ed did not write {[p.name for p in paths]}')
        self.fields(250)

    def snapshot(self, before):
        shutil.rmtree(before, ignore_errors=True)
        before.mkdir()
        for p in RUN.iterdir():
            if p.is_file():
                shutil.copyfile(p, before/p.name)

    def save(self, before):
        self.snapshot(before)
        self.chord(R_AMIGA, 0x35)       # Project/Save to F1GP binary
        self.chord(L_AMIGA, 0x34)       # its confirmation
        self.changed([RUN/'f1gp'], before)
        self.shot('datafile')

    def cockpit(self, before, settings='mattcockpit', image=None):
        self.snapshot(before)
        self.click(GRAPHICS)
        self.click(LOAD_SETTINGS)
        self.type(f'dh0:f1gp-ed/graphics/{settings}.settings')
        self.click(REQUEST_OK, 150)
        if image:
            self.click(IMAGE, 20)
            self.chord(R_AMIGA, 0x32)   # clear the gadget (Right-Amiga X)
            self.type(f'dh0:f1gp-ed/graphics/{image}')
            with Input(self.g) as c:
                c.key(RETURN, True); c.fields(3); c.key(RETURN, False); c.fields(50)
        self.shot('cockpit-settings')
        self.click(TO_BINARY)
        self.click(CONFIRM, 50)
        self.changed([RUN/'f1gp'], before)
        self.shot('cockpit')
        self.click(CLOSE)

    def backdrop(self, before):
        self.snapshot(before)
        self.click(BACKDROPS)
        self.click(LOAD_IMAGE)
        self.type('dh0:f1gp-ed/graphics/c_champ_ferrari.ilbm')
        self.click(REQUEST_OK, 200)
        self.click(C_CHAMP, 30)
        self.shot('backdrop-buffer')
        self.click(REPLACE)
        self.click(DRAWER_SAVE, 200)    # the drawer of c_champ.bkg: f1gp_disk_#3:, DH1
        self.click(CONFIRM, 50)
        self.changed([RUN/'C_CHAMP.BKG'], before)   # then its palette in the binary
        self.shot('backdrop')
        self.click(CLOSE)


def build(out, names):
    os.environ.setdefault('F1ED_HOME', '74,37')   # the pointer's clamp on F1GP-Ed's screen
    import f1_ed
    verify_game()
    out = Path(out).resolve()
    if not out.is_relative_to(ROOT/'tmp'):
        raise ValueError('output must stay in project tmp/')
    os.environ.setdefault('WARP', '1')
    for name in names:
        target = out/name
        if target.exists():
            raise ValueError(f'{target} exists; use a fresh output directory')
        shots = target/'shots'
        env = {'DATAFILE': str(DATAFILE)} if 'save' in VARIANTS[name] else {}
        g = f1_ed.server.boot(env)
        try:
            g.stop()
            with Input(g) as c:
                c.fields(1500)          # Workbench boot and F1GP-Ed's windows
            shutil.copytree(STOCK, target)
            shots.mkdir()
            session = Session(f1_ed.server, g, shots)
            session.shot('start')
            for step in VARIANTS[name]:
                step, *arg = step.split(':')
                getattr(session, step)(out/'.before', *arg)
        finally:
            f1_ed.server.handle(g, 'quit')
        for p in RUN.iterdir():
            if p.is_file() and not p.name.endswith('.uaem'):
                shutil.copyfile(p, target/'data'/p.name)
        shutil.rmtree(out/'.before', ignore_errors=True)
        print(name, json.dumps(edited(target)))


def edited(target):
    """{relative path: SHA-256} of the files that differ from the stock game directory."""
    result = {}
    for p in sorted((target/'data').iterdir()):
        stock = STOCK/'data'/p.name
        if p.is_file() and not filecmp.cmp(p, stock, shallow=False):
            result[f'data/{p.name}'] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def verify(out, names=None):
    pins = json.loads(PINS.read_text())
    for name, files in pins.items():
        if names and name not in names:
            continue
        found = edited(Path(out)/name)
        if found != files:
            raise ValueError(f'{name}: edited files differ from manifest/f4-inputs.json: {found}')
    print('F4 inputs verified:', ', '.join(names or pins))


if __name__ == '__main__':
    if sys.argv[1] == 'build':
        build(sys.argv[2], sys.argv[3:] or list(VARIANTS))
    elif sys.argv[1] == 'verify':
        verify(sys.argv[2])
    else:
        raise SystemExit(__doc__)

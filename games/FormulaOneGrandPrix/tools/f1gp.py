#!/usr/bin/env python3
"""Drive Formula One Grand Prix in FS-UAE through the Barto gdb stub.

  python3 tools/f1gp.py serve          boot (amiga/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/f1gp.py <command...>   send one command to the running server, print the reply

Commands are the shared server's (AmigaXDev amigaxdev.gdbserve): stop, cont, gdb <text>,
shot <png>, profile <fields> <bin> (PAL fields, Barto format), wait <s>, until <addr>, quit,
and:
  quickrace [log]    from boot, drive the menus into a Quick Race at Silverstone and stop
                     at the first race field; optional log file of every input sent.
                     ROUTE_SHOTS=dir (server environment) saves every polled screenshot
  startup [log]      boot to the startup menu, with the same screen checks
  practice [log]     Main Menu -> Practise any Circuit -> Silverstone -> cockpit
  qualifying [log]   Main Menu -> Non-Championship Race -> Silverstone -> Qualifying
  menuclick X Y      click a screenshot coordinate using the homed pointer
  tap RAW [FIELDS]   press a hexadecimal raw key for FIELDS (default 25), then release
  raceprofile PHASE DIR [FIELDS]
                     quickrace, then profile FIELDS (default 500) fields from the green
                     light, the retirement/towing scene or the follow camera
                     (PHASE green|tow|follow) into DIR; see tools/race_profile.py
  raceclock DIR      quickrace, then run the race to the results screen, sampling the game's
                     frame counter; see tools/race_clock.py
Input goes through the native build's harness: gdb monitor key|mouse|input|fields.
The CPU stays halted from reset until the first command (BOOT_BREAK, below); `cont` resumes.
Uses the native arm64 FS-UAE ($FSUAE_ARM) unless FSUAE is set; it profiles the whole
24-bit space without a trigger, so no lldb profiler-window fix.
"""
import io, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev import barto
from amigaxdev.gdbserve import Server, require_harness
from amigaxdev.input import Input
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('FSUAE', os.environ.get('FSUAE_ARM')
                      or os.path.expanduser('~/.local/share/amiga/fs-uae-arm/fs-uae'))

# Screens, as pixels of a one-field trace screenshot (754x576; one mouse count moves the
# pointer one pixel in both axes).  Each colour is a dialog element the pointer never covers.
SCREENS = {
    'main': {(320, 85): 0xffffff, (380, 85): 0xffffff, (340, 95): 0xffffff},
    'circuit': {(260, 105): 0xffffff, (340, 105): 0xffffff, (460, 105): 0xffffff},
    'weekend': {(260, 125): 0xffffff, (380, 125): 0xffffff, (300, 135): 0xffffff},
    'language':   {(555, 258): 0xeecc00, (235, 240): 0xbb0000},     # German, UK flags
    'protection': {(395, 200): 0xbb0000, (555, 258): 0x667799},     # UK flag, no German
    'startup':    {(170, 275): 0xcc0000, (600, 275): 0x667799},     # Quick Race selected
    'track':      {(195, 391): 0xbb0000, (400, 120): 0x0066cc},     # O.K. selected, map sky
    'race':       {(100, 70): 0x5599ff, (84, 424): 0xffffff,        # sky, cockpit
                   (236, 300): 0x555555, (92, 424): 0x555555},
    'green':      {(548, 135): 0x009900, (592, 144): 0x009900,      # start lights green
                   (636, 146): 0x009900},
    'viewing':    {(206, 74): 0x009900, (247, 78): 0x009900,        # banner: green "Viewing"
                   (272, 81): 0x009900},
    'results':    {(190, 252): 0xcc0000, (590, 252): 0xcc0000,      # Non Championship Results
                   (190, 200): 0x667799, (590, 292): 0x667799},
    'times':      {(120, 438): 0x667799, (650, 438): 0x667799,      # Race Finishing Times
                   (200, 100): 0xffff44},
}
HOME = (74, 54)            # the pointer's top-left clamp
OK = {'language': (395, 358), 'startup': (395, 313), 'track': (235, 391),
      'times': (390, 252)}   # results menu: Race Finishing Times
KEY_A, KEY_RETURN = 0x20, 0x44
POLL = 25                  # fields between screen checks
LIMIT = 6000               # fields to wait for any one screen (two minutes of PAL)


def screenshot(server, g):
    target = os.path.join(server.run_dir, 'route.bin')
    g.cmd(f'monitor profile 1 "" "{target}"', timeout=1800)
    return Image.open(io.BytesIO(barto.load(target).fields[-1].shot)).convert('RGB')


def showing(image, name):
    return all(image.getpixel(p) == ((c >> 16) & 255, (c >> 8) & 255, c & 255)
               for p, c in SCREENS[name].items())


def click(c, target):
    """Home the pointer to its top-left clamp, move it to target (screenshot pixels) and
    click the left mouse button; c is an amigaxdev.input.Input, the CPU stopped."""
    for _ in range(8):
        c.mouse(-64, -64)
    dx, dy = target[0] - HOME[0], target[1] - HOME[1]
    while dx or dy:
        sx, sy = max(-64, min(64, dx)), max(-64, min(64, dy))
        c.mouse(sx, sy)
        dx, dy = dx - sx, dy - sy
    c.fields(5)
    c.button('JOY1_FIRE_BUTTON', True)
    c.fields(5)
    c.button('JOY1_FIRE_BUTTON', False)


def quickrace(server, g, rest, destination="race"):
    """Boot to the first race field.  Fire is pressed while waiting for the language
    dialog, which skips the intro (or clicks its prompt) when CUSTOM1 is not set."""
    g.stop()
    # Field counts here and in race_profile/race_clock assume exact fields and gapless
    # profiles after a stop at a vsync.
    require_harness(g, 'key', 'fields', 'mouse', 'input', 'exact-fields', 'gapless-profile')
    log = open(rest, 'w') if rest else None
    elapsed = {'fields': 0}
    trail = []
    shots = os.environ.get('ROUTE_SHOTS')   # save every polled screenshot here
    if shots:
        os.makedirs(shots, exist_ok=True)

    def record(r):
        if r['command'].startswith('fields '):
            elapsed['fields'] += int(r['command'].split()[1])
        if log:
            log.write(json.dumps(r) + '\n')

    def wait_for(name, idle):
        for _ in range(LIMIT // POLL):
            image = screenshot(server, g)       # traces (runs) one field
            elapsed['fields'] += 1
            if shots:
                image.save(os.path.join(shots, f'{elapsed["fields"]:06d}-{name}.png'))
            if showing(image, name):
                trail.append(f'{name}@{elapsed["fields"]}')
                return
            idle()
        raise TimeoutError(f'no {name} screen after {LIMIT} fields; seen {trail}')

    def tap(c, key):
        c.key(key, True)
        c.fields(5)
        c.key(key, False)
        c.fields(5)

    try:
        with Input(g, log=record) as c:
            def fire():
                c.button('JOY1_FIRE_BUTTON', True)
                c.fields(POLL)
                c.button('JOY1_FIRE_BUTTON', False)
                c.fields(5)
            wait_for('language', fire)
            click(c, OK['language'])
            wait_for('protection', lambda: c.fields(POLL))
            tap(c, KEY_A)
            tap(c, KEY_RETURN)
            wait_for('startup', lambda: c.fields(POLL))
            if destination == 'startup':
                return ' '.join(trail) + ' (CPU stopped)'
            if destination in ('practice', 'qualifying'):
                click(c, (500, 275))
                click(c, OK['startup'])
                wait_for('main', lambda: c.fields(POLL))
                click(c, (395, 252 if destination == 'practice' else 290))
                wait_for('circuit', lambda: c.fields(POLL))
                click(c, (530, 246))
            else:
                click(c, OK['startup'])
            wait_for('track', lambda: c.fields(POLL))
            click(c, OK['track'])
            if destination == 'qualifying':
                wait_for('weekend', lambda: c.fields(POLL))
                click(c, (395, 252))
            wait_for('race', lambda: c.fields(POLL))
    finally:
        if log:
            log.close()
    return ' '.join(trail) + ' (fields since the command; CPU stopped)'


def menuclick(server, g, rest):
    x, y = map(int, rest.split())
    if not (HOME[0] <= x < 714 and HOME[1] <= y < 454):
        raise ValueError('target outside game screen')
    g.stop()
    with Input(g) as c:
        click(c, (x, y))
    return 'clicked; CPU stopped'


def tap_key(server, g, rest):
    args = rest.split()
    raw = int(args[0], 16)
    fields = int(args[1]) if len(args) == 2 else 25
    if len(args) not in (1, 2):
        raise ValueError('tap RAW [FIELDS]')
    g.stop()
    with Input(g) as c:
        c.key(raw, True)
        c.fields(fields)
        c.key(raw, False)
    return 'released; CPU stopped'


def raceprofile(server, g, rest):
    import race_profile
    return race_profile.raceprofile(server, g, rest)


def raceclock(server, g, rest):
    import race_clock
    return race_clock.raceclock(server, g, rest)


# Keep the CPU halted from reset until a command advances it (BOOT_BREAK is the shared
# server's): otherwise host timing decides how many fields run before the first command,
# and the race (its random elements included) differs from boot to boot.  $F800D6 is the
# second instruction of the Kickstart 3.1 reset code in both host ROMs.
os.environ.setdefault('BOOT_BREAK', '0xf800d6')
server = Server('f1gp', root=ROOT, profile_window=False,
                commands={'quickrace': quickrace, 'menuclick': menuclick, 'tap': tap_key,
                          'startup': lambda s, g, r: quickrace(s, g, r, 'startup'),
                          'practice': lambda s, g, r: quickrace(s, g, r, 'practice'),
                          'qualifying': lambda s, g, r: quickrace(s, g, r, 'qualifying'),
                          'raceprofile': raceprofile,
                          'raceclock': raceclock})

if __name__ == '__main__':
    server.main(sys.argv[1:])

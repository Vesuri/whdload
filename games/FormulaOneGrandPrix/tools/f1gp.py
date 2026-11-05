#!/usr/bin/env python3
"""Drive Formula One Grand Prix in FS-UAE through the Barto gdb stub.

  python3 tools/f1gp.py serve          boot (common/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/f1gp.py <command...>   send one command to the running server, print the reply

Commands are the shared server's (AmigaXDev amigaxdev.gdbserve): stop, cont, gdb <text>,
shot <png>, profile <fields> <bin> (PAL fields, Barto format), wait <s>, until <addr>, quit,
and:
  quickrace [log]    from boot, drive the menus into a Quick Race at Silverstone and stop
                     at the first race field; optional log file of every input sent.
                     ROUTE_SHOTS=dir (server environment) saves every polled screenshot.
                     A file whose settings skip the language screen and the startup menu
                     (F1GP-Ed's 1995-2002 datafiles) gets the shortest Non-Championship
                     race at Silverstone instead (Race Options distance 10%); with
                     F1GP_EDITED=1 the stop is the first field of any race view, whatever
                     the file's cockpit and palette
  startup [log]      boot to the startup menu, with the same screen checks
  practice [log]     Main Menu -> Practise any Circuit -> Silverstone -> cockpit
  qualifying [log]   Main Menu -> Non-Championship Race -> Silverstone -> Qualifying
  menuclick X Y      click a screenshot coordinate using the homed pointer
  tap RAW [FIELDS]   press a hexadecimal raw key for FIELDS (default 25), then release
  statediff live|replay DIR [FRAMES]
                     dump call-boundary state for complete drawn frames (default 50)
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
The run options of common/run.sh (SETUP, BUILD, SLAVE, WHD_ARGS, INSTANCE, ...) apply to
serve; without SLAVE it builds and boots the release slave, SLAVE=original boots
Codetapper's installed one.
"""
import io, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev import barto
from amigaxdev.gdbserve import require_harness
from amigaxdev.input import Input as SharedInput
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../common/tools'))
from game_server import game_server  # noqa: E402

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
    # F4: the Main Menu route of files whose settings skip the startup menu.
    'gameoptions': {(226, 160): 0xffffff, (271, 169): 0xffffff,     # title
                    (523, 181): 0xffffff},
    'raceoptions': {(270, 90): 0xffffff, (500, 131): 0xaa0000,      # title, practice field
                    (620, 131): 0xaa0000},
    'grid':       {(340, 438): 0xcc0000, (450, 438): 0xcc0000,      # Exit selected
                   (150, 438): 0x99aacc},
}
# Any race view, whatever the file's palette, cockpit and display position: one sky colour
# across the top band, unchanged over two polls (the menus' bands fade in and out).
LIVE = ((100, 58), (700, 58), (100, 70), (700, 70), (110, 64))
HOME = (74, 54)            # the pointer's top-left clamp
OK = {'language': (395, 358), 'startup': (395, 313), 'track': (235, 391),
      'times': (390, 252)}   # results menu: Race Finishing Times
KEY_A, KEY_RETURN = 0x20, 0x44
POLL = 25                  # fields between screen checks
LIMIT = 6000               # fields to wait for any one screen (two minutes of PAL)


class Input(SharedInput):
    """Allow slow cycle-exact machines longer field-command deadlines locally."""
    def __init__(self, g, log=None):
        class FieldDeadline:
            def cmd(self, command, timeout=30):
                if command.startswith('monitor fields '):
                    timeout = max(timeout, int(os.environ.get('F1GP_FIELD_TIMEOUT', '1800')))
                return g.cmd(command, timeout=timeout)
        super().__init__(FieldDeadline(), log=log)


def screenshot(server, g):
    target = os.path.join(server.run_dir, 'route.bin')
    # A disconnected debugger must never turn the previous picture into a new
    # successful field. This matters when diagnosing a stalled emulator.
    if os.path.exists(target):
        os.unlink(target)
    reply = g.cmd(f'monitor profile 1 "" "{target}"', timeout=1800)
    if not os.path.isfile(target):
        raise RuntimeError(f'screenshot profile produced no trace: {reply}')
    trace = barto.load(target)
    if len(trace.fields) != 1:
        raise RuntimeError('screenshot profile did not contain exactly one field')
    return Image.open(io.BytesIO(trace.fields[0].shot)).convert('RGB')


def sky(image, dy=0):
    colours = {image.getpixel((x, y+dy)) for x, y in LIVE}
    r, g, b = next(iter(colours))
    return colours.pop() if len(colours) == 1 and b > max(r, g) else None


def showing(image, name):
    # The pinned NTSC output places this same viewport ten pixels lower.
    # Mouse movement is relative to the home clamp, so click deltas stay unchanged.
    dy = int(os.environ.get('F1GP_SCREEN_Y', '0'))
    if name == 'live':
        return sky(image, dy) is not None and not showing(image, 'weekend')
    return all(0 <= p[1]+dy < image.height and image.getpixel((p[0], p[1]+dy)) == ((c >> 16) & 255, (c >> 8) & 255, c & 255)
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
    g.cmd(f'set remotetimeout {max(120, int(os.environ.get("F1GP_FIELD_TIMEOUT", "1800")))}')
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

    def wait_for(*names, idle):
        """Wait for the first of names; return it."""
        last = None
        for _ in range(LIMIT // POLL):
            image = screenshot(server, g)       # traces (runs) one field
            elapsed['fields'] += 1
            if shots:
                image.save(os.path.join(shots, f'{elapsed["fields"]:06d}-{"-".join(names)}.png'))
            for name in names:
                if showing(image, name) and (name != 'live' or sky(image) == last):
                    trail.append(f'{name}@{elapsed["fields"]}')
                    return name
            last = sky(image)
            idle()
        raise TimeoutError(f'no {"/".join(names)} screen after {LIMIT} fields; seen {trail}')

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
            wait = lambda: c.fields(POLL)
            # F1GP-Ed's settings can skip the language screen and the startup menu (F4).
            if wait_for('language', 'protection', idle=fire) == 'language':
                click(c, OK['language'])
                wait_for('protection', idle=wait)
            else:
                c.fields(100)   # seen while it is drawn, before it reads the keyboard
            tap(c, KEY_A)
            tap(c, KEY_RETURN)
            menu = wait_for('startup', 'main', idle=wait)
            if destination == 'startup':
                if menu != 'startup':
                    raise ValueError('this game file skips the startup menu')
                return ' '.join(trail) + ' (CPU stopped)'
            if destination in ('practice', 'qualifying'):
                if menu == 'startup':
                    click(c, (500, 275))
                    click(c, OK['startup'])
                    wait_for('main', idle=wait)
                click(c, (395, 252 if destination == 'practice' else 290))
                wait_for('circuit', idle=wait)
                click(c, (530, 246))
            elif menu == 'startup':
                click(c, OK['startup'])
            else:
                # No Quick Race: the shortest Non-Championship race at Silverstone, its
                # distance held down to the 10% minimum in Race Options.
                click(c, (395, 371))
                wait_for('gameoptions', idle=wait)
                click(c, (395, 257))
                wait_for('raceoptions', idle=wait)
                click(c, (476, 212))
                c.button('JOY1_FIRE_BUTTON', True)
                c.fields(600)           # 1% each 5 fields, from at most 100%
                c.button('JOY1_FIRE_BUTTON', False)
                click(c, (395, 415))
                wait_for('gameoptions', idle=wait)
                click(c, (395, 337))
                wait_for('main', idle=wait)
                click(c, (395, 290))
                wait_for('circuit', idle=wait)
                click(c, (530, 246))
            wait_for('track', idle=wait)
            click(c, OK['track'])
            if destination == 'qualifying' or menu == 'main' and destination == 'race':
                wait_for('weekend', idle=wait)
                click(c, (395, 252 if destination == 'qualifying' else 331))
            if menu == 'main' and destination == 'race':
                wait_for('grid', idle=wait)
                click(c, (395, 438))
            wait_for('live' if os.environ.get('F1GP_EDITED') else 'race', idle=wait)
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


def statediff(server, g, rest):
    import state_diff
    return state_diff.capture(server, g, rest)


def raceclock(server, g, rest):
    import race_clock
    return race_clock.raceclock(server, g, rest)


# Keep the CPU halted from reset until a command advances it (BOOT_BREAK is the shared
# server's): otherwise host timing decides how many fields run before the first command,
# and the race (its random elements included) differs from boot to boot.  $F800D6 is the
# second instruction of the Kickstart 3.1 reset code in both host ROMs.
os.environ.setdefault('BOOT_BREAK', '0xf800d6')
# This game, whatever the caller's GAME: the tool may be started from anywhere.
os.environ['GAME'] = os.path.basename(ROOT)
server = game_server('f1gp', profile_window=False,
                     commands={'quickrace': quickrace, 'menuclick': menuclick, 'tap': tap_key,
                               'startup': lambda s, g, r: quickrace(s, g, r, 'startup'),
                               'practice': lambda s, g, r: quickrace(s, g, r, 'practice'),
                               'qualifying': lambda s, g, r: quickrace(s, g, r, 'qualifying'),
                               'raceprofile': raceprofile,
                               'raceclock': raceclock, 'statediff': statediff})

if __name__ == '__main__':
    server.main(sys.argv[1:])

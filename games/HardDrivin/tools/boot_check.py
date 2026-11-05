"""Boot a release slave from the game's entry and sample where it runs, with screenshots.

boot_check.py SLAVE NAME [--profile P] [--custom1 N] [--swaps N]   (output tmp/prof/NAME)
"""
import argparse, os, re, shutil, sys
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from capture_demo import ROOT, command      # noqa: E402
from capture_session import Session         # noqa: E402

p = argparse.ArgumentParser()
p.add_argument('slave', type=Path); p.add_argument('name')
p.add_argument('--profile', default='a500'); p.add_argument('--custom1', type=int, default=2)
p.add_argument('--swaps', type=int, default=300)
a = p.parse_args(); os.chdir(ROOT)
out = ROOT / 'tmp/prof' / a.name; out.mkdir(exist_ok=False)
shutil.copyfile(a.slave.resolve(), out / 'slave.slave')
s = Session(out, a.profile, out / 'slave.slave', 0)
s.env['WHD_ARGS'] += ' CUSTOM1=%d' % a.custom1
try:
    s.start(tag='run'); layout = None
    for _ in range(20):
        command('wait 1'); command('stop')
        try:
            layout = s.locate(s.dump_banks('run')); break
        except (AssertionError, ValueError):
            command('cont')
    assert layout, 'live game not found'
    code = layout['code_base']; size = layout['regions'][0]['size']
    for i in range(4):
        command('cont'); command('wait 15'); command('stop')
        pc = int(re.search(r'pc\s+0x([0-9a-f]+)', command('gdb info registers pc')).group(1), 16)
        where = 'game +%x' % (pc - code) if code <= pc < code + size else 'outside the game: %x' % pc
        command('shot %s/shot%d.png' % (s.rel, i))
        print(a.name, 'after %d s:' % (15 * (i + 1)), where, flush=True)
finally:
    s.close()

"""Run a feel plan (build_feel.py) to a record count, then look at the machine.

hang_probe.py OUT --plan NAME --custom1 N --records R [--gdb FILE] [--samples S] [--prefix P]

OUT is a new directory below tmp/prof. Boots tmp/build/feel-NAME.slave like
capture_feel.py and continues to the first record flush at or past R. Then
runs the gdb commands in FILE, if given, as one command (breakpoints,
loops, stepi traces; $sig is the fixture's signature, $code the game's
code base; --timeout limits it), and S times lets the emulator run 2 s, stops it and saves the
registers and the next instructions. OUT/samples.txt holds the replies,
OUT/hang-code.bin and hang-data.bin the game's hunks at the end.
"""
import argparse, os, shutil, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_demo import ROOT, command
from capture_session import Session

a = argparse.ArgumentParser()
a.add_argument('out'); a.add_argument('--plan'); a.add_argument('--custom1', type=int)
a.add_argument('--records', type=int); a.add_argument('--samples', type=int, default=150); a.add_argument('--gdb'); a.add_argument('--timeout', type=int, default=300); a.add_argument('--prefix', default='feel-')
a = a.parse_args()
os.chdir(ROOT)
out = (ROOT / a.out).resolve(); out.mkdir(parents=True, exist_ok=False)
shutil.copyfile(ROOT / 'tmp/build' / ('%s%s.slave' % (a.prefix, a.plan)), out / 'slave.slave')
s = Session(out, 'a500', out / 'slave.slave', 0x10ed4)
s.env['WHD_ARGS'] += ' CUSTOM1=%d' % a.custom1
try:
    layout = s.boot()
    print('code_base %#x a4 %#x' % (layout['code_base'], layout['a4']), flush=True)
    hits = []
    for bank, b in s.dump_banks('anchor'):
        for tag, n in ((b'HDFEEL02', 5), (b'HDFEEL03', 6)):
            i = b.find(tag)
            while i >= 0:
                hits.append((bank + i, struct.unpack_from('>%di' % n, b, i + 8)))
                i = b.find(tag, i + 1)
    sig, offsets = hits[0]
    state, vbuf, pbuf, flush_rec, flush_steps = (sig + o for o in offsets[:5])
    print(command('\n'.join([
        'gdb break *%#x' % flush_rec, 'break *%#x' % flush_steps, 'set $n=0',
        'while $n < %d' % a.records, 'continue',
        'if $pc == %#x' % flush_rec, 'set $n=$n+(*(unsigned short*)%#x)' % (state + 34), 'end', 'end',
        'printf "records %d\\n", $n', 'delete']), timeout=900), flush=True)
    lines = []
    if a.gdb:
        lines.append(command('gdb set $sig=%#x\nset $code=%#x\n' % (sig, layout['code_base']) + open(a.gdb).read(), timeout=a.timeout))
    for k in range(a.samples):
        command('cont'); command('wait 2'); command('stop')
        lines.append(command('gdb info registers'))
        lines.append(command('gdb x/12i $pc'))
    command('gdb dump binary memory %s/hang-data.bin %#x %#x' % (out.relative_to(ROOT), layout['data_base'], layout['data_base'] + 31948))
    command('gdb dump binary memory %s/hang-code.bin %#x %#x' % (out.relative_to(ROOT), layout['code_base'], layout['code_base'] + 77116))
    (out / 'samples.txt').write_text('\n'.join(lines))
finally:
    s.close()

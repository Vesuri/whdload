#!/usr/bin/env python3
"""Drive a native (CUSTOM2=0) run through a qualifying race to the bike shop.

  python3 tools/shop_route.py OUT

Builds OUT/shop-test.Slave from src/ with a test-only keyboard hook that never ships:
keypad * moves the player to 2 segments before the finish (keypad / moves it 2 segments
on; large jumps skip the native passing logic, so the rank does not change). The route
starts the race, jumps to the finish, waits on the results screen, presses F3 there
("check out new bikes", whatever the rank) and steps right through two bikes, with
screenshots and Barto traces in OUT/run. The actor addresses are the native ones, so
Enhanced framerate (CUSTOM2=1, relocated actors) is not supported.

With the blitter-sync observer (tools/patches/fsuae-blitsync.patch) as FSUAE and
BLITSYNC_LOG=FILE it records every unsynchronised blit on the way (tools/blitsync.py).
Other environment: AMIGA_SETUP (default a1200-fast; 020 traces carry blitter DMA).
"""
import os
import re
import shlex
import shutil
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drive import Session, rd  # noqa: E402
from harness_a import read_bytes  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HOOK = """.noquit
	cmp.b	#$5c,D0			; test only: keypad / moves the player 2 segments on
	bne	.nojump
	add.l	#2<<16,$a5d64
	add.l	#2<<16,$a5d1e
	bra	.noteleport
.nojump
	cmp.b	#$5d,D0			; test only: keypad * moves the player near the finish
	bne	.noteleport
	movem.l	d1,-(a7)
	moveq	#0,d1
	move.w	$947fc,d1
	subq.w	#2,d1
	swap	d1
	move.l	d1,$a5d64
	move.l	d1,$a5d1e
	movem.l	(a7)+,d1
.noteleport
	move.l	(sp)+,D0
	rts
"""


def build_test_slave(out):
    src = out / 'shop-src'
    shutil.rmtree(src, ignore_errors=True)
    shutil.copytree(ROOT / 'src', src)
    main = src / 'RoadRashHD.s'
    text = main.read_text()
    native = re.search(r'\.noquit\n\tmove\.l\t\(sp\)\+,D0\n\trts\t*\n', text)
    if not native:
        raise RuntimeError('kbint exit not found in src/RoadRashHD.s')
    main.write_text(text[:native.start()] + HOOK + text[native.end():])
    conf = dict(re.findall(r'^(\w+)="([^"]*)"', (ROOT / 'game.conf').read_text(), re.M))
    env_sh = ROOT.parents[1] / 'common/env.sh'
    slave = out / 'shop-test.Slave'
    cmd = (f'. {shlex.quote(str(env_sh))} && "$VASM" {conf["VASM_FLAGS"]} -I{shlex.quote(str(src))} '
           '-I"$AMIGA_INCLUDE" -I"$WHDLOAD/Include" -I"$WHDLOAD/Src/sources" -I"${NDK:-$AMIGA_SHARE/ndk/Include_I}" '
           f'-quiet -o {shlex.quote(str(slave))} {shlex.quote(str(main))}')
    subprocess.run(['bash', '-c', cmd], check=True)
    return slave


def route(s):
    held = {}

    def want(k, v):
        if held.get(k, 0) != v:
            s.input(k, v)
            held[k] = v

    def key(code, hold=5):
        s.cmd(f'monitor key {code:x} 1')
        s.fields(hold)
        s.cmd(f'monitor key {code:x} 0')

    def trace(name, n=99):
        p = s.out / name
        s.cmd(f'monitor profile {n} "" "{p}"', timeout=1800)
        s.field += n
        print('trace', name, 'at', s.field, flush=True)

    while rd(s, 0xa5916) != 0x87040:          # the native race's per-field hook
        if s.field > 8000:
            raise RuntimeError('race not reached')
        s.press('JOY2_FIRE_BUTTON')
        s.fields(95)
    s.input('JOY2_UP', 1)
    s.fields(2)
    key(0x5d)
    s.input('JOY2_UP', 0)
    while rd(s, 0xa5916) == 0x87040:
        crash = struct.unpack('>b', read_bytes(s, 0xa5dce, 1))[0]
        lateral = struct.unpack('>h', read_bytes(s, 0xa5d90, 2))[0]
        riding = crash < 0 and not rd(s, 0xa5980, 2)
        want('JOY2_UP', int(riding))
        want('JOY2_LEFT', int(riding and lateral > 64))
        want('JOY2_RIGHT', int(riding and lateral < -64))
        s.fields(20)
    for k in list(held):
        want(k, 0)
    print('race ended at field', s.field, flush=True)
    s.fields(500)
    s.shot('1-results.png')
    key(0x52)                                  # F3: check out new bikes
    for i in range(3):
        trace(f'shop-enter-{i + 1}.bin')
    s.shot('2-shop.png')
    for i in range(2):
        s.input('JOY2_RIGHT', 1)
        trace(f'shop-right-{i + 1}a.bin', 30)
        s.input('JOY2_RIGHT', 0)
        trace(f'shop-right-{i + 1}b.bin')
        s.shot(f'{3 + i}-shop-right.png')


if __name__ == '__main__':
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    os.environ['SLAVE'] = str(build_test_slave(out))
    os.environ.setdefault('AMIGA_SETUP', 'a1200-fast')
    os.environ['WHD_ARGS'] = 'CUSTOM2=0'
    s = Session(out / 'run')
    try:
        route(s)
    finally:
        s.quit()

#!/usr/bin/env python3
"""Follow one VERIFY game from SOL through native transitions to the ending (step 8).

Usage: SETUP=<machine> INSTANCE=<name> VERIFY_FLAGS='...' tools/campaign.py tmp/<out> [--sample 300]

The build supplies the input-only pilot (APPROACH_*, POWER_*) and DEATH_TEST=1
DEATH_NATURAL=1 DEATH_RETRY=1, which answers Yes to every natural death's Continue
and OK to the Hall of Fame name entry.
Nothing else is injected: waves, health and inventory stay native.

Read-only breakpoints log native events with the completed SIM60 tick and session:
  H  any damage to the boss (type 44, or 45 for the level 1 boss's other form) at $3f04 entry (health before, damage, caller)
  K  actor killed: $3f20, after $3f04's health test (type, health, damage, caller)
  P  player damage entry $3cc2 (damage, energy, shield/cloak timers, caller)
  B  boss-helper damage stubs $116c6 (player) / $116cc (actor), with the helper caller
  X  native exit collision $3610 (level index before the native advance)
  D  natural death flag write $2ce0;  E  ending entry $2ebc;  the run stops at $2ec0
  O  native death handling at $2dae (level, Continues left: 2 minus difficulty per game)
  G  game over at $2ec8 (no Continue left);  N  Hall of Fame name entry $6554
  L  native landing notification $e948 (level, player x, z, height, argument; 2 = landing)
After a game over the menu's Begin restarts level 0 and the fixture requests native
exits back to the highest level reached (DEATH_RETRY's GO60 record).
Every --sample completed ticks a compact sample records level, energy, score,
inventory, power timers and the active actors. Writes events.txt, samples.json
and, at the end, the exact slave and the final memory dump for the ABI readers.
Create OUT/stop to finish cleanly at the next sample.
"""
import argparse
import json
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import sys
import time

from stellar7 import SOCK
import machines
from stellar7_report import loaded_game_regions

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('out', type=Path)
p.add_argument('--sample', type=int, default=300, help='completed ticks between samples')
p.add_argument('--max-sessions', type=int, default=60, help='give up after this many game sessions')
p.add_argument('--max-session-ticks', type=int, default=90000, help='give up when one session runs this long')
p.add_argument('--watchdog', type=int, default=3600, help='fields without a sample before a screenshot/state dump')
p.add_argument('--max-stalls', type=int, default=3, help='watchdog stops in a row before giving up')
p.add_argument('--boot-timeout', type=float, default=1800)
p.add_argument('--level', type=int, help='per-level run: finish once this level is left '
               '(build with -DCAMPAIGN_START=LEVEL)')
a = p.parse_args()
root = Path(__file__).resolve().parent.parent
os.chdir(root)
out = a.out.resolve()
out.relative_to(root/'tmp')
if out.exists() and any(out.iterdir()):
    p.error('capture directory is not empty')
out.mkdir(parents=True, exist_ok=True)
flags = os.environ.get('VERIFY_FLAGS', '')
for need in ('-DDEATH_RETRY=1', '-DDEATH_NATURAL=1', '-DDEATH_TEST=1', '-DAPPROACH_TYPE=0'):
    if need not in flags.split():
        p.error(f'VERIFY_FLAGS needs {need}')


def cmd(text, timeout=1200):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(timeout)
        s.connect(SOCK)
        s.sendall(text.encode())
        reply = b''
        while part := s.recv(65536):
            reply += part
    result = reply.decode()
    if 'ERROR' in result:
        raise RuntimeError(result)
    return result


try:
    cmd('quit', 5)
except (OSError, RuntimeError):
    pass
# A build directory of its own, so a campaign can run in its own INSTANCE beside other captures.
build = 'campaign_'+re.sub(r'[^a-zA-Z0-9]', '_', out.name)
subprocess.run(['make', '-s', 'build', 'BUILD='+build, 'VARIANT=Stellar7'], check=True,
               env=dict(os.environ, **{'DEFINES_'+build: '-DVERIFY=1 '+flags}))
(out/'slave.slave').write_bytes(Path(f'tmp/build/{build}/Stellar7.Slave').read_bytes())
(out/'slave.lst').write_bytes(Path(f'tmp/build/{build}/Stellar7.lst').read_bytes())
env = dict(os.environ, SLAVE=str(out/'slave.slave'), WHD_ARGS='CUSTOM5=1 '+os.environ.get('WHD_ARGS', ''),
           JOY0='none', JOY1='none', DETERMINISTIC='1', WARP='1')
os.environ['SLAVE'] = env['SLAVE']
setup = machines.effective(env)
if not setup:
    p.error('campaign runs need a named SETUP')
for key in machines.SETTINGS:
    env.pop(key, None)
env.pop('AMIGA_SETUP', None)
env['SETUP'] = setup
machine = machines.resolve(setup)
chip, fast, slow = machine['chip_kb'], machine['fast_kb'], machine['slow_kb']
base = 0x200000 if fast else 0xc00000 if slow else 0
size = (fast or slow or chip)*1024
log = (out/'serve.log').open('w')
server = subprocess.Popen([sys.executable, 'tools/stellar7.py', 'serve'], stdout=log, stderr=subprocess.STDOUT, env=env)


def dump(destination):
    destination.mkdir(parents=True, exist_ok=True)
    code = str((destination/'code.bin').relative_to(root))
    chipfile = str((destination/'chip.bin').relative_to(root))
    cmd(f'gdb dump binary memory {code} {base:#x} {base+size:#x}\ndump binary memory {chipfile} 0 {chip*1024:#x}')
    return (destination/'code.bin').read_bytes(), (destination/'chip.bin').read_bytes()


BOSSES = (44, 45)  # the level 1 boss switches between types 44 and 45 ($10e60)
EVENTS = (
    ('K', 0x3f20, '"K %u %u %d %d %d %#x\\n", *(unsigned int*)$S, *(unsigned int*)$T, '
                  '*(short*)($a3+2), *(signed char*)($a3+0x55), $d7, *(unsigned int*)($sp+12)-$C'),
    ('H', 0x3f04, '"H %u %u %d %d %d %#x\\n", *(unsigned int*)$S, *(unsigned int*)$T, *(short*)(*(unsigned int*)($sp+4)+2), '
                  '*(signed char*)(*(unsigned int*)($sp+4)+0x55), *(short*)($sp+8), *(unsigned int*)$sp-$C'),
    ('P', 0x3cc2, '"P %u %u %d %d %d %d %#x\\n", *(unsigned int*)$S, *(unsigned int*)$T, '
                  '*(short*)($sp+4), *(short*)($D+0x46c4), *(short*)($D+0x1e9e), *(short*)($D+0x1ea4), *(unsigned int*)$sp-$C'),
    ('B', 0x116c6, '"B %u %u player %#x\\n", *(unsigned int*)$S, *(unsigned int*)$T, *(unsigned int*)$sp-$C'),
    ('B', 0x116cc, '"B %u %u actor %#x %d\\n", *(unsigned int*)$S, *(unsigned int*)$T, *(unsigned int*)$sp-$C, '
                   '*(short*)(*(unsigned int*)($sp+4)+2)'),
    ('X', 0x3610, '"X %u %u %d\\n", *(unsigned int*)$S, *(unsigned int*)$T, *(short*)($D+0x46a0)'),
    ('D', 0x2ce0, '"D %u %u %d %d\\n", *(unsigned int*)$S, *(unsigned int*)$T, *(short*)($D+0x46a0), *(short*)($D+0x46c4)'),
    ('E', 0x2ebc, '"E %u %u %d\\n", *(unsigned int*)$S, *(unsigned int*)$T, *(short*)($D+0x46a0)'),
    ('O', 0x2dae, '"O %u %u %d %d\\n", *(unsigned int*)$S, *(unsigned int*)$T, *(short*)($D+0x46a0), *(short*)($a5-12)'),
    ('G', 0x2ec8, '"G %u %u %d\\n", *(unsigned int*)$S, *(unsigned int*)$T, *(short*)($D+0x46a0)'),
    ('N', 0x6554, '"N %u %u %d\\n", *(unsigned int*)$S, *(unsigned int*)$T, *(short*)($D+0x46a0)'),
    ('L', 0xe948, '"L %u %u %d %d %d %d %d\\n", *(unsigned int*)$S, *(unsigned int*)$T, *(short*)($D+0x46a0), '
                  '*(int*)(*(unsigned int*)($D+0x43c0)+8), *(int*)(*(unsigned int*)($D+0x43c0)+12), '
                  '*(int*)(*(unsigned int*)($D+0x43c0)+16), *(short*)($sp+4)'),
)
ACTOR_LIST = '''set $i = 0
printf "S %u %u %d %d %d %d %d\\n", *(unsigned int*)$S, *(unsigned int*)$T, *(short*)($D+0x46a0), *(short*)($D+0x46c4), *(int*)($D+0x46c8), *(unsigned char*)($D+0x1e53), *(short*)($D+0x1e90)
printf "I %02x %02x %02x %02x %02x %02x %02x\\n", *(unsigned char*)($D+0x20f8), *(unsigned char*)($D+0x20f9), *(unsigned char*)($D+0x20fa), *(unsigned char*)($D+0x20fb), *(unsigned char*)($D+0x20fc), *(unsigned char*)($D+0x20fd), *(unsigned char*)($D+0x20fe)
printf "T %d %d %d %d %d %d %d\\n", *(short*)($D+0x1e9c), *(short*)($D+0x1e9e), *(short*)($D+0x1ea0), *(short*)($D+0x1ea2), *(short*)($D+0x1ea4), *(short*)($D+0x1ea6), *(short*)($D+0x1ea8)
while $i < *(short*)($D+0x43b2) && $i < 64
set $o = *(unsigned int*)($D+0x3fb2+4*$i)
printf "A %d %d %d\\n", *(short*)($o+2), *(signed char*)($o+0x55), *(int*)($o+0x50)
set $i = $i + 1
end'''

started = time.monotonic()
try:
    deadline = time.monotonic()+120
    while 'serving on' not in (out/'serve.log').read_text():
        if server.poll() is not None:
            raise RuntimeError((out/'serve.log').read_text())
        if time.monotonic() > deadline:
            raise TimeoutError('server startup')
        time.sleep(.2)
    boot_deadline = time.monotonic()+a.boot_timeout
    while time.monotonic() < boot_deadline:
        cmd('wait 0.1')
        cmd('stop')
        mem, ch = dump(out/'boot')
        try:
            r = {n: lo for lo, hi, n, o in loaded_game_regions(mem, base, ch)}
        except ValueError:
            continue
        if 's7' not in r:
            continue
        hook = mem[r['s7']-base+0x2af6:r['s7']-base+0x2afc]
        if hook[:2] != bytes.fromhex('4ef9'):
            continue
        entry = struct.unpack_from('>I', hook, 2)[0]
        if mem[entry-base+4:entry-base+8] == b'S760':
            break
    else:
        raise TimeoutError('SIM60 game not ready')
    code, data = r['s7'], r['s7-data']
    anchor = entry+struct.unpack_from('>H', mem, entry-base+44)[0]
    ticks, session = entry+16, entry+100
    setvars = f'set $C = {code:#x}\nset $D = {data:#x}\nset $T = {ticks:#x}\nset $S = {session:#x}'
    lines = [setvars, 'delete']
    for kind, offset, fmt in EVENTS:
        lines += [f'break *{code+offset:#x}', 'commands', 'silent', f'printf {fmt}', 'continue', 'end']
        if kind == 'H':  # boss damage only: every call, so its health before the first hit shows
            boss_type = '*(short*)(*(unsigned int*)($sp+4)+2)'
            lines.append(f'condition $bpnum {boss_type} == {BOSSES[0]} || {boss_type} == {BOSSES[1]}')
    lines.append(f'break *{code+0x2ec0:#x}')
    lines += [f'break *{anchor:#x}', f'condition $bpnum *(unsigned int*){ticks:#x} % {a.sample} == 0']
    # Watchdog: the slave's field callback stops the run after --watchdog fields without a sample.
    symbols = (out/'slave.lst').read_text(encoding='latin1')
    symbol = lambda name: int(re.search(r'^'+name+r'\s+00:([0-9A-F]+)', symbols, re.M)[1], 16)
    watch = entry+symbol('s60_history_field')-symbol('s60_entry')
    field = data+0x24a8
    lines += [f'break *{watch:#x}', f'condition $bpnum *(unsigned int*){field:#x} >= $limit']
    reply = cmd('gdb '+'\n'.join(lines))
    (out/'breakpoints.txt').write_text(reply)
    events, samples = (out/'events.txt').open('w'), []
    finished, last, stalls, stalled_at = None, None, 0, None
    while finished is None:
        reply = cmd(f'gdb set $limit = *(unsigned int*){field:#x} + {a.watchdog}\ncontinue', timeout=3600)
        for line in reply.splitlines():
            if re.match(r'^[HKPBXDEOGNL] ', line):
                events.write(line+'\n')
        events.flush()
        pc = re.findall(r'^Breakpoint \d+, (0x[0-9a-f]+)', reply, re.M)
        if pc and int(pc[-1], 16) == code+0x2ec0:
            finished = 'ending returned'
            break
        if pc and int(pc[-1], 16) == watch:
            if not samples:  # still in the intro and menus before the first gameplay sample
                continue
            # Short sessions (native return exits) end before a sample tick; only a
            # watchdog stop without any session or tick progress counts towards giving up.
            where = re.search(r'^W (\d+) (\d+)$', cmd(f'gdb printf "W %u %u\\n", *(unsigned int*){session:#x}, '
                                                    f'*(unsigned int*){ticks:#x}'), re.M)
            where = where and where.groups()
            if stalls and where != stalled_at:
                stalls = 0
            stalled_at = where
            stalls += 1
            try:
                cmd(f'shot {out}/stall-{stalls}.png')
            except RuntimeError as e:  # the screenshot's one-field trace can come back empty
                print(f'stall-{stalls}: no screenshot ({str(e).strip()[:80]})', flush=True)
            dump(out/f'stall-{stalls}')
            (out/f'stall-{stalls}'/'anchor.txt').write_text(f'code={code:#x}\ndata={data:#x}\nbase={base:#x}\n')
            print(f'no sample for {a.watchdog} fields: stall-{stalls}', flush=True)
            events.write(f'W {stalls}\n')
            if stalls >= a.max_stalls:
                finished = 'stalled'
            continue
        if 'SIGINT' in reply or not pc or int(pc[-1], 16) != anchor:
            raise RuntimeError('unexpected stop: '+reply[-500:])
        stalls = 0
        for attempt in range(3):  # a reply can rarely come back without the printf output
            state = cmd('gdb '+setvars+'\n'+ACTOR_LIST)
            s = re.search(r'^S (\d+) (\d+) (-?\d+) (-?\d+) (-?\d+) (\d+) (-?\d+)$', state, re.M)
            if s and re.search(r'^T ', state, re.M):
                break
            (out/f'bad-sample-{len(samples)}-{attempt}.txt').write_text(state)
            print(f'sample {len(samples)}: incomplete reply, retrying', flush=True)
        else:
            continue
        sample = dict(zip(('session', 'tick', 'level', 'energy', 'score', 'active', 'death'), map(int, s.groups())))
        sample['inventory'] = re.search(r'^I (.*)$', state, re.M)[1].replace(' ', '')
        sample['timers'] = list(map(int, re.search(r'^T (.*)$', state, re.M)[1].split()))
        sample['actors'] = [list(map(int, x)) for x in re.findall(r'^A (-?\d+) (-?\d+) (-?\d+)$', state, re.M)]
        sample['elapsed_s'] = round(time.monotonic()-started)
        samples.append(sample)
        if last != (sample['session'], sample['level']):
            print(f"session {sample['session']} level {sample['level']} tick {sample['tick']} energy {sample['energy']}"
                  f" score {sample['score']} after {sample['elapsed_s']} s", flush=True)
            last = (sample['session'], sample['level'])
        (out/'samples.json').write_text(json.dumps(samples)+'\n')
        if (out/'stop').exists():
            finished = 'stop requested'
        elif a.level is not None and sample['level'] > a.level:
            finished = 'level left'
        elif sample['session'] > a.max_sessions:
            finished = 'session limit'
        elif sample['tick'] >= a.max_session_ticks:
            finished = 'session tick limit'
    events.close()
    cmd('gdb delete')
    mem, ch = dump(out)
    (out/'anchor.txt').write_text(f'code={code:#x}\ndata={data:#x}\nbase={base:#x}\n')
    (out/'state.bin').write_bytes(mem[data-base:data-base+0x823c])
    meta = dict(setup=setup, setup_args=machine['args'], verify_flags=flags, whd_args=env['WHD_ARGS'],
                extra_args=env.get('EXTRA_ARGS', ''), sample=a.sample, finished=finished,
                elapsed_s=round(time.monotonic()-started), code_base=code, data_base=data, base=base)
    (out/'metadata.json').write_text(json.dumps(meta, indent=2)+'\n')
    print('Finished:', finished, flush=True)
finally:
    try:
        cmd('quit', 5)
    except (OSError, RuntimeError):
        pass
    try:
        server.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server.terminate()
    log.close()

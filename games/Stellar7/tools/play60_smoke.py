#!/usr/bin/env python3
"""Launcher check (open-work step 9): boot the real tools/play60.sh (release build, default
CUSTOM1=1) on one machine; confirm the selected slave matches the audited release build, its
hooks are installed, CUSTOM1=1 reaches WHDLoad and the native menu is reached.
Usage: tools/play60_smoke.py SETUP BUILDS OUT
  BUILDS  a baseline_checks.py builds folder (its VARIANT.slave/.lst are the audited builds)
  OUT     new folder under tmp/; writes OUT/validation.json
Warp, silent and disconnected inputs: no gameplay or audible-output claim."""
import fcntl, json, os, socket, struct, subprocess, sys, time
from pathlib import Path
root = Path(__file__).resolve().parents[1]
os.chdir(root)
sys.path.insert(0, str(root/'tools'))
import _amigaxdev  # noqa: F401
import machines, audit_hooks, sim60_state
from stellar7_report import loaded_game_regions
from amigaxdev import barto

setup = sys.argv[1]
machine = machines.resolve(setup)
variant = 'Stellar7-Sim68000' if machine['cpu'] in ('68000', '68010') else 'Stellar7-Sim60'
n = 3 if variant == 'Stellar7-Sim68000' else 12
builds = Path(sys.argv[2]).resolve()
out = Path(sys.argv[3]).resolve()
out.relative_to(root/'tmp')
out.mkdir(parents=True, exist_ok=False)
INSTANCE = 'smoke'
RUN = root/'tmp/run'/INSTANCE/'.run'
SOCK = str(RUN/'stellar7.sock')

def cmd(text, timeout=900):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(timeout); s.connect(SOCK); s.sendall(text.encode()); reply = b''
        while part := s.recv(65536): reply += part
    result = reply.decode()
    if 'ERROR' in result: raise RuntimeError(result)
    return result

fast, slow, chip = machine['fast_kb'], machine['slow_kb'], machine['chip_kb']
base = 0x200000 if fast else 0xc00000 if slow else 0
size = (fast or slow or chip)*1024
def dump():
    code = str((out/'code.bin').relative_to(root)); cb = str((out/'chip.bin').relative_to(root))
    cmd(f'gdb dump binary memory {code} {base:#x} {base+size:#x}\ndump binary memory {cb} 0 {chip*1024:#x}')
    return (out/'code.bin').read_bytes(), (out/'chip.bin').read_bytes()

env = {k: v for k, v in os.environ.items() if k not in
       ('WHD_ARGS', 'VERIFY_FLAGS', 'VASM_EXTRA', 'SIM68000_SUBSTEPS', 'SLAVE', 'VARIANT', 'BUILD', 'EXTRA_ARGS', 'AMIGA_SETUP',
        *machines.SETTINGS)}
env.update(SETUP=setup, INSTANCE=INSTANCE, WARP='1', SOUND='0', JOY0='none', JOY1='none', DETERMINISTIC='1', WINDOW='none')
serve = ("import sys; sys.argv[0]='tools/stellar7.py'; sys.path.insert(0,'tools'); import stellar7; "
         "stellar7.server.run_script='"+str(root/'tools/play60.sh')+"'; stellar7.server.main(['serve'])")
with (root/'tmp/rate-matrix.lock').open('a') as lock:
    print('Waiting for the capture lock', flush=True)
    fcntl.flock(lock, fcntl.LOCK_EX)
    log = (out/'serve.log').open('w')
    server = subprocess.Popen([sys.executable, '-c', serve], stdout=log, stderr=subprocess.STDOUT, env=env)
    try:
        deadline = time.monotonic()+300
        while 'serving on' not in (out/'serve.log').read_text():
            if server.poll() is not None: raise RuntimeError((out/'serve.log').read_text())
            if time.monotonic() > deadline: raise TimeoutError('server startup')
            time.sleep(.2)
        built = root/'tmp/build/release'/(variant+'.Slave')
        (out/'slave.slave').write_bytes(built.read_bytes())
        release_matches = built.read_bytes() == (builds/(variant+'.slave')).read_bytes()
        assert release_matches, 'play60 build differs from the audited release build'
        listing = builds/(variant+'.lst')
        deadline = time.monotonic()+1800
        while time.monotonic() < deadline:
            cmd('wait 0.1'); cmd('stop'); mem, ch = dump()
            try:
                r = {name: lo for lo, hi, name, o in loaded_game_regions(mem, base, ch)}
                h, data = r['s7'], r['s7-data']
                (out/'anchor.txt').write_text(f'code={h:#x}\ndata={data:#x}\nbase={base:#x}\n')
                audit_hooks.installed(out, listing)
            except (KeyError, ValueError, AssertionError):
                cmd('cont'); continue
            break
        else:
            raise RuntimeError('release hooks not installed during boot')
        print('Release hooks installed; waiting for the native menu', flush=True)
        reply = cmd(f'gdb break *{h+0x4582:#x}\ncontinue\ndelete', timeout=900)
        mem, ch = dump()
        (out/'anchor.txt').write_text(reply+f'\ncode={h:#x}\ndata={data:#x}\nbase={base:#x}\n')
        assert mem[h-base+0x4582:h-base+0x4588] == bytes.fromhex('4eba64ca2e00'), 'not at the native menu call'
        for offset, expected in [(0xb1f4, '4eba56847245'), (0xb8c4, '4eba4fb47245')]:
            assert mem[h-base+offset:h-base+offset+6] == bytes.fromhex(expected), 'menu fixture present'
        installed = audit_hooks.installed(out, listing)
        cmd('gdb monitor profile 1 "" "'+str(out/'screen.bin')+'"', timeout=300)
        field = barto.load(out/'screen.bin').fields[-1]
        (out/'menu.png').write_bytes(field.shot)
        assert sim60_state.read(out)['substeps'] == n
        startup = (RUN/'dh0/S/startup-sequence').read_text(encoding='latin1')
        (out/'startup-sequence').write_text(startup)
        whdload = [l for l in startup.splitlines() if l.startswith('WHDLoad ')]
        assert len(whdload) == 1 and 'CUSTOM1=1' in whdload[0].split(), whdload
        result = dict(setup=setup, variant=variant, substeps=n, installed=installed, native_menu_reached=True,
                      menu_fixture_absent=True, release_matches_audited=release_matches,
                      whdload_command=whdload[0],
                      scope='Actual play60 launcher, default CUSTOM1; warp, silent, disconnected inputs. No gameplay or audible-output claim.')
        (out/'validation.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result), flush=True)
    finally:
        try: cmd('quit', 30)
        except (OSError, RuntimeError): pass
        server.wait(60)

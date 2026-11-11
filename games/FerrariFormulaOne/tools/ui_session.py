#!/usr/bin/env python3
"""An interactive game session on $FSUAE_ARM, driven through a control socket (open-work:
the real A1200/040 freeze; reach a race through the native menus, as a player does).

  ui_session.py PROFILE     env FF1_BUILD (dir), C1_VARIANT (tag), RELEASE_WHD_ARGS,
                            RELEASE_PROFILE_OVERRIDES (JSON, as ff1check.py's MMU cases)
  ui_session.py --send JSON send one request (or a JSON list of them) and print the answers

Requests: {"op":"fields","count":N}, {"op":"mouse","dx":X,"dy":Y},
{"op":"move","x":X,"y":Y} (the game's pointer, native $24aa8/$24aaa, y upward),
{"op":"click","settle":N}, {"op":"button","event":"JOY1_FIRE_BUTTON","state":1},
{"op":"key","raw":R,"state":S}, {"op":"shot","label":L}, {"op":"gdb","command":C},
{"op":"exec","code":C}, {"op":"quit"}. A request that does not finish within its timeout
reports the guest as stuck, with the registers. Output tmp/step5/ui-session-PROFILE-TAG/.
"""
from pathlib import Path
import os, sys, time, signal, json, struct, hashlib, socket
sys.path.insert(0, str(Path.home() / '.local/share/amiga/pylib'))
r = Path(__file__).resolve().parents[1]
SOCK = r / 'tmp/run/default/.run/ui-session.sock'

if sys.argv[1] == '--send':
    requests = json.loads(sys.argv[2])
    for request in requests if isinstance(requests, list) else [requests]:
        c = socket.socket(socket.AF_UNIX); c.connect(str(SOCK)); c.sendall((json.dumps(request) + '\n').encode())
        answer = b''
        while not answer.endswith(b'\n'):
            chunk = c.recv(65536)
            if not chunk: break
            answer += chunk
        c.close(); print(answer.decode().strip(), flush=True)
    sys.exit(0)

from amigaxdev.gdbserve import Server
from amigaxdev.input import Input
os.chdir(r)
profile = sys.argv[1]; tag = os.environ.get('C1_VARIANT', 'candidate')
out = r / 'tmp/step5' / f'ui-session-{profile}-{tag}'; out.mkdir(parents=True, exist_ok=True)
b = Path(os.environ.get('FF1_BUILD', str(r / 'tmp/build/fr10-production'))) / 'FerrariFormulaOne.slave'
profiles = json.loads((r / 'tmp/manifest/step3-profiles.json').read_text()); os.environ.update(profiles[profile])
os.environ.update(json.loads(os.environ.get('RELEASE_PROFILE_OVERRIDES', '{}')))
os.environ.update(SLAVE=str(b), WARP='1', WINDOW='none', JOY0='mouse', DETERMINISTIC='1',
                  WHD_ARGS=os.environ.get('RELEASE_WHD_ARGS', 'CUSTOM2=1'),
                  FSUAE=os.environ.get('RELEASE_FSUAE', os.environ['FSUAE_ARM']), FF1_FRAME_SENTINEL='0',
                  KICKSTART=os.environ['KICKSTART_A1200'] if not profile.startswith('a500') else os.environ['KICKSTART'])
s = Server('ff1measure', root=str(r), run_script='tools/run.sh', run_dir='tmp/run/default/.run', profile_window=False)
log = []; controls = None
report = dict(profile=profile, tag=tag, whd=os.environ['WHD_ARGS'], extra=os.environ.get('EXTRA_ARGS', ''),
              slave_sha256=hashlib.sha256(b.read_bytes()).hexdigest(), requests=[])


def save(): (out / 'result.json').write_text(json.dumps(report, indent=1) + '\n')


try:
    g = s.boot(); controls = Input(g)

    def cmd(c, timeout=180):
        v = g.cmd(c, timeout=timeout); log.append(c + '\n' + v); (out / 'live.log').write_text('\n'.join(log)); return v

    def val(e): return int(cmd('p/x ' + e).split('=')[-1].strip(), 16)

    # The root and its hunk table (as the other harness scripts find them).
    chip = int(os.environ['CHIP_KB']) * 1024
    for attempt in range(int(os.environ.get('UI_ROOT_TRIES', '30'))):
        controls.fields(50)
        cmd(f'dump binary memory {out.relative_to(r)}/memory.bin 0 {chip}')
        mem = (out / 'memory.bin').read_bytes()
        size = int(os.environ.get('FAST_KB', '0')) * 1024
        if size:
            cmd(f'dump binary memory {out.relative_to(r)}/memory-fast.bin {0x200000} {0x200000 + size}')
            mem += bytes(0x200000 - len(mem)) + (out / 'memory-fast.bin').read_bytes()
        u = lambda a: struct.unpack_from('>I', mem, a)[0]
        at = mem.find(b'FF1B7PUBLICROOT')
        if at > 0:
            root = u(at - 4) * 4 + 4
            if mem[root:root + 2] == bytes.fromhex('6000'): break
    else:
        root = None                                  # not reached yet: no native mapping
    table = u(root + 16) * 4 if root else None
    for f in out.glob('memory*.bin'): f.unlink()
    report.update(root=root and hex(root), table=table and hex(table)); save()
    sys.path.insert(0, str(r / 'tools'))
    from step5_b7_addresses import Addresses

    def native(a):
        """Map a canonical address through the live hunk table (hunks move between overlays)."""
        cmd(f'dump binary memory {out.relative_to(r)}/map.bin 0 {chip}')
        m = (out / 'map.bin').read_bytes()
        size = int(os.environ.get('FAST_KB', '0')) * 1024
        if size:
            cmd(f'dump binary memory {out.relative_to(r)}/map-fast.bin {0x200000} {0x200000 + size}')
            m += bytes(0x200000 - len(m)) + (out / 'map-fast.bin').read_bytes()
        return Addresses(m, table).map(a)

    def position():
        x = native(0x24aa8)
        return val(f'*(unsigned short*){x}'), val(f'*(unsigned short*){x + 2}')

    if SOCK.exists(): SOCK.unlink()
    server = socket.socket(socket.AF_UNIX); server.bind(str(SOCK)); server.listen(1)
    print('UI session ready', SOCK, flush=True)
    while True:
        connection, _ = server.accept(); request = json.loads(s.read_request(connection)); answer = {}
        try:
            op = request['op']
            if op == 'fields': controls.fields(request['count'])
            elif op == 'mouse': controls.mouse(request['dx'], request['dy'], request.get('fields', 2))
            elif op == 'move':
                # The game's pointer y grows upward, the mouse's downward: converge on -y.
                def flipped():
                    x, y = position(); return x, -y
                x, y = controls.move_to((request['x'], -request['y']), flipped); answer['at'] = (x, -y)
            elif op == 'click':
                controls.button('JOY1_FIRE_BUTTON', 1); controls.fields(4)
                controls.button('JOY1_FIRE_BUTTON', 0); controls.fields(request.get('settle', 20))
            elif op == 'button': controls.button(request['event'], request['state'])
            elif op == 'key': controls.key(request['raw'], request['state'])
            elif op == 'shot': answer['capture'] = s.handle(g, f'shot {out}/{request["label"]}.png')
            elif op == 'gdb': answer['reply'] = cmd(request['command'])
            elif op == 'exec': exec(request['code'], dict(globals(), answer=answer))   # own namespace
            elif op == 'quit': answer = {'status': 'closing'}
            else: raise ValueError(op)
        except TimeoutError as e:
            answer = {'error': 'stuck: ' + repr(e)[:400]}
            try:
                g.stop(); answer['registers'] = cmd('info registers', timeout=30)
                s.handle(g, f'shot {out}/stuck.png')
            except Exception as e2:
                answer['registers_error'] = repr(e2)
        except Exception as e:
            answer = {'error': repr(e)[:2000]}
        report['requests'].append({'request': request, 'answer': answer}); save()
        connection.sendall((json.dumps(answer) + '\n').encode()); connection.close()
        if request['op'] == 'quit': break
    server.close(); SOCK.unlink()
finally:
    try:
        if controls: controls.release_all()
    except Exception: pass
    (out / 'capture.log').write_text('\n'.join(log))
    if s.g: s.g.p.kill()
    try: os.kill(int((r / 'tmp/run/default/.run/fsuae.pid').read_text()), signal.SIGKILL)
    except (ProcessLookupError, FileNotFoundError): pass

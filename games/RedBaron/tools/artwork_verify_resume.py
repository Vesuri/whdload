import json, re, socket, subprocess, sys, time
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, 'tools')
import route_status as r
a=SimpleNamespace(out=Path('tmp/prof/artwork-final-verify-040-1'), transitions=True)
__file__=str(Path('tools/artwork_verify.py').resolve())
symbols = {m[1]: int(m[2], 16) for line in (a.out / 'slave.lst').read_text(encoding='latin1').splitlines()
           if (m := re.match(r'^(\w+)\s+00:([0-9A-Fa-f]+)\s*$', line))}
entry = json.loads((a.out / 'entry.json').read_text())['entry']
base = entry['game_anchor'] - symbols['tape_game_anchor']
sim = entry['sim']


def advance(count):
    return r.command(f'gdb delete\nbreak *{entry["game_anchor"]:#x}\nignore $bpnum {count - 1}\ncontinue\ndelete')


def dump(name, size, label):
    address = base + symbols[name]
    path = a.out / (label + '-' + name + '.bin')
    r.command(f'gdb dump binary memory {path} {address:#x} {address + size:#x}')
    return path.read_bytes()


def twins(label):
    result = dump('artwork_cache_twin_result', 16, label)
    checked, active, scratch, passes = [int.from_bytes(result[i:i+4], 'big') for i in range(0, 16, 4)]
    assert (checked, active, scratch, passes) == (63, 0, 0, 6), result.hex()
    stats = dump('artwork_cache_stats', 12, label)
    print(label, 'six native twins passed', stats.hex(), flush=True)
    return dict(label=label, checks=6, hits=int.from_bytes(stats[:4], 'big'), fills=int.from_bytes(stats[4:8], 'big'))


rows = [twins('initial')]
if a.transitions:
    # The completed VERIFY menu tape still replaces the native key pop. Restore
    # its original jump target so hardware keys reach the unmodified flight UI.
    r.command(f'gdb set {{unsigned int}}{sim + 0x1ef94:#x}={sim + 0x309cc:#x}')
    tracked = Path(__file__).resolve().parent

    def key(raw, up=False):
        with socket.socket(socket.AF_UNIX) as sock:
            sock.connect(str(Path('tmp/run/default/.run/completion-input.sock').resolve()))
            sock.sendall(f'irq-{"up" if up else "down"}:{sim},200588,{raw}'.encode())
            reply = sock.recv(65536).decode()
            assert reply.startswith('OK '), reply

    h3raw = r.command(f'gdb printf "H3 %u\\n", *(unsigned int*){base + symbols["artwork_cache_h3"]:#x}')
    h3 = int(re.search(r'H3 (\d+)', h3raw)[1])
    for label, raw, expected in [('rear', 0x51, 1), ('left', 0x52, 2), ('right', 0x53, 3), ('front', 0x50, 0)]:
        key(raw)
        advance(2)
        key(raw, True)
        advance(4)
        result = r.command(f'gdb printf "VIEW %u\\n", *(unsigned short*){h3 + 0x6712:#x}')
        assert int(re.search(r'VIEW (\d+)', result)[1]) == expected, result
        r.command('shot ' + str((a.out / (label + '.png')).resolve()))
        rows.append(dict(label=label, view=expected))
        print(label, 'view passed', flush=True)
    # Actual hardware fire key. Native firing programs remain outside the cache.
    key(0x40)
    fire = r.command(f'gdb delete\nset $firing=0\nbreak *{sim + 0x15f62:#x}\ncommands\nsilent\nset $firing=$firing+1\ncontinue\nend\nbreak *{entry["game_anchor"]:#x}\nignore $bpnum 5\ncontinue\nprintf "FIRING %u\\n", $firing\ndelete')
    (a.out / 'firing.log').write_text(fire)
    assert int(re.search(r'FIRING (\d+)', fire)[1]) > 0, fire
    r.command('shot ' + str((a.out / 'firing.png').resolve()))
    key(0x40, True)
    advance(4)
    # Reset only VERIFY instrumentation, then compare the warmed caches again.
    at = base + symbols['artwork_cache_twin_result']
    r.command(f'gdb set {{unsigned int}}{at:#x}=0\nset {{unsigned int}}{at + 12:#x}=0')
    advance(8)
    rows.append(twins('after-views-fire'))
    subprocess.run([sys.executable, '-B', str(tracked / 'completion_host_input.py'), 'quit'], check=True)
r.command('shot ' + str((a.out / 'final.png').resolve()))
(a.out / 'result.json').write_text(json.dumps(dict(passed=True, rows=rows), indent=2) + '\n')
r.command('quit')
print('ARTWORK VERIFICATION COMPLETE', a.out, flush=True)

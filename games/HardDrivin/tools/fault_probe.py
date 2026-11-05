"""Replay a feel fixture run to a field, then stop at the first CPU fault (plan step H3).

fault_probe.py OUT --plan NAME --field N [--custom1 0|1|2] [--prefix P] [--slave PATH]

OUT is a new directory below tmp/prof (relative to the game directory). Boots the fixture slave
(tmp/build/PREFIX+NAME.slave, or PATH, for example a run's slave.slave) like
capture_feel.py, replays to record N (the runs are deterministic), then puts breakpoints
on the bus error, address error, illegal instruction, zero divide, CHK, TRAPV and line A/F
handlers (privilege violations are routine in the game) and runs to the first one.
Writes the vector table (vectors.txt), the registers, the exception frame and the code at
the handler (exception.txt), and the game's code, data and BSS and the memory banks at
the fault (fault-*.bin). The stacked PC of an address error is in the frame after the
access address and instruction word. Use a distinct INSTANCE.
"""
import argparse
import os
import struct
from capture_demo import ROOT, command
from capture_session import Session

REC = 80
VCOUNT = 34
FAULT_VECTORS = (0, 1, 2, 3, 4, 5, 8, 9)   # from $8: all but privilege ($20) and trace ($24)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    p.add_argument('--plan', required=True)
    p.add_argument('--field', type=int, required=True)
    p.add_argument('--custom1', type=int, choices=(0, 1, 2), default=2)
    p.add_argument('--prefix', default='feel-')
    p.add_argument('--slave')
    a = p.parse_args()
    slave = os.path.abspath(a.slave) if a.slave else ROOT / 'tmp/build' / ('%s%s.slave' % (a.prefix, a.plan))
    os.chdir(ROOT)
    out = (ROOT / a.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    s = Session(out, 'a500', slave, 0x10ed4)
    s.env['WHD_ARGS'] += ' CUSTOM1=%d' % a.custom1
    try:
        s.boot()
        hits = []
        for bank, b in s.dump_banks('anchor'):
            i = b.find(b'HDFEEL02')
            while i >= 0:
                hits.append((bank + i, struct.unpack_from('>5i', b, i + 8)))
                i = b.find(b'HDFEEL02', i + 1)
        assert len(hits) == 1, hits
        sig, offsets = hits[0]
        state, vbuf, _, flush_rec, _ = (sig + o for o in offsets)
        rel = out.relative_to(ROOT)
        count = '(*(unsigned short*)%#x)' % (state + VCOUNT)
        command('\n'.join([
            'gdb break *%#x' % flush_rec,
            'set $n=0',
            'while $n < %d' % a.field,
            'continue',
            'append binary memory %s/rec.bin %#x %#x+%d*%s' % (rel, vbuf, vbuf, REC, count),
            'set $n=$n+%s' % count,
            'end',
            'delete']), timeout=1800)
        print('replayed to record', len((out / 'rec.bin').read_bytes()) // REC, flush=True)
        vec = command('gdb x/16xw 0x8')
        (out / 'vectors.txt').write_text(vec)
        words = [int(w, 16) for line in vec.splitlines() if ':' in line for w in line.split(':', 1)[1].split()]
        targets = sorted(set(words[i] for i in FAULT_VECTORS))
        reply = command('\n'.join(['gdb ' + '\n'.join('break *%#x' % t for t in targets), 'continue',
                                   'info registers', 'x/8xw $sp', 'x/12i $pc', 'delete']), timeout=600)
        (out / 'exception.txt').write_text(reply)
        print(reply[-2500:], flush=True)
        for r in s.layout['regions']:
            command('gdb dump binary memory %s/fault-%s.bin %#x %#x' % (rel, r['name'], r['base'], r['base'] + r['size']))
        s.dump_banks('fault')
    finally:
        s.close()


if __name__ == '__main__':
    main()

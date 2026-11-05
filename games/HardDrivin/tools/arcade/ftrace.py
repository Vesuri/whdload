"""Decode an ftrace.lua value trace (plan step D1).

ftrace.py FTRACE [FRAME [FUNC]]

Prints the float operations of one MSP frame (default: the first complete
one) as  CALLER  a OP b = result, with values in the MSP's double format
(tidbl.py), followed by the lifted statement (msp_lift.py) that the call
feeds. FUNC (hex) limits the output to calls from one function.
"""
import bisect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tidbl import from_hex_be                      # noqa: E402
import msp_lift                                    # noqa: E402

OPS = {'74b400': '*', '74b600': '/', '74ba00': '\\', '74c0a0': '+', '74c000': '-', '74c400': '-r',
       '74d600': '<=', '74d620': '<', '74d640': '>=', '74d660': '>', '74dc00': '!=',
       '74de00': 'neg', '74d260': 'itod', '74ce00': 'dtoi'}


def s32(v):
    return v - (1 << 32) if v & 0x80000000 else v


def statements():
    """call site -> (function, first lifted statement at or after it)"""
    lf = msp_lift.Lifter(msp_lift.load())
    stm = []
    for f in lf.starts:
        out = []
        lf.lift(f, out)
        for ln in out[1:]:
            if len(ln) > 7 and ln[6] == ' ':
                stm.append((int(ln[:6], 16), f, ln[8:]))
    stm.sort()
    return lf, stm


def frames(path):
    cur, fr = None, None
    for ln in open(path):
        f = ln.split()
        if not f:
            continue
        if f[0] == 'S':
            if cur:
                yield fr, cur
            fr, cur = int(f[1]), []
        elif f[0] in ('OFF', 'ON'):
            if cur:
                yield fr, cur
            cur = None
        elif cur is not None and f[0] in ('F', '='):
            cur.append(f)
    if cur:
        yield fr, cur


def main():
    path = sys.argv[1]
    want = int(sys.argv[2]) if len(sys.argv) > 2 else None
    func = int(sys.argv[3], 16) if len(sys.argv) > 3 else None
    lf, stm = statements()
    keys = [s[0] for s in stm]
    for fr, rows in frames(path):
        if want is not None and fr != want:
            continue
        print('frame', fr)
        for i, f in enumerate(rows):
            if f[0] != 'F':
                continue
            site = int(f[2], 16) - 0x20
            fn = lf.starts[bisect.bisect_right(lf.starts, site) - 1]
            if func is not None and fn != func:
                continue
            op = OPS.get(f[1], f[1])
            res = rows[i + 1] if i + 1 < len(rows) and rows[i + 1][0] == '=' else None
            if op == 'itod':
                txt = 'itod %d' % s32(int(f[3], 16))
            elif op in ('neg', 'dtoi'):
                txt = '%s %.8g' % (op, from_hex_be(f[5]))
            else:
                txt = '%.8g %s %.8g' % (from_hex_be(f[4]), op, from_hex_be(f[5]))
            if res:
                txt += ' = %d' % s32(int(res[2], 16)) if res[1] == 'i' else ' = %.8g' % from_hex_be(res[1])
            j = bisect.bisect_left(keys, site)
            ctx = stm[j][2] if j < len(stm) and stm[j][1] == fn else ''
            print('%06X  %-44s  %s' % (site, txt, ctx[:90]))
        if want is None:
            break


if __name__ == '__main__':
    main()

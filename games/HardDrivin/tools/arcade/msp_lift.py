"""Lift the MSP's double-precision stack code into expressions (plan step D).

msp_lift.py FUNC [FUNC...]   (hex bit addresses; 'all' lifts every function)

The TI C compiler evaluates doubles on the A14 operand stack: push the operand
longs (low then high), call the float routine, pop the result high then low.
This follows that pattern symbolically through straight-line code and prints
each store, compare and call. It is a reading aid, not a decompiler: register
state is forgotten at branch targets, and anything it does not understand is
printed as the raw instruction.

Names: g_ADDR is a global double (bit address), L_OFF a local at A13+OFF,
[BASE+OFF] memory through a pointer; constants in the code section are shown
by value (MSP doubles have no hidden bit, see tidbl.py). Compares: 74D600 a<=b, 74D620 a<b, 74D640 a>=b, 74D660 a>b, 74DC00
a!=b; each returns 0/1 in A8, so JREQ branches when the comparison is false.
"""
import bisect
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tidbl import from_bytes_le

HERE = os.path.dirname(os.path.abspath(__file__))
DIS = os.path.join(HERE, '..', '..', 'tmp', 'arcade', 'msp', 'msp_code.dis')
SEC0 = os.path.join(HERE, '..', '..', 'tmp', 'arcade', 'msp', 'sec00_00700000.bin')
BASE0 = 0x700000

BIN = {0x74b400: '*', 0x74b600: '/', 0x74ba00: '\\', 0x74c0a0: '+', 0x74c000: '-', 0x74c400: '-r'}
CMP = {0x74d600: '<=', 0x74d620: '<', 0x74d640: '>=', 0x74d660: '>', 0x74dc00: '!='}
NEG, ITOD, DTOI = 0x74de00, 0x74d260, 0x74ce00
NAMES = {}          # optional names for globals, from msp_names.txt


def load():
    L = []
    with open(DIS) as f:
        for ln in f:
            m = re.match(r'([0-9A-F]{8}): ((?:[0-9A-F]{4} )+)\s*(.*)$', ln.rstrip('\n'))
            if m:
                L.append((int(m.group(1), 16), m.group(3).strip(), ln.rstrip('\n')))
    return L


CODE = open(SEC0, 'rb').read()


def const_double(addr):
    o = (addr - BASE0) // 8
    if addr % 16 or o < 0 or o + 8 > len(CODE):
        return None
    return from_bytes_le(CODE[o:o + 8])


def num(t):
    return int(t[:-1], 16) if t.endswith('h') else int(t)


def s32(v):
    v &= 0xffffffff
    return v - (1 << 32) if v & 0x80000000 else v


def gname(a):
    if a in NAMES:
        return NAMES[a]
    return 'g_%06X' % a


class Addr:
    """Address = base (None for absolute, or a string) + offset in bits."""
    def __init__(self, base, off):
        self.base, self.off = base, off

    def plus(self, k):
        return Addr(self.base, self.off + k)

    def key(self):
        return (self.base, self.off)

    def __str__(self):
        if self.base is None:
            return gname(self.off)
        if self.base == 'fp':
            return 'L_%X' % self.off
        return '[%s%+X]' % (self.base, self.off) if self.off else '[%s]' % self.base


def dname(a):
    """Name for the double at Addr a."""
    if a.base is None and BASE0 <= a.off < BASE0 + len(CODE) * 8:
        v = const_double(a.off)
        if v is not None:
            return '%.10g' % v
    return str(a)


class Long:
    """One 32-bit item on the A14 stack: a memory long, half of a double
    expression, or an integer value."""
    def __init__(self, kind, x):
        self.kind, self.x = kind, x     # kind: mem (x Addr), lo/hi (x str), int (x str)


def pair(lo, hi):
    if lo.kind == 'mem' and hi.kind == 'mem' and lo.x.base == hi.x.base and hi.x.off == lo.x.off + 0x20:
        return dname(lo.x)
    if lo.kind == 'lo' and hi.kind == 'hi' and lo.x == hi.x:
        return lo.x
    return '{%s:%s}' % (show(lo), show(hi))


def show(l):
    return ('*' + str(l.x)) if l.kind == 'mem' else str(l.x)


def args_list(items):
    out, i = [], 0
    while i < len(items):
        if i + 1 < len(items):
            p = pair(items[i], items[i + 1])
            if not p.startswith('{'):
                out.append(p); i += 2; continue
        out.append(show(items[i])); i += 1
    return out


def strip(e):
    return e[1:-1] if e.startswith('(') and e.endswith(')') else e


class Lifter:
    def __init__(self, L):
        self.L = L
        self.addrs = [a for a, _, _ in L]
        starts = {BASE0}
        self.targets = set()
        for a, t, _ in L:
            m = re.match(r'CALL[RA]\s+([0-9A-F]+)h', t)
            if m:
                starts.add(int(m.group(1), 16))
            m = re.match(r'(J\w+|DSJ\w*)\s+(?:A\d+,)?([0-9A-F]+)h', t)
            if m:
                self.targets.add(int(m.group(2), 16))
        self.starts = sorted(starts)

    def func_range(self, f):
        i = bisect.bisect_right(self.starts, f)
        end = self.starts[i] if i < len(self.starts) else 1 << 32
        return [x for x in self.L if f <= x[0] < end]

    def reset(self):
        self.R = {}          # reg -> ('addr', Addr) | ('val', str)
        self.stack = []
        self.marks = []
        self.pending = None  # (cmp expr) waiting for a branch
        self.prev_op = ''
        self._copy = self._last_copy = None
        self._last_addr = 0

    def reg_addr(self, r):
        v = self.R.get(r)
        if v and v[0] == 'addr':
            return v[1]
        if r == 'A13':
            return Addr('fp', 0)
        if v and v[0] == 'long':
            return Addr(show(v[1]), 0)
        return Addr(r if not v else v[1], 0)

    def reg_val(self, r):
        v = self.R.get(r)
        if v is None:
            return r
        if v[0] == 'long':
            return show(v[1])
        return str(v[1]) if v[0] == 'addr' else v[1]

    def mem(self, op):
        """Addr for an indirect operand: *Rn, *Rn+, *Rn(K), @N."""
        m = re.match(r'@([0-9A-F]+)h$', op)
        if m:
            return Addr(None, int(m.group(1), 16)), None
        m = re.match(r'\*(A\d+)\(([0-9A-F]+h)\)$', op)
        if m:
            k = s32(num(m.group(2))) if num(m.group(2)) < 0x10000 else s32(num(m.group(2)))
            if k >= 0x8000 and k < 0x10000:
                k -= 0x10000
            return self.reg_addr(m.group(1)).plus(k), None
        m = re.match(r'\*(A\d+)(\+?)$', op)
        if m:
            return self.reg_addr(m.group(1)), (m.group(1) if m.group(2) else None)
        return None, None

    def advance(self, r, k):
        a = self.reg_addr(r)
        self.R[r] = ('addr', a.plus(k))

    def pop(self):
        if self.stack:
            return self.stack.pop()
        return Long('int', '?')

    def pop_double(self):
        hi = self.pop()
        lo = self.pop()
        return pair(lo, hi)

    def push_double(self, e):
        self.stack.append(Long('lo', e))
        self.stack.append(Long('hi', e))

    def lift(self, f, out):
        self.reset()
        rng = self.func_range(f)
        out.append('== %06X' % f)
        held = None          # high long popped into a register, waiting for its store
        for addr, t, raw in rng:
            if addr in self.targets:
                out.append('%06X:' % addr)
                self.R = {}
            p = t.split(None, 1)
            op = p[0]
            args = p[1].split(',') if len(p) > 1 else []
            s = None
            if op == 'CALLR' or op == 'CALLA':
                tgt = num(args[0])
                if tgt in BIN:
                    b = self.pop_double(); a = self.pop_double()
                    o = BIN[tgt]
                    if o == '\\':
                        e = '(%s / %s)' % (b, a)
                    elif o == '-r':
                        e = '(%s - %s)' % (b, a)
                    else:
                        e = '(%s %s %s)' % (a, o, b)
                    self.push_double(e)
                elif tgt in CMP:
                    b = self.pop_double(); a = self.pop_double()
                    self.pending = '%s %s %s' % (strip(a), CMP[tgt], strip(b))
                    self.R['A8'] = ('val', '(%s)' % self.pending)
                elif tgt == NEG:
                    self.push_double('-%s' % self.pop_double())
                elif tgt == ITOD:
                    self.push_double('dbl(%s)' % self.reg_val('A8'))
                elif tgt == DTOI:
                    self.R['A8'] = ('val', 'int(%s)' % strip(self.pop_double()))
                else:
                    base = self.marks[-1] if self.marks else 0
                    argl = args_list(self.stack[base:])
                    s = 'call %06X(%s)' % (tgt, ', '.join(argl))
                    self.R['A8'] = ('val', 'ret_%06X' % tgt)
                    self.retval = tgt
                    for r in ('A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6'):
                        self.R.pop(r, None)
            elif op == 'MOVI' and len(args) == 2:
                v = num(args[0])
                self.R[args[1]] = ('addr', Addr(None, v)) if v >= 0x700000 else ('val', '%d' % s32(v))
            elif op == 'MOVK' and len(args) == 2:
                self.R[args[1]] = ('val', '%d' % num(args[0]))
            elif op in ('CLR',) or (op in ('SUB', 'XOR') and len(args) == 2 and args[0] == args[1]):
                self.R[args[-1]] = ('val', '0')
            elif op == 'MOVE' and len(args) >= 2:
                src, dst = args[0], args[1]
                if dst == '*A14+':
                    if re.match(r'A\d+$', src):
                        v = self.R.get(src)
                        self.stack.append(Long('int', self.reg_val(src)))
                    else:
                        a, inc = self.mem(src)
                        if a is None:
                            s = '?? ' + t
                        else:
                            self.stack.append(Long('mem', a))
                            if inc:
                                self.advance(inc, 0x20)
                elif src == '-*A14':
                    l = self.pop()
                    if re.match(r'A\d+$', dst):
                        if l.kind == 'hi':
                            held = l
                        self.R[dst] = ('long', l)
                    else:
                        m = re.match(r'-\*(A\d+)$', dst)
                        if m:
                            self.advance(m.group(1), -0x20)
                            a = self.reg_addr(m.group(1))
                        else:
                            a, _ = self.mem(dst)
                        s = self.store(a, l)
                elif src == 'A14' and dst == '-*SP':
                    self.marks.append(len(self.stack))
                elif dst == 'A14' and 'SP' in src:
                    if self.marks:
                        del self.stack[self.marks.pop():]
                elif re.match(r'A\d+$', src) and not re.match(r'A\d+$', dst) and 'SP' not in dst:
                    a, inc = self.mem(dst)
                    v = self.R.get(src)
                    if a is None:
                        s = '?? ' + t
                    elif v and v[0] == 'long' and v[1].kind == 'mem' and args[2:] == ['1']:
                        s = self.copy(v[1].x, a)
                    elif v and v[0] == 'long':
                        s = self.store(a, v[1])
                    else:
                        self.longstore(a, self.reg_val(src))
                        s = '%s = %s' % (a, self.reg_val(src)) if a.base != 'fp' or True else None
                        if args[2:] == ['0']:
                            s += '    (word)'
                    if inc:
                        self.advance(inc, 0x20 if args[2:] == ['1'] else 0x10)
                elif re.match(r'A\d+$', dst) and not re.match(r'A\d+$', src) and 'SP' not in src:
                    a, inc = self.mem(src)
                    if a is None:
                        s = '?? ' + t
                    elif args[2:] == ['1']:
                        self.R[dst] = ('long', Long('mem', a))
                    else:
                        self.R[dst] = ('val', 'w%s' % a)
                    if inc:
                        self.advance(inc, 0x20 if args[2:] == ['1'] else 0x10)
                elif re.match(r'A\d+$', src) and re.match(r'A\d+$', dst):
                    if src == 'A14' and dst == 'A13':
                        pass
                    else:
                        self.R[dst] = self.R.get(src, ('addr', self.reg_addr(src)) if src == 'A13' else ('val', src))
                elif src.startswith('@') and dst.startswith('@'):
                    a, _ = self.mem(src); b, _ = self.mem(dst)
                    if args[2:] == ['0']:
                        s = '%s = w%s    (word)' % (b, a)
                    else:
                        s = self.copy(a, b)
                elif 'SP' not in t:
                    a, inc = self.mem(src); b, inc2 = self.mem(dst)
                    if a is not None and b is not None:
                        s = self.copy(a, b)
                        for r in (inc, inc2):
                            if r:
                                self.advance(r, 0x20)
                    else:
                        s = '?? ' + t
            elif op in ('ADDI', 'ADDK', 'SUBI', 'SUBK') and len(args) == 2:
                k = num(args[0])
                if op in ('ADDI', 'SUBI') and k >= 0x8000 and k < 0x10000 and len(raw.split()) < 6:
                    k -= 0x10000
                if op.startswith('SUB'):
                    k = -k if op == 'SUBK' else -(k + 1) if op == 'SUBI' and k < 0x10000 else -k
                if op == 'SUBI' and len(raw.split()) < 6:
                    pass
                r = args[1]
                if r == 'A14' and self.prev_op == 'MOVE A14,A13':
                    pass
                elif r == 'A14':
                    if k > 0:
                        for _ in range(k // 0x20):
                            self.stack.append(Long('int', '?'))
                    else:
                        for _ in range((-k) // 0x20):
                            self.pop()
                else:
                    v = self.R.get(r)
                    if v and v[0] == 'addr':
                        self.R[r] = ('addr', v[1].plus(k))
                    else:
                        self.R[r] = ('val', '(%s%+d)' % (self.reg_val(r), k))
            elif op in ('ADD', 'SUB', 'SLL', 'SLA', 'SRL', 'SRA', 'AND', 'OR', 'XOR', 'ANDI', 'ORI', 'XORI', 'MPYS', 'MPYU', 'DIVS', 'DIVU', 'NEG', 'NOT', 'INC', 'DEC', 'ABS') and len(args) >= 1:
                r = args[-1]
                sym = {'ADD': '+', 'SUB': '-', 'SLL': '<<', 'SLA': '<<', 'SRL': '>>', 'SRA': '>>', 'AND': '&', 'OR': '|',
                       'XOR': '^', 'ANDI': '&', 'ORI': '|', 'XORI': '^', 'MPYS': '*', 'MPYU': '*', 'DIVS': '/', 'DIVU': '/'}
                if op in sym:
                    x = args[0]
                    try:
                        xv = self.reg_val(x) if re.match(r'A\d+$', x) else ('%d' % num(x))
                    except ValueError:
                        xv = x
                    self.R[r] = ('val', '(%s %s %s)' % (self.reg_val(r), sym[op], xv))
                else:
                    self.R[r] = ('val', '%s(%s)' % (op.lower(), self.reg_val(r)))
            elif op.startswith('J') or op.startswith('DSJ'):
                tgt = args[-1] if args else ''
                if self.pending and op in ('JREQ', 'JRNE', 'JREQ', 'JRZ', 'JRNZ'):
                    c = self.pending if op in ('JRNE', 'JRNZ') else '!(%s)' % self.pending
                    s = 'if %s goto %s' % (c, tgt.rstrip('h'))
                    self.pending = None
                else:
                    s = '%s %s' % (op, ','.join(args))
            elif op in ('RETS', 'RETI'):
                s = op.lower() + (' ' + args[0] if args else '')
            elif op in ('MMTM', 'MMFM', 'SETF', 'NOP', 'DW', 'MOVB'):
                pass
            elif op in ('CMP', 'CMPI', 'BTST', 'MOVE') or True:
                s = '.. ' + t
            self.prev_op = t.replace(' ', '')[:4] + ' ' + ','.join(args)
            c = getattr(self, '_copy', None)
            if c and c is self._last_copy:
                # a long copy that the next instruction did not pair up
                out.append('%06X  %s = (long) %s' % (self._last_addr, c[1], dname(c[0]) if False else c[0]))
                self._copy = None
            self._last_copy, self._last_addr = getattr(self, '_copy', None), addr
            if s:
                out.append('%06X  %s' % (addr, s))
        return out

    def store(self, a, l):
        """Store of a popped long; a high half then its low half make a double store."""
        if l.kind == 'hi':
            self._hi = (a, l)
            return None
        if l.kind == 'lo' and getattr(self, '_hi', None) and self._hi[1].x == l.x and self._hi[0].key() == a.plus(0x20).key():
            self._hi = None
            return '%s = %s' % (a, strip(l.x))
        if l.kind == 'mem':
            return '%s = (long) %s' % (a, l.x)
        return '%s = (long) %s' % (a, show(l))

    def longstore(self, a, v):
        pass

    def copy(self, a, b):
        """Long copy; an aligned pair of copies is a double copy."""
        prev = getattr(self, '_copy', None)
        self._copy = (a, b)
        if prev and prev[0].key() == a.plus(-0x20).key() and prev[1].key() == b.plus(-0x20).key():
            self._copy = None
            return '%s = %s' % (prev[1], dname(prev[0]))
        return None


def main():
    global NAMES
    p = os.path.join(HERE, 'msp_names.txt')
    if os.path.exists(p):
        for ln in open(p):
            ln = ln.split('#')[0].split()
            if len(ln) >= 2:
                NAMES[int(ln[0], 16)] = ln[1]
    L = load()
    lf = Lifter(L)
    fs = lf.starts if sys.argv[1:] == ['all'] else [int(x, 16) for x in sys.argv[1:]]
    for f in fs:
        out = []
        lf.lift(f, out)
        print('\n'.join(out))


if __name__ == '__main__':
    main()

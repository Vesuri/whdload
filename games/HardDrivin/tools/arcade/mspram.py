"""Read MSP RAM dumps (ftrace.lua dump: words from bit address $74DE80).

mspram.py DUMP ADDR[:TYPE] ...   TYPE d (MSP double, see tidbl.py; default), l (long), w (word)
ADDR may be BASE+OFF (hex). Fields can sit at any bit address.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tidbl import from_bits

BASE = 0x74DE80


class Ram:
    def __init__(self, path):
        b = open(path, 'rb').read()
        self.w = struct.unpack('<%dH' % (len(b) // 2), b)

    def bits(self, addr, n):
        i, sh = divmod(addr - BASE, 16)
        v = 0
        for k in range((sh + n + 15) // 16):
            v |= self.w[i + k] << (16 * k)
        return (v >> sh) & ((1 << n) - 1)

    def dbl(self, addr):
        return from_bits(self.bits(addr, 64))

    def long(self, addr):
        v = self.bits(addr, 32)
        return v - (1 << 32) if v & 0x80000000 else v

    def word(self, addr):
        v = self.bits(addr, 16)
        return v - 0x10000 if v & 0x8000 else v


def parse(a):
    s = 0
    for part in a.split('+'):
        s += int(part, 16)
    return s


def main():
    r = Ram(sys.argv[1])
    for a in sys.argv[2:]:
        a, _, t = a.partition(':')
        addr = parse(a)
        v = {'l': r.long, 'w': r.word}.get(t, r.dbl)(addr)
        print('%06X %s' % (addr, ('%.10g' % v) if isinstance(v, float) else v))


if __name__ == '__main__':
    main()

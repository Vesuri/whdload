"""Dump the MSP's TI C .cinit records (msp/sec01_00778e80.bin): msp_cinit.py [ADDR...]

Each record is a 16-bit word count, a 32-bit bit address and the data words;
the C start-up copies them into RAM. Four-word records are printed as doubles
(the MSP format, see tidbl.py),
longer ones as doubles where they hold 8-byte aligned values, plus raw words.
With addresses, prints only the records that cover them.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tidbl import from_bytes_le

HERE = os.path.dirname(os.path.abspath(__file__))
SEC1 = os.path.join(HERE, '..', '..', 'tmp', 'arcade', 'msp', 'sec01_00778e80.bin')


def records(path=SEC1):
    b = open(path, 'rb').read()
    o = 0
    while o + 6 <= len(b):
        n = struct.unpack_from('<H', b, o)[0]
        if n == 0:
            break
        addr = struct.unpack_from('<I', b, o + 2)[0]
        data = b[o + 6:o + 6 + 2 * n]
        yield addr, data
        o += 6 + 2 * n


def doubles(addr, data):
    return [(addr + 64 * i, from_bytes_le(data[8 * i:8 * i + 8])) for i in range(len(data) // 8)]


def main():
    want = [int(a, 16) for a in sys.argv[1:]]
    for addr, data in records():
        end = addr + 16 * (len(data) // 2)
        if want and not any(addr <= w < end for w in want):
            continue
        n = len(data) // 2
        if n % 4 == 0 and n <= 64:
            vals = ' '.join('%.10g' % v for _, v in doubles(addr, data))
            print('%06X %3d  %s' % (addr, n, vals))
        else:
            w = struct.unpack('<%dh' % n, data)
            print('%06X %3d  words %s' % (addr, n, ' '.join(str(x) for x in w)))


main()

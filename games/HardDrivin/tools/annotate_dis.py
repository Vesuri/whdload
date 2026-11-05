# annotate_dis.py SLOW.BIN CODE.DIS > OUT: resolve jsr d16(a4) jump-table calls to code offsets.
import re, struct, sys
SLOW_BASE, CODE, A4 = 0xc00000, 0xcfb1d0, 0xd15f16
d = open(sys.argv[1], 'rb').read()
def target(disp):
    o = A4 + disp - SLOW_BASE
    if d[o:o+2] != b'\x4e\xf9':
        return None
    return struct.unpack('>I', d[o+2:o+6])[0] - CODE
pat = re.compile(r'(jsr|jmp) (-?\d+)\(a4\)')
for line in open(sys.argv[2]):
    m = pat.search(line)
    if m:
        t = target(int(m.group(2)))
        if t is not None:
            line = line.rstrip('\n') + '\t; -> game:%05x\n' % t
    sys.stdout.write(line)

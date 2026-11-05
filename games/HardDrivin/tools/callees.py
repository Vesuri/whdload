# callees.py CODE.ANN START: list function extent (to next link.w a5) and its call targets.
import re, sys
lines = open(sys.argv[1]).read().splitlines()
start = int(sys.argv[2], 16)
out, began = [], False
for l in lines:
    a = l.split(':', 1)[0].strip()
    try: v = int(a, 16)
    except ValueError: continue
    if v < start: continue
    if began and 'link.w a5' in l: print('end %05x' % v); break
    began = True
    m = re.search(r'jsr (0x[0-9a-f]+)\(pc\)|-> game:([0-9a-f]+)|bsr\.[sw] (0x[0-9a-f]+)', l)
    if m: out.append(m.group(1) or ('0x' + m.group(2) if m.group(2) else None) or m.group(3))
print(sys.argv[2], 'calls', ' '.join(dict.fromkeys(out)))

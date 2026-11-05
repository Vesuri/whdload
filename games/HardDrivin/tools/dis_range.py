import sys
f, s, e = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
for line in open(f):
    a = line.split(':', 1)[0].strip()
    try:
        v = int(a, 16)
    except ValueError:
        continue
    if s <= v < e:
        sys.stdout.write(line)

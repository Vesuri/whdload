"""tools/link.sh's serial link. Join two pseudo-terminals: prints their two device names, relays bytes between them,
and counts bytes each way into a status file every second."""
import os, pty, select, sys, time, tty
status = sys.argv[1]
m1, s1 = pty.openpty(); m2, s2 = pty.openpty()
for fd in (s1, s2):
    tty.setraw(fd)
print(os.ttyname(s1), os.ttyname(s2), flush=True)
n = {m1: 0, m2: 0}; last = 0
while True:
    r, _, _ = select.select([m1, m2], [], [], 0.5)
    for fd in r:
        try:
            data = os.read(fd, 4096)
        except OSError:
            continue
        os.write(m2 if fd == m1 else m1, data)
        n[fd] += len(data)
    if time.time() - last > 1:
        last = time.time()
        with open(status, 'w') as f:
            f.write('1->2 %d 2->1 %d\n' % (n[m1], n[m2]))

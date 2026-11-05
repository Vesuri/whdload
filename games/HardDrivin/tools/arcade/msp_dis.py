"""Print part of msp/msp_code.dis: msp_dis.py START [END] (hex bit addresses).
Without END, prints to the next RETS."""
import os
import sys

DIS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tmp', 'arcade', 'msp', 'msp_code.dis')


def lines():
    with open(DIS) as f:
        for ln in f:
            if len(ln) > 9 and ln[8] == ':':
                yield int(ln[:8], 16), ln.rstrip('\n')


def main():
    a = int(sys.argv[1], 16)
    b = int(sys.argv[2], 16) if len(sys.argv) > 2 else None
    for addr, ln in lines():
        if addr < a:
            continue
        if b is not None and addr > b:
            break
        print(ln)
        if b is None and ln.split()[-1:] == ['RETS'] or (b is None and 'RETS' in ln.split()):
            break


main()

#!/usr/bin/env python3
"""The VERIFY frame log (plan step A3): frame_log.py PROF|verify.bin [FIRST_STEP [LAST_STEP]]

Per frame: step, period and work in lines (313 per PAL field), blitter interrupts, and the
game's own frame time (target, fields). Prints the period histogram in fields, the frames on
target (G1: period <= target) and work statistics for frames whose step is in the range."""
import collections,statistics as S,sys
from pathlib import Path
from pop import symbols
from verify import frames
LINES=313
def load(p):
    p=Path(p);p=p/'verify.bin' if p.is_dir() else p
    return frames(p.read_bytes(),symbols(Path(__file__).resolve().parents[1]/'tmp/build/verify/PrinceOfPersia.Slave'))
if __name__=='__main__':
    fr=load(sys.argv[1])[1:]       # the first entry has no previous exit
    lo=int(sys.argv[2]) if len(sys.argv)>2 else 0;hi=int(sys.argv[3]) if len(sys.argv)>3 else 1<<16
    fr=[f for f in fr if lo<=f['step']<=hi]
    print(f'{len(fr)} frames, steps {fr[0]["step"]}..{fr[-1]["step"]}')
    print('period histogram (fields):',sorted(collections.Counter(round(f['period']/LINES) for f in fr).items()))
    for k in ('period','work'):print(f"  {k:6} mean {S.mean(f[k] for f in fr)/LINES:5.2f}  median {S.median(f[k] for f in fr)/LINES:5.2f}  max {max(f[k] for f in fr)/LINES:5.2f}")
    print(f"  blits mean {S.mean(f['blits'] for f in fr):.1f} max {max(f['blits'] for f in fr)}; work > target: {sum(f['work']>f['target']*LINES for f in fr)}")
    on=sum(round(f['period']/LINES)<=f['target'] for f in fr)
    print(f"  on target: {on} of {len(fr)} ({on/len(fr)*100:.0f}%); targets {sorted(collections.Counter(f['target'] for f in fr).items())}")

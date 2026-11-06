#!/usr/bin/env python3
"""Turn a field-timed keypad route into a VERIFY input tape: tape_from_route.py OUT STEP...

Runs the route on the VERIFY slave with live input (CUSTOM4=$TAPE, default 0; a tape's own
entries play first, then its zero mask lets the game read the keyboard) and reads the
gameplay step counter at every keypad press/release; prints the new entries as assembler
(step, mask) lines.
"""
import os,sys
os.environ.setdefault('SLAVE',os.path.join(os.path.dirname(__file__),'../tmp/build/verify/PrinceOfPersia.Slave'))
from pop import Session
from route import run
from verify import Verify
MASK=dict(kp8=1,kp2=2,kp4=4,kp6=8)
s=Session(sys.argv[1],dict(WHD_ARGS=f"CUSTOM4={os.environ.get('TAPE','0')}"));v=Verify(s);held=0;out=['\tdc.w\t0,0']
try:
    for st in sys.argv[2:]:
        op,*a=st.split(':')
        if op in 'du' and a[0] in MASK:
            # The key takes effect at the next poll after this point.
            n=v.long('verify_steps')+1
            held=held|MASK[a[0]] if op=='d' else held&~MASK[a[0]]
            out.append(f'\tdc.w\t{n},{held}\t\t; {st} at field {s.field}')
        run(s,[st])
    print('steps at end',v.long('verify_steps'),'field',s.field)
finally:s.quit()
print('\n'.join(out+['\tdc.w\t$ffff,0']))

"""Bring-up port of the audited all-car ownership hooks; NOT gameplay acceptance."""
from pathlib import Path
import re
r=Path(__file__).resolve().parents[1];repo=r.parents[1];o=r/'tmp/build/step5-c4-motion-port';o.mkdir(parents=True,exist_ok=True)
s=(repo/'Games/FerrariFormulaOne_UpdateHooks.s').read_text();s=s[s.index('install_velocity:'):s.index('install_events:')]+s[s.index('install_fuel:'):s.index('boost_record:')]
# Retain simple failure branches normally guarded by VERIFY even in bring-up.
s=re.sub(r' IFD VERIFY\n( (?:b\w+)[.]\w+ [^\n]+\n) ENDC',r'\1',s)
stack=[True];out=[]
for line in s.splitlines():
 w=line.strip().split();op=w[0].upper() if w else ''
 if op in ('IFD','IFND'):
  assert w[1] in ['VERIFY','FF1_PLAN_B','FF1_PLAYER_HOOKS','FF1_LEAN_PLAYER'],w
  stack.append(stack[-1] and op=='IFND');continue
 if op in ('IFNE','IFEQ','IFGT','IFLT'):
  assert not stack[-1],line
  stack.append(False);continue
 if op=='ELSE':stack[-1]=stack[-2] and not stack[-1];continue
 if op=='ENDC':stack.pop();continue
 if stack[-1]:out.append(line)
assert len(stack)==1
s='\n'.join(out)+'\n'
s=re.sub(r' include "FerrariFormulaOne_[^"]+"\n','',s)
s=re.sub(r'\(([\w+]+)[.]l,pc\)',r'\1(pc)',s).replace('move.w ccr,','move.w sr,')
s=re.sub(r' cmpi[.]([wl]) ([^,]+),([\w+]+)\(pc\)',r' move.\1 \3(pc),-(sp)\n cmpi.\1 \2,(sp)+',s)
s=re.sub(r' tst[.]([wl]) ([\w+]+)\(pc\)',r' move.\1 \2(pc),-(sp)\n tst.\1 (sp)+',s)
# Native multiply calls were replaced by MULS.L in the fine fixture. The 000
# bridge must check/copy the native JSR sequence, not those 020 opcodes.
for site in (0x6de74,0x6defa):
 for off,old,new in [(0,0x4c01,0x4eb9),(2,0x0800,0x0002),(4,0x4e71,0x9500)]:
  s=s.replace(f'cmpi.w #${old:04x},${site+off:x}',f'cmpi.w #${new:04x},${site+off:x}')
s=s.replace('dc.w $4c01,$0800,$4e71','dc.w $4eb9,$0002,$9500')
# Carry is identically zero at the integer interval ratio. This adapter still
# uses the prior six/twelve-byte ownership layouts so all reset/contact writers
# retain their audited indexes; remove spare carry storage only after validation.
prefix='''; Generated bring-up port; provenance: committed UpdateHooks all-car branch.
; Not installed by ordinary slave; event cadence and 200 ms scheduler still open.
FF1PlayerContext macro
 bsr.w \\2
 endm
FF1PlayerSave macro
 movem.l d0-d7/a0-a6,-(sp)
 endm
FF1PlayerRestore macro
 movem.l (sp)+,d0-d7/a0-a6
 endm
'''
for site in ('672f0','673fc','67426','67438','6744a','6768e','676e0'):
 a=s.index('velocity_speed_rate_'+site+':');b=s.index('\n.done:',a)
 segment=s[a:b].replace(' bsr.w velocity_speed_rate',' bsr.w C4WeightedSpeedRate')
 s=s[:a]+segment+s[b:]
s=s.replace(' bsr.w FF1SpeedRate20\n',' moveq #2,d1\n bsr.w FF1SpeedRatePulses200\n')
s+='\nC4WeightedSpeedRate:\n lea speed_work(pc),a0\n move.w C4PhaseWeight(pc),d1\n bsr.w FF1SpeedRatePulses200\n tst.l d1\n bne.w velocity_fault\n move.w (a0),d0\n ext.l d0\n move.w d0,$32fbe\n rts\n'
(o/'motion.s').write_text(prefix+s)
print('Prepared',len(s.splitlines()),'lines of all-car ownership hooks')

"""B8 renderer bring-up diagnostic, not a release or accepted candidate."""
from pathlib import Path
import re,os
r=Path(__file__).resolve().parents[1]
# Keep frozen B7 evidence and its builder untouched.
s=(r/'tools/build_step5_b7_v3.py').read_text()
s=s.replace("step5-b7-v3", "step5-b8-probe")
insert='''
# Full drawing runs only when no simulation tick is due. Catch-up retains debt.
s=s.replace('FF1PresentationAfterTick:\\n rts', '''+repr('''FF1PresentationAfterTick:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 lea (schedule_context.l,pc),a0
 bsr.l FF1TimeDue
 tst.l d0
 bne.b .done
 bsr.l B8Draw
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 rts
 include "b8draw.s"
''')+''')
s=s.replace(' bsr.l FF1InstallPresentation',' bsr.l FF1InstallPresentation\\n move.w #$4ef9,$654ec\\n move.l #$65542,$654ee')
'''
s=s.replace("(o/'reset.bin').write_bytes",insert+"\n(o/'reset.bin').write_bytes",1)
s=s.replace("args=[str(Path.home()", "(o/'b8draw.s').write_text((r/'tmp/build/step5-b8-probe/b8draw.s').read_text())\nargs=[str(Path.home()",1)
rows=[]
for line in (r/'tmp/step4/active.dis').read_text().splitlines():
 m=re.match(r'([0-9a-f]{6}): ([0-9a-f]+)\s+(.*?) ;',line)
 if m:rows.append((int(m[1],16),m[3]))
text='''; Diagnostic native drawing clone; ownership audit not yet accepted.
B8Draw:
 link a6,#-64
 lea -24(sp),sp
'''
for lo,hi in [(0x654ec,0x65542),(0x65606,0x65714),(0x6571a,0x65d6e)]:
 for pc,ins in rows:
  if not lo<=pc<hi:continue
  text+=f'B8_{pc:x}:\n'
  if pc==0x65518:ins='lsl.l #4,d0\n move.l d0,a0' # native fixed screen-pointer calculation
  if pc==0x65c98:ins='nop' # mixed status routine: excluded until ownership is audited
  m=re.fullmatch(r'(b\w+)\.[bw] \$([0-9a-f]+)',ins)
  if m:
   target=int(m[2],16)
   if lo<=target<=hi:ins=f'{m[1]}.w B8_{target:x}'
   else:raise ValueError((hex(pc),ins))
  ins=ins.replace('link.w','link').replace('lea.l','lea').replace('exg.l','exg').replace('btst.b','btst')
  text+=' '+ins.replace(', ', ',')+'\n'
 text+=f'B8_{hi:x}:\n'
text+=''' bsr.l FF1PresentFlag
 bsr.l FF1PresentClock
 jsr $2a130
 jsr $2a270
 clr.w $1c1b4
 jsr $6694e
 jsr $2a130
 lea (B8Frames.l,pc),a0
 addq.l #1,(a0)
 unlk a6
 rts
B8Frames: dc.l 0
'''
o=r/'tmp/build/step5-b8-probe';o.mkdir(parents=True,exist_ok=True);(o/'b8draw.s').write_text(text)
exec(compile(s,str(r/'tools/build_step5_b7_v3.py'),'exec'))

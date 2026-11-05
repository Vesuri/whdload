"""B8 renderer bring-up diagnostic, not a release or accepted candidate."""
from pathlib import Path
import re,os
r=Path(__file__).resolve().parents[1]
# Keep frozen B7 evidence and its builder untouched.
s=(r/'tools/build_step5_b7_v3.py').read_text()
s=s.replace("step5-b7-v3", "step5-b8-v1")
insert='''
# Full drawing runs only when no simulation tick is due. Catch-up retains debt.
s=s.replace('FF1PresentationAfterTick:\\n rts', '''+repr('''FF1PresentationAfterTick:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 bsr.l B8PoseTick
 tst.w B8DrawEnabled(pc)
 beq.b .done
 lea (schedule_context.l,pc),a0
 bsr.l FF1TimeDue
 tst.l d0
 bne.b .done
 bsr.l B8PrepareRenderCopies
 bsr.l B8Draw
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 rts
B8DrawEnabled: dc.w 1
 include "FerrariFormulaOne_RenderPose.s"
 include "FerrariFormulaOne_RenderHistory.s"
 include "FerrariFormulaOne_RenderOwnership.s"
 include "b8draw.s"
''')+''')
s=s.replace(' bsr.l FF1InstallPresentation',' bsr.l FF1InstallPresentation\\n bsr.l B8InstallRenderCopies')
'''
s=s.replace("(o/'reset.bin').write_bytes",insert+"\n(o/'reset.bin').write_bytes",1)
s=s.replace("'-DFF1_PRESENTATION_SPLIT=1'","'-DFF1_RENDER_POSES=1','-DFF1_PRESENTATION_SPLIT=1'")
s=s.replace("args=[str(Path.home()", "(o/'b8draw.s').write_text((r/'tmp/build/step5-b8-v1/b8draw.s').read_text())\nargs=[str(Path.home()",1)
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
  if pc in (0x65772,0x6577c,0x657c4,0x657d6):ins='nop'
  if pc==0x65c98:ins='bsr.l B8PresentPit' # mixed status routine: excluded until ownership is audited
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
o=r/'tmp/build/step5-b8-v1';o.mkdir(parents=True,exist_ok=True);(o/'b8draw.s').write_text(text)
if os.environ.get('B8_DRAW')=='0':
 s=s.replace("step5-b8-v1","step5-b8-v1-control")
 target=r/'tmp/build/step5-b8-v1-control';target.mkdir(parents=True,exist_ok=True);(target/'b8draw.s').write_text(text)
exec(compile(s,str(r/'tools/build_step5_b7_v3.py'),'exec'))

if os.environ.get('B8_DRAW')=='0':
 at=int(re.search(r'^B8DrawEnabled\s+00:([0-9A-F]+)',(o/'fine.list').read_text(),re.M)[1],16)
 for filename,offset in [('fine.bin',at),('fine.slave',32+size+at)]:
  data=bytearray((o/filename).read_bytes());assert data[offset:offset+2]==b'\0\1';data[offset:offset+2]=b'\0\0';(o/filename).write_bytes(data)

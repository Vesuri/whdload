from pathlib import Path
p=Path(__file__).with_name('build_step5_b4_scalar_hooks.py');s=p.read_text()
marker="extra+=' lea scalar_complete(pc),a0"
extra="""
for address,axis in [(0x678de,0),(0x67900,1),(0x67948,0),(0x67976,1)]:
 extra+=f' move.w #$4e75,${address+6:x}\\n'
extra+=' lea (start.l,pc),a2\\n suba.l #5440,a2\\n move.l $1180(a2),a2\\n jsr $20(a2)\\n'
for address,axis in [(0x678de,0),(0x67900,1),(0x67948,0),(0x67976,1)]:
 native=0x32fb4+axis*4
 for before,rem,inc in [(0,4,1),(0,-4,-1),(0x7fffffff,2,1000),(0x80000000,-2,-1000),(0xffffffff,-4,2147483643)]:
  total=inc+rem;delta=(abs(total)//5)*(1 if total>=0 else -1);after=(before+delta)&0xffffffff;nr=total-delta*5;i=len(cases)
  cases.append(dict(kind='heading',site=hex(address),before=before,rem=rem,proposal=inc,expected_q16=after,expected_rem=nr))
  extra+=f' lea heading_shadow+{axis*6}(pc),a0\\n move.l #${before:08x},(a0)\\n move.w #{rem},4(a0)\\n move.l #${before:08x},${native:x}\\n'
  for k in range(1,8):extra+=f' move.l #${0x10101010+k:08x},d{k}\\n'
  for k in range(7):extra+=f' movea.l #${0x20202020+k:08x},a{k}\\n'
  extra+=f' move.l #{inc},d0\\n move.w #31,ccr\\n bsr.w heading_{address:x}\\n movem.l d0-d7/a0-a6,-(sp)\\n move.w ccr,-(sp)\\n move.l sp,a0\\n lea (scalar_results+{i*72}.l,pc),a1\\n moveq #30,d0\\n.copy{i}:\\n move.w (a0)+,(a1)+\\n dbra d0,.copy{i}\\n move.l heading_shadow+{axis*6}(pc),(a1)+\\n move.w heading_shadow+{axis*6+4}(pc),(a1)+\\n move.l ${native:x},(a1)+\\n adda.w #62,sp\\n'
"""
s=s.replace(marker,extra+'\n'+marker);p.write_text(s)

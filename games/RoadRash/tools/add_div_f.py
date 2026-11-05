from pathlib import Path
import re
p=Path('src');s=(p/'cpu_work.s').read_text().replace(' bsr.w f_patterns_init',' bsr.w f_projection_init\n bsr.w f_patterns_init',1);(p/'cpu_work.s').write_text(s)
rows=[]
for l in Path('tmp/ana/game.dis').read_text().splitlines():
 m=re.match(r'([0-9a-f]{6})\s+[0-9a-f]+\s+(.+)',l)
 if m and 0x8970e<=int(m[1],16)<0x898e2:rows.append((int(m[1],16),m[2].strip()))
code=['; F2c prototype: exact reciprocal with remainder correction.','f_projection_init:',' move.l a5,d7',' subi.l #$80000,d7',' lea f_projection_refs(pc),a0','.fix:',' move.l (a0)+,d0',' bmi .patch',' lea _base(pc),a1',' adda.l d0,a1',' add.l d7,(a1)',' bra .fix','.patch:',' move.l a5,a1',' adda.l #$970e,a1',' lea f_projection(pc),a0',' move.w #$4ef9,(a1)',' move.l a0,2(a1)',' rts','f_projection:'];refs=[]
for addr,op in rows:
 code.append(f'fp_{addr:x}:')
 op=re.sub(r'\$(8[0-9a-f]+)',lambda m: 'fp_'+m[1] if 0x8970e<=int(m[1],16)<0x898e2 else m[0],op)
 if op.startswith('divu.w d6, d1'):code.append(' bsr f_div_d1');continue
 if op.startswith('divu.w d6, d2'):code.append(' bsr f_div_d2');continue
 code.append(' '+op)
 if re.search(r'\$[89ab][0-9a-f]{4}',op):
  n=len(refs);refs.append(f'fp_ref_{n}');code.append(f'fp_ref_{n} equ *-4')
code+=['f_projection_refs:']+[' dc.l '+r+'-_base' for r in refs]+[' dc.l -1']
code+=['''f_div_d2:
 move.l d1,-(a7)
 move.l d2,d1
 bsr f_div_d1
 move.l d1,d2
 move.l (a7)+,d1
 tst.w d2
 rts
f_div_d1:
 cmpi.w #256,d6
 bls .native
 movem.l d0/d2-d3/a0,-(a7)
 move.l d1,d3
 lea f_div_cache(pc),a0
 cmp.w (a0),d6
 beq .cached
 move.l #$1000000,d0
 divu.w d6,d0
 move.w d0,2(a0)
 move.w d6,(a0)
.cached:
 move.l d1,d0
 lsr.l #8,d0
 mulu.w 2(a0),d0
 swap d0
 andi.l #$ffff,d0
 move.w d0,d2
 mulu.w d6,d2
 sub.l d2,d3
 cmp.w d6,d3
 bcs .exact
 sub.w d6,d3
 addq.w #1,d0
.exact:
 swap d3
 move.w d0,d3
 move.l d3,d1
 movem.l (a7)+,d0/d2-d3/a0
 tst.w d1
 rts
.native:
 divu.w d6,d1
 rts
f_div_cache: dc.l 0
''']
(p/'projection_reciprocal.s').write_text('\n'.join(code)+'\n')
f=p/'RoadRashHD.s';s=f.read_text().replace('include cpu_work.s','include cpu_work.s\n\tinclude projection_reciprocal.s');f.write_text(s)

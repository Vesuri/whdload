from pathlib import Path
import shutil,json,collections
src=Path('src');dst=Path('tmp/d-main-c-v2-source');shutil.copytree(src,dst)
refs=json.loads(Path('tmp/d-original-hunk/slave-native-refs.json').read_text());by=collections.defaultdict(dict);labels=[]
for r in refs:
 names=[]
 for off,value in r['hits']:
  name=f'public_ref_{len(labels)}';labels.append(name);names.append(f'{name} equ *-{len(bytes.fromhex(r["data"]))-off}')
 by[r['file']][r['line']]=(r,names)
for file,rows in by.items():
 p=dst/file;lines=p.read_text().splitlines();out=[]
 for line,text in enumerate(lines,1):
  out.append(text)
  if line in rows:
   r,names=rows[line];assert text.strip()==r['source'].strip(),(file,line,text,r['source']);out+=names
 p.write_text('\n'.join(out)+'\n')
p=dst/'RoadRashHD.s';s=p.read_text().replace('dc.l -$5000 ; optional WHDLoad-managed stack and guards','dc.l -$50000 ; private main-image relocation feasibility allocation')
s=s.replace('.no_c:\n','\tbsr d_main_init\n.no_c:\n',1).replace('ReadSomeFile:\n','\tinclude public_main.s\n\nReadSomeFile:\n',1);p.write_text(s)
spans=[('C_PHYSICS_FAST',0x8b486,7040,'step_physics_fast_code'),('C_OBJECT_FAST',0x8b02e,0x350,'step_object_fast_code'),('C_COLLISION_GEOMETRY',0x8970e,0x140,'step_collision_geometry_code'),('C_COLLISION_GEOMETRY',0x8989e,0x44,'step_collision_geometry_code+$140'),('C_PHYSICS_AUX',0x8d2c0,1552,'aux_8d2c0'),('C_PHYSICS_AUX',0x8dd66,262,'aux_8dd66'),('C_PHYSICS_AUX',0x8e166,368,'aux_8e166'),('C_PHYSICS_AUX',0x8da5c,174,'aux_8da5c'),('C_LANE_SCAN',0x8d970,0x72,'aux_lane_scan_body')]
code='''; PRIVATE integration prototype. Not production-approved.
d_main_init:
 movem.l d0-d7/a0-a6,-(a7)
 move.l _expmem(pc),a5
 cmpa.l #$200000,a5
 bcs .done
 cmpa.l #$a00000,a5
 bcc .done
 cmpi.l #$3ec,$bc40c
 bne .done
 cmpi.l #5173,$bc410
 bne .done
 lea $5000(a5),a5
 lea $80000,a0
 move.l a5,a1
 move.w #$3c3ec/4-1,d0
.copy:
 move.l (a0)+,(a1)+
 dbf d0,.copy
 move.l a5,d7
 sub.l #$80000,d7
 moveq #0,d2
 move.l #$3c3ec,d3
 move.l a5,a4
 bsr d_main_remap_span
 lea d_main_spans(pc),a6
.spans:
 move.l (a6)+,d2
 bmi .helpers
 move.l (a6)+,d3
 add.l d2,d3
 move.l (a6)+,d0
 lea _base(pc),a4
 adda.l d0,a4
 bsr d_main_remap_span
 bra .spans
.helpers:
 lea _base(pc),a6
 adda.l #d_main_helper_refs-_base,a6
.next_helper:
 move.l (a6)+,d0
 bmi .publish
 lea _base(pc),a1
 adda.l d0,a1
 bsr d_main_adjust
 bra .next_helper
.publish:
 lea expansion_memory(pc),a0
 move.l a5,(a0)
 move.w #$4ef9,$80000
 move.l a5,$80002
 move.l _resload(pc),a2
 jsr (resload_FlushCache,a2)
.done:
 movem.l (a7)+,d0-d7/a0-a6
 rts
; d2/d3: source span offsets, a4: copied span base, d7: relocation delta.
d_main_remap_span:
 lea $bc418,a3
 move.w #5173-1,d6
.fix:
 move.l (a3)+,d0
 cmp.l d2,d0
 bcs .next
 cmp.l d3,d0
 bcc .next
 sub.l d2,d0
 move.l a4,a1
 adda.l d0,a1
 bsr d_main_adjust
.next:
 dbf d6,.fix
 rts
d_main_adjust:
 move.l (a1),d1
 cmpi.l #$80000,d1
 bcs .done
 cmpi.l #$bc3ec,d1
 bcc .done
 add.l d7,(a1)
.done:
 rts
d_main_spans:
'''
for cond,source,size,label in spans:code+=f' IFD {cond}\n dc.l ${source-0x80000:x},${size:x},{label}-_base\n ENDC\n'
code+=' dc.l -1\n';(dst/'public_main.s').write_text(code);code='d_main_helper_refs:\n'
for name in labels:code+=f' IFD {name}\n dc.l {name}-_base\n ENDC\n'
code+=' dc.l -1\n';(dst/'public_refs.s').write_text(code)
p=dst/'RoadRashHD.s';p.write_text(p.read_text()+'\n\tinclude public_refs.s\n')
print('tagged',len(labels),'operands in',len(by),'files')

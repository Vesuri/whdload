from pathlib import Path
import json,re,shutil
root=Path.cwd();src=root/'src';dst=root/'tmp/d-public-boot-v3-source';shutil.copytree(src,dst)
code='''; PRIVATE raw-module relocation prototype. Embedded copper lists stay Chip.
public_boot_title:
 lea public_boot_title_info(pc),a0
 bra public_boot_copy
public_boot_intro:
 lea public_boot_intro_info(pc),a0
public_boot_copy:
 movem.l d0-d7/a0-a6,-(a7)
 move.l _enhanced_framerate(pc),d0
 beq .done
 move.l _expmem(pc),a5
 cmpa.l #$200000,a5
 bcs .done
 cmpa.l #$a00000,a5
 bcs .placement
 cmpa.l #$1000000,a5
 bcs .done
.placement:
 move.l a0,a6
 cmpi.w #$4ef9,$8000
 bne .done
 move.l (a6)+,d0
 cmp.l $8002,d0
 bne .done
 move.w (a6)+,d0
 move.l (a6)+,d1
 move.l (a6)+,d2
 lea $5000(a5),a5
 lea $8000,a0
 move.l a5,a1
.copy:
 move.w (a0)+,(a1)+
 dbf d0,.copy
 move.l a5,d7
 sub.l #$8000,d7
 lea _base(pc),a6
 adda.l d1,a6
.fix:
 moveq #0,d0
 move.w (a6)+,d0
 cmpi.w #-1,d0
 beq .relative
 move.l a5,a1
 adda.l d0,a1
 move.l (a1),d1
 cmpi.l #$8000,d1
 bcs .fix
 cmpi.l #$17e86,d1
 bcc .fix
 add.l d7,(a1)
 bra .fix
.relative:
 lea _base(pc),a6
 adda.l d2,a6
.next:
 moveq #0,d0
 move.w (a6)+,d0
 cmpi.w #-1,d0
 beq .publish
 move.l a5,a1
 adda.l d0,a1
 moveq #0,d1
 move.w (a6)+,d1
 move.l a5,a2
 adda.l d1,a2
 sub.w d0,d1
 subq.w #2,d1
 move.w #$6100,(a1)+
 move.w d1,(a1)
 move.w #$43f9,(a2)+
 move.l (a6)+,(a2)+
 move.w #$4e75,(a2)
 bra .next
.publish:
 move.w #$4ef9,$8000
 move.l a5,$8002
 move.l _resload(pc),a2
 jsr (resload_FlushCache,a2)
.done:
 movem.l (a7)+,d0-d7/a0-a6
 rts
'''
for name,tag,spans,irq in [('TITLE.AMI','title',[(0x86c8,0x878c),(0x128a8,0x1294c)],0x13846),('INTRO.AMI','intro',[(0x8904,0x8a68)],0x98ce)]:
 x=json.loads(Path('tmp/d-raw-modules/'+name+'.json').read_text());refs=set(([0x2e4,0x2f6] if tag=='title' else [0x8a,0x8e,0x92,0x96,0xf2,0xbb6]));pcfix=[]
 for astr,r in x['instructions'].items():
  a=int(astr,16);b=bytes.fromhex(r['bytes']);vals=[int(v,16) for v in re.findall(r'\$([0-9a-f]+)\.l',r['operands'])]
  if r['mnemonic']=='move.l' and r['operands'].startswith(f'#${irq:x},'):vals.append(irq)
  for v in vals:
   if not 0x8000<=v<0x8000+x['file_bytes'] or any(lo<=v<hi for lo,hi in spans):continue
   hits=[i for i in range(0,len(b)-3,2) if b[i:i+4]==v.to_bytes(4,'big')];assert len(hits)==1,(r,v,hits)
   refs.add(a-0x8000+hits[0])
  m=re.fullmatch(r'\$([0-9a-f]+)\(pc\), a1',r['operands'])
  if m and any(lo<=int(m[1],16)<hi for lo,hi in spans):
   assert r['mnemonic']=='lea.l' and len(b)==4
   pcfix.append((a-0x8000,x['file_bytes']+8*len(pcfix),int(m[1],16)))
 entry=int.from_bytes((root/'tmp/game/RoadRash/data'/name).read_bytes()[2:6],'big')
 code+=f'public_boot_{tag}_info:\n dc.l ${entry:x}\n dc.w {x["file_bytes"]//2-1}\n dc.l public_boot_{tag}_refs-_base,public_boot_{tag}_relative-_base\npublic_boot_{tag}_refs:\n'
 for r in sorted(refs):code+=f' dc.w ${r:x}\n'
 code+=f' dc.w -1\npublic_boot_{tag}_relative:\n'
 for a,b,v in pcfix:code+=f' dc.w ${a:x},${b:x}\n dc.l ${v:x}\n'
 code+=' dc.w -1\n';print(name,len(refs),'absolute refs',len(pcfix),'copper LEA stubs')
(dst/'public_boot.s').write_text(code)
p=dst/'RoadRashHD.s';s=p.read_text();s=s.replace('\tmovem.l\t(a7)+,d0-d1/a1-a2\n\n\tmove.l\t$4C98.W,A0','\tbsr public_boot_title\n\tmovem.l\t(a7)+,d0-d1/a1-a2\n\n\tmove.l\t$4C98.W,A0',1)
s=s.replace('\tmovem.l\t(a7)+,d0-d1/a1-a2\n\t\n\tmove.l\t$4C98.W,A0','\tbsr public_boot_intro\n\tmovem.l\t(a7)+,d0-d1/a1-a2\n\t\n\tmove.l\t$4C98.W,A0',1)
s=s.replace('ReadSomeFile:\n',' include public_boot.s\n\nReadSomeFile:\n',1);p.write_text(s)

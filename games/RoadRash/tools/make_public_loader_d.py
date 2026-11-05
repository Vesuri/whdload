from pathlib import Path
import json,re,shutil
root=Path.cwd();src=root/'tmp/d-public-boot-v3-source';dst=root/'tmp/d-public-loader-source';shutil.copytree(src,dst)
x=json.loads(Path('tmp/d-raw-modules/lomain.ami.json').read_text());refs=set();pcfix=[]
for astr,r in x['instructions'].items():
 a=int(astr,16);b=bytes.fromhex(r['bytes']);vals=[int(v,16) for v in re.findall(r'\$([0-9a-f]+)\.l',r['operands'])]
 if r['mnemonic']=='move.l' and re.match(r'#\$(4734|4c50|645c),',r['operands']):vals.append(int(re.match(r'#\$([0-9a-f]+)',r['operands'])[1],16))
 for v in vals:
  if not 0x4720<=v<=0x73b0 or 0x4c98<=v<0x4c9c or 0x4cc4<=v<0x4d60:continue
  hits=[i for i in range(0,len(b)-3,2) if b[i:i+4]==v.to_bytes(4,'big')];assert len(hits)==1,(r,v)
  refs.add(a-0x400+hits[0])
 if '$8000(pc)' in r['operands']:
  assert r['mnemonic'] in ['lea.l','jsr'] and len(b)==4
  pcfix.append((a-0x400,0x6fb0+8*len(pcfix),r['mnemonic']=='lea.l'))
code='''; PRIVATE loader relocation. Shared low-memory ABI/copper cells stay Chip.
public_loader_init:
 movem.l d0-d7/a0-a2/a4-a6,-(a7)
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
 cmpi.l #$6000431e,$400
 bne .done
 move.l a5,a4
 adda.l #$42000,a4
 lea $400,a0
 move.l a4,a1
 move.w #$6fb0/2-1,d0
.copy:
 move.w (a0)+,(a1)+
 dbf d0,.copy
 move.l a4,d7
 sub.l #$400,d7
 lea public_loader_refs(pc),a6
.fix:
 moveq #0,d0
 move.w (a6)+,d0
 cmpi.w #-1,d0
 beq .relative
 move.l a4,a1
 adda.l d0,a1
 move.l (a1),d1
 cmpi.l #$4720,d1
 bcs .fix
 cmpi.l #$73b0,d1
 bhi .fix
 add.l d7,(a1)
 bra .fix
.relative:
 lea public_loader_relative(pc),a6
.next:
 moveq #0,d0
 move.w (a6)+,d0
 cmpi.w #-1,d0
 beq .stack
 move.l a4,a1
 adda.l d0,a1
 moveq #0,d1
 move.w (a6)+,d1
 move.l a4,a2
 adda.l d1,a2
 sub.w d0,d1
 subq.w #2,d1
 move.w #$6100,(a1)+
 move.w d1,(a1)
 move.l (a6)+,(a2)+
 move.l (a6)+,(a2)
 bra .next
.stack:
 move.l a5,a0
 adda.l #$49000,a0
 move.w #$4020/4-1,d0
.guard:
 move.l #$a55aa55a,(a0)+
 dbf d0,.guard
 suba.w #16,a0
 move.l a0,$433a(a4)
 move.l a4,a3
 move.l _resload(pc),a2
 jsr (resload_FlushCache,a2)
.done:
 movem.l (a7)+,d0-d7/a0-a2/a4-a6
 rts
public_loader_refs:
'''
for r in sorted(refs):code+=f' dc.w ${r:x}\n'
code+=' dc.w -1\npublic_loader_relative:\n'
for a,b,lea in pcfix:code+=f' dc.w ${a:x},${b:x}\n dc.w ${"43f9" if lea else "4ef9"},$0000,$8000,${"4e75" if lea else "4e71"}\n'
code+=' dc.w -1\n';(dst/'public_loader.s').write_text(code)
p=dst/'RoadRashHD.s';s=p.read_text().replace('\t\tmove.l\texpansion_memory(pc),A0\t; expansion start','\t\tbsr public_loader_init\n\t\tmove.l\texpansion_memory(pc),A0\t; expansion start',1).replace(' include public_boot.s',' include public_loader.s\n include public_boot.s',1);p.write_text(s)
print('loader references',len(refs),'external PC-relative stubs',len(pcfix))

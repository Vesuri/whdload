from pathlib import Path
import re,shutil
src=Path('tmp/d-public-loader-source');dst=Path('tmp/d-public-boot-hardened-v2-source');shutil.copytree(src,dst)
assets=Path('tmp/game/RoadRash/data')
# Validate every typed relocation operand and every rewritten PC-relative instruction
# against the audited native module before any destination or entry is changed.
checks=[]
for name,base,labels in [('lomain.ami',0x400,['public_loader']),('TITLE.AMI',0x8000,['public_boot_title']),('INTRO.AMI',0x8000,['public_boot_intro'])]:
 b=(assets/name).read_bytes();file=dst/('public_loader.s' if base==0x400 else 'public_boot.s');s=file.read_text()
 for label in labels:
  body=s.split(label+'_refs:\n',1)[1].split(' dc.w -1',1)[0];offsets=[int(v,16) for v in re.findall(r'dc.w \$([0-9a-f]+)',body)]
  body=s.split(label+'_relative:\n',1)[1].split(' dc.w -1',1)[0];offsets+= [int(v,16) for v in re.findall(r'dc.w \$([0-9a-f]+),\$',body)] if base==0x400 else [int(v,16) for v in re.findall(r'dc.w \$([0-9a-f]+),\$',body)]
  # Relative stubs have dc.w instructions on alternate lines for the loader.
  if base==0x400: offsets=offsets[:len(offsets)-8]+[0x43ec,0x4406,0x4430,0x444a]
  check=label+'_check:\n'+''.join(f' dc.w ${v:x}\n dc.l ${int.from_bytes(b[v:v+4],"big"):08x}\n' for v in sorted(set(offsets)))+' dc.w -1\n'
  checks.append(check)
  if base==0x8000:s=s.replace(' dc.l '+label+'_refs-_base',' dc.l '+label+'_check-_base\n dc.l '+label+'_refs-_base')
 if base==0x400:
  s=s.replace(' move.l a5,a4\n', ' lea public_loader_check(pc),a0\n lea $400,a1\n bsr public_boot_validate\n bne .done\n move.l a5,a4\n',1)
 elif name=='TITLE.AMI':
  s=s.replace(' move.w (a6)+,d0\n', ' move.w (a6)+,d6\n move.l (a6)+,d0\n lea _base(pc),a0\n adda.l d0,a0\n lea $8000,a1\n bsr public_boot_validate\n bne .done\n move.w d6,d0\n',1)
 file.write_text(s)
p=dst/'public_boot.s';s=p.read_text();s+='''
; a0: six-byte (offset, expected longword) records terminated by -1.
; a1: native module base. Return Z only if every audited operand matches.
; Check before copying or publishing, preserving all caller registers.
public_boot_validate:
 movem.l d0-d1/a0-a2,-(a7)
.next:
 moveq #0,d0
 move.w (a0)+,d0
 cmpi.w #-1,d0
 beq .done
 move.l a1,a2
 adda.l d0,a2
 move.l (a0)+,d1
 cmp.l (a2),d1
 beq .next
.done:
 movem.l (a7)+,d0-d1/a0-a2
 rts
'''+''.join(checks);p.write_text(s)
# Helpers require the larger optional allocation, including diagnostic builds.
p=dst/'RoadRashHD.s';s=p.read_text();s=s.replace('\t\tbsr public_loader_init',' IFD C_PUBLIC_MAIN\n\t\tbsr public_loader_init\n ENDC').replace('\tbsr public_boot_title',' IFD C_PUBLIC_MAIN\n\tbsr public_boot_title\n ENDC').replace('\tbsr public_boot_intro',' IFD C_PUBLIC_MAIN\n\tbsr public_boot_intro\n ENDC').replace(' include public_loader.s\n include public_boot.s',' IFD C_PUBLIC_MAIN\n include public_loader.s\n include public_boot.s\n ENDC');p.write_text(s)

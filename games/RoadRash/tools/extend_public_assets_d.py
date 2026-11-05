from pathlib import Path
import shutil,json
src=Path('tmp/d-public-assets-source');dst=Path('tmp/d-public-assets-v2-source');shutil.copytree(src,dst)
p=dst/'RoadRashHD.s';s=p.read_text().replace('dc.l -$56000 ; optional main/bootstrap/stacks and 12 image-header slots','dc.l -$5c000 ; optional runtime plus CPU-only image headers');p.write_text(s)
p=dst/'public_main.s';s=p.read_text().replace(' move.l d0,(a0)\n move.l a5,a1\n adda.l #$2fd9c,a1',' move.l d0,(a0)\n bsr public_asset_init\n move.l a5,a1\n adda.l #$2fd9c,a1',1);p.write_text(s)
p=dst/'public_assets.s';s=p.read_text().replace(' bra .done\n.copy:', ''' bra .fixed
.copy:''',1).replace(' moveq #0,d0\n move.w (a0),d0', ' move.w #2044,d2\n bra .copy_header\n.fixed:\n lea public_asset_fixed(pc),a3\n move.l public_asset_pool(pc),a1\n adda.l #$6000,a1\n moveq #2,d2\n.fixed_next:\n cmpa.l (a3),a0\n beq .fixed_copy\n addq.l #8,a3\n adda.l #$2000,a1\n dbf d2,.fixed_next\n bra .done\n.fixed_copy:\n addq.l #4,a3\n move.w #8188,d2\n.copy_header:\n moveq #0,d0\n move.w (a0),d0',1).replace(' cmpi.w #2044,d0',' cmp.w d2,d0',1)
s+='''
; Descriptor readers use MOVEA.L through a typed pointer cell, the same six
; bytes and CCR behavior as LEA absolute. Loader/depacker addresses stay Chip.
; These rendering consumers are outside every separate C code-copy span.
public_asset_init:
 movem.l d0-d2/a0-a3,-(a7)
 lea public_asset_readers(pc),a0
.check:
 move.l (a0)+,d0
 bmi .install
 move.l a5,a1
 adda.l d0,a1
 move.w (a0)+,d1
 cmp.w (a1),d1
 bne .done
 move.l (a0)+,d1
 cmp.l 2(a1),d1
 bne .done
 addq.l #4,a0
 bra .check
.install:
 lea public_asset_readers(pc),a0
.next:
 move.l (a0)+,d0
 bmi .done
 move.l a5,a1
 adda.l d0,a1
 move.w (a0)+,d1
 subi.w #$2180,d1
 move.w d1,(a1)
 addq.l #4,a0
 move.l (a0)+,d0
 lea _base(pc),a2
 adda.l d0,a2
 move.l a2,2(a1)
 bra .next
.done:
 movem.l (a7)+,d0-d2/a0-a3
 rts
public_asset_fixed:
 dc.l $19a7e,$19a7e
 dc.l $38c84,$38c84
 dc.l $5c2cc,$5c2cc
public_asset_readers:
'''
x=json.load(open('tmp/d-original-hunk/reachable.json'))['instructions']
for idx,sites in enumerate([[0xb0520,0xb0538],[0xb032c,0xb03fa,0xb0e80,0xb1de8,0xb1e3c],[0xafe94,0xaff80,0xb0e1e,0xb1ee6,0xb1f2c]]):
 for addr in sites:
  r=x[hex(addr-0x80000)];b=bytes.fromhex(r['bytes']);assert len(b)==6 and r['mnemonic']=='lea.l'
  s+=f' dc.l ${addr-0x80000:x}\n dc.w ${b[:2].hex()}\n dc.l ${b[2:].hex()},public_asset_fixed+{idx*8+4}-_base\n'
s+=' dc.l -1\n';p.write_text(s)

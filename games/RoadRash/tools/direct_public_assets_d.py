from pathlib import Path
import shutil
src=Path('tmp/d-public-assets-v2-source');dst=Path('tmp/d-public-assets-v3-source');shutil.copytree(src,dst)
p=dst/'public_assets.s';s=p.read_text().replace(' move.l d1,(a3)\n.done:', ' move.l d1,(a3)\n cmpa.l #$1000,a3\n bcs .done\n bsr public_asset_publish_fixed\n.done:',1)
a=s.index('.install:\n',s.index('public_asset_init:'));b=s.index('.done:\n',a)
s=s[:a]+'''.install:
 lea public_asset_image(pc),a0
 move.l a5,(a0)
'''+s[b:]
a=s.index('public_asset_fixed:')
s=s[:a]+'''public_asset_image:
 dc.l 0
; Called only while loading a fixed SET, after the complete descriptor copy.
; Retain direct LEA operands for frame-time speed; publish and flush all typed
; reader operands together. The enclosing relocation wrapper saves registers.
public_asset_publish_fixed:
 move.l public_asset_image(pc),a3
 cmpa.l #0,a3
 beq .done
 lea public_asset_readers(pc),a0
.next:
 move.l (a0)+,d0
 bmi .flush
 move.l a3,a1
 adda.l d0,a1
 addq.l #6,a0
 move.l (a0)+,d0
 lea _base(pc),a2
 adda.l d0,a2
 move.l (a2),2(a1)
 bra .next
.flush:
 move.l _resload(pc),a2
 jsr (resload_FlushCache,a2)
.done:
 rts
'''+s[a:]
s=s.replace('; Descriptor readers use MOVEA.L through a typed pointer cell, the same six\n; bytes and CCR behavior as LEA absolute. Loader/depacker addresses stay Chip.', '; Descriptor readers retain direct LEA operands. Loader/depacker addresses\n; stay Chip. Preflight all sites once before permitting reader publication.')
p.write_text(s)

from pathlib import Path
p=Path('src/TFXHD.s');s=p.read_bytes().decode().replace('\r\n','\n')
s=s.replace('        bsr     fix_new_chip_pointers\n\n','')
a=s.index('; The merged executable lost');b=s.index('; d0 = target address delta;',a)
s=s[:a]+'''; The merged executable lost its chip attributes. Retain only DMA objects in
; chip RAM. Palette snapshots, sprite pointer tables and screen selectors are
; CPU-only and stay in fast RAM, as do all PL_GA objects used by the slave.
NEW_CHIP_SIZE = $22760

split_new_chip_data:
        tst.b   new_fast_data(pc)
        beq     .done
        movem.l d0-d7/a0-a6,-(sp)
        move.l  $4.w,a6
        move.l  #NEW_CHIP_SIZE,d0
        move.l  #MEMF_CHIP!MEMF_CLEAR,d1
        jsr     _LVOAllocMem(a6)
        tst.l   d0
        bne.b   .allocated
        pea     outofmemory(pc)
        pea     (TDREASON_FAILMSG).w
        move.l  _resload(pc),a0
        jmp     resload_Abort(a0)
.allocated:
        move.l  d0,a4
        lea     new_chip_ranges(pc),a5
.relocate:
        move.l  (a5)+,d1
        bmi.b   .copy_ranges
        bsr.b   .range
        move.l  a3,d0
        sub.l   a2,d0
        lea     new_chip_ranges(pc),a0
        add.l   (a5)+,a0
        bsr     apply_new_chip_relocs
        bra.b   .relocate
.copy_ranges:
        ; Relocate every pointer before copying any initialized objects.
        lea     new_chip_ranges(pc),a5
.copy_next:
        move.l  (a5)+,d1
        bmi.b   .copied
        bsr.b   .range
        addq.l  #4,a5
        lsr.l   #2,d3
        subq.w  #1,d3
.copy:
        move.l  (a2)+,(a3)+
        dbf     d3,.copy
        bra.b   .copy_next
.copied:
        movem.l (sp)+,d0-d7/a0-a6
.done:
        rts
.range:
        lsl.w   #2,d1
        lea     sections(pc),a2
        move.l  (a2,d1.w),a2
        add.l   (a5)+,a2
        move.l  (a5)+,d3
        move.l  a4,a3
        add.l   (a5)+,a3
        rts

; Section, source offset, length, chip offset, relative relocation-table address.
; Keep the video buffers 8-byte aligned, as required by their initialization.
new_chip_ranges:
        dc.l 1,$00d98,$0173c,$00000,chip_reloc_mouse-new_chip_ranges
        dc.l 1,$027e0,$01b50,$01740,chip_reloc_display-new_chip_ranges
        dc.l 1,$04938,$000c8,$03290,chip_reloc_audio-new_chip_ranges
        dc.l 2,$07cec,$1f408,$03358,chip_reloc_video-new_chip_ranges
        dc.l -1

''' + s[b:]
a=s.index('; PatchSeg\'s PL_GA');b=s.index('        include "chip_reloc_new.i"',a)
s=s[:a]+'new_fast_data: dc.w 0\n'+s[b:]
p.write_bytes(s.replace('\n','\r\n').encode())
p=Path('tools/generate_chip_relocs.py');s=p.read_text();s=s.replace('ranges=[(1,0xd98,0x4a00),(2,0x7cec,0x270f4)]','ranges=[(1,0xd98,0x24d4),(1,0x27e0,0x4330),(1,0x4938,0x4a00),(2,0x7cec,0x270f4)]')
s=s.replace("'; Data: $d98..$49ff; BSS video memory: $7cec..$270f3.'","'; CPU-only palettes, sprite pointer tables and page selectors are excluded.'")
s=s.replace("lines.append('chip_reloc_data:' if ri==0 else 'chip_reloc_bss:')","lines.append('chip_reloc_'+['mouse','display','audio','video'][ri]+':')")
s=s.replace('dict(target=tgt,source=src,count=len(offsets),offsets=offsets)','dict(target=tgt,start=start,end=end,chip_offset=[0,0x1740,0x3290,0x3358][ri],source=src,count=len(offsets),offsets=offsets)');p.write_text(s)

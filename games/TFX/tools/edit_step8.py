from pathlib import Path
p=Path('src/TFXHD.s');s=p.read_bytes().decode();s=s.replace('\r\n','\n')
s=s.replace('.chip\n    or.w    #MEMF_CHIP,d1   ; wrong hunk, fix it','.chip\n    IFD CHIP_ONLY\n    ELSE\n    ; Keep the original placement on 020/030/060 and with original rendering.\n    btst.b  #AFB_68040,attnflags+3(pc)\n    beq.b   .keepchip\n    btst.b  #AFB_68060,attnflags+3(pc)\n    bne.b   .keepchip\n    CHECK_NO_FAST_ALLOC\n    bne.b   .keepchip\n    and.w   #~MEMF_CHIP,d1\n    or.w    #MEMF_FAST,d1\n    movem.l a0,-(sp)\n    lea     new_fast_data(pc),a0\n    st.b    (a0)\n    movem.l (sp)+,a0\n    bra.b   .no_dataseg\n.keepchip\n    ENDC\n    or.w    #MEMF_CHIP,d1   ; wrong hunk, fix it')
needle='        move.l  d7,a1\n        move.l  _resload(pc),a2\n        jsr\tresload_PatchSeg(a2)'
assert s.count(needle)==2
s=s.replace(needle,'        bsr     split_new_chip_data\n\n'+needle,1)
s=s.replace('.no_060_patches\n\n        CHECK_NO_FAST_ALLOC','.no_060_patches\n\n        bsr     fix_new_chip_pointers\n\n        CHECK_NO_FAST_ALLOC')
pos=s.index(';;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;',s.index('.not020v\n'))
code='''; The merged executable lost its chip attributes. Keep its ordinary data and BSS
; in fast RAM, and copy only the original DMA groups to one chip allocation.
; HUNK_RELOC32 sites include code operands and pointer tables (not scan guesses).
NEW_CHIP_DATA_START = $d98
NEW_CHIP_DATA_SIZE  = $4a00-NEW_CHIP_DATA_START
NEW_CHIP_BSS_START  = $7cec
NEW_CHIP_BSS_SIZE   = $270f4-NEW_CHIP_BSS_START

split_new_chip_data:
        tst.b   new_fast_data(pc)
        beq     .done
        movem.l d0-d7/a0-a6,-(sp)
        move.l  $4.w,a6
        move.l  #NEW_CHIP_DATA_SIZE+NEW_CHIP_BSS_SIZE,d0
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
        lea     new_chip_base(pc),a0
        move.l  d0,(a0)
        move.l  sections+4(pc),a2
        add.l   #NEW_CHIP_DATA_START,a2
        sub.l   a2,d0
        lea     new_chip_data_delta(pc),a0
        move.l  d0,(a0)
        lea     chip_reloc_data(pc),a0
        bsr     apply_new_chip_relocs
        move.l  a4,d0
        add.l   #NEW_CHIP_DATA_SIZE-NEW_CHIP_BSS_START,d0
        sub.l   sections+8(pc),d0
        lea     chip_reloc_bss(pc),a0
        bsr     apply_new_chip_relocs
        ; Copy after relocation so embedded pointers also use chip addresses.
        move.l  a4,a1
        move.w  #NEW_CHIP_DATA_SIZE/4-1,d0
.copy:
        move.l  (a2)+,(a1)+
        dbf     d0,.copy
        movem.l (sp)+,d0-d7/a0-a6
.done:
        rts

; d0 = target address delta; a0 = groups terminated by a negative section.
apply_new_chip_relocs:
        move.w  (a0)+,d1
        bmi.b   .done
        lsl.w   #2,d1
        lea     sections(pc),a1
        move.l  (a1,d1.w),a1
        move.w  (a0)+,d2
        subq.w  #1,d2
.next:
        move.l  (a0)+,d1
        add.l   d0,(a1,d1.l)
        dbf     d2,.next
        bra.b   apply_new_chip_relocs
.done:
        rts

; PatchSeg's PL_GA resolves the original segment layout. Move these three
; slave-held addresses too; all other PL_GA objects stay in their old sections.
fix_new_chip_pointers:
        tst.b   new_fast_data(pc)
        beq.b   .done
        movem.l d0/a0,-(sp)
        move.l  new_chip_data_delta(pc),d0
        lea     _logbase_ptr(pc),a0
        add.l   d0,(a0)
        lea     _current_page_ptr(pc),a0
        add.l   d0,(a0)
        lea     _sprogtab_ptr(pc),a0
        add.l   d0,(a0)
        movem.l (sp)+,d0/a0
.done:
        rts

new_fast_data: dc.w 0
new_chip_base: dc.l 0
new_chip_data_delta: dc.l 0
        include "chip_reloc_new.i"

'''
s=s[:pos]+code+s[pos:];p.write_bytes(s.replace('\n','\r\n').encode())
p=Path('src/Makefile');s=p.read_text().replace('$(WHDLOADER) : $(SOURCE)','$(WHDLOADER) : $(SOURCE) chip_reloc_new.i');p.write_text(s)

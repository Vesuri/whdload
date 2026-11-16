; The objects' images in fast memory for the ECS game on the 68020 and up (docs/performance.md,
; ECS plan step 10; docs/internals.md, "ECS improvements", item 6): the AGA slave's plan
; step 13 (RobinSonSRequiemAga.asm, _objpatch; docs/internals.md, "AGA improvements") at
; the ECS sites ("The AGA's sites in the ECS game", item 14). The 3D view's sprite routine
; (hunk 1 +$d090) finds an object's image at +$d0a0, adda.l (a2),a2 (an image of the
; resource heap in chip: type 24 or 26 at +0, width - 1 at +2, height - 1 at +4, the pixels
; from +6, two bytes sooner than the AGA's), and reads it only through a2: its header, the
; scaled pixels and the pick test's pixel (from lea (6,a2,d1.l) at +$d18e, +$d246, +$d2ba).
; +$d0a0 adda.l (a2),a2 and cmpi.b #24,(a2) become jsr _objimg, which gives the routine a
; copy in fast memory: a cache of OSLOTS images in an OBJMAX room from the fast memory
; list, each at its image's address modulo 16, found by the image's address. The heap
; changes only through its top <+$d3b6>: an allocation (+$7b20 add.l d1,<+$d3b6>), the
; compaction that moves the blocks above a freed one down (+$78ce sub.l d1,<+$d3b6>) and
; its reset (+$7322 move.l d0,<+$d3b6>); each becomes a jsr that does the same and empties
; the cache. A full cache is emptied too. Each copy holds OMARGIN bytes after the image as
; well. MAPCHECK compares each image given with the original, counting differing longwords
; in O_BAD. All sites are checked first; no room: no patch. OBJCOPY_OFF (a test define):
; not patched. RobinsonSRequiemEcs.asm calls _objpatch when WHDLoad's AttnFlags have the
; 68020 bit. Assembled for the 68020: hunk 1 offsets above $7fff are base displacements.

        MC68020

OBJMAX  equ     65536                   ; the cache's bytes
OSLOTS  equ     128                     ; its images
OMARGIN equ     64                      ; bytes copied after an image: the scaled reads'
                                        ; rounding past its last pixel reads the same
OHEAD   equ     6                       ; the image's header

H1_HEAPTOP      = $d3b6                 ; the resource heap's top

_objpatch
        IFND OBJCOPY_OFF
        movem.l d0-d2/a0-a2/a6,-(a7)
        move.l  _hunk1(pc),a0
        lea     .sites(pc),a2
.chk    move.l  (a2)+,d0
        bmi     .ok
        move.w  (a2)+,d1
        cmp.w   (a0,d0.l),d1
        bne     .x
        move.l  a0,d2
        add.l   (a2)+,d2
        tst.l   -4(a2)
        bmi     .chk                    ; no address operand
        cmp.l   2(a0,d0.l),d2
        bne     .x
        bra     .chk
.ok     move.l  #OBJMAX+OSLOTS*8+16,d0
        moveq   #MEMF_FAST|MEMF_PUBLIC,d1
        move.l  4.w,a6
        jsr     _LVOAllocMem(a6)
        tst.l   d0
        beq     .x
        add.l   #15,d0
        and.w   #-16,d0
        lea     _ovars(pc),a1
        move.l  d0,O_TAB(a1)
        add.l   #OSLOTS*8,d0
        move.l  d0,O_BUF(a1)
        move.l  d0,O_FREE(a1)
        add.l   #OBJMAX,d0
        move.l  d0,O_END(a1)
        move.l  _hunk1(pc),a0
        lea     .jsrs(pc),a2
.put    move.l  (a2)+,d0
        beq     .done
        move.l  (a2)+,d1
        move.w  #$4eb9,(a0,d0.l)
        lea     .jsrs(pc,d1.l),a1
        move.l  a1,2(a0,d0.l)
        bra     .put
.done   move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.x      movem.l (a7)+,d0-d2/a0-a2/a6
        ENDC
        rts
; offset, opcode, the address operand's hunk 1 offset (-1: the next word instead)
.sites  dc.l    $d0a0
        dc.w    $d5d2
        dc.l    -1
        dc.l    $d0a2
        dc.w    $0c12
        dc.l    -1
        dc.l    $d0a4
        dc.w    $0018
        dc.l    -1
        dc.l    $d18e                   ; the pixels from +6
        dc.w    $41f2
        dc.l    -1
        dc.l    $d190
        dc.w    $1806
        dc.l    -1
        dc.l    $7b20
        dc.w    $d3b9
        dc.l    H1_HEAPTOP
        dc.l    $78ce
        dc.w    $93b9
        dc.l    H1_HEAPTOP
        dc.l    $7322
        dc.w    $23c0
        dc.l    H1_HEAPTOP
        dc.l    -1
.jsrs   dc.l    $d0a0,_objimg-.jsrs
        dc.l    $7b20,_heapadd-.jsrs
        dc.l    $78ce,_heapsub-.jsrs
        dc.l    $7322,_heapset-.jsrs
        dc.l    0

_heapadd
        move.l  a0,-(a7)
        move.l  _hunk1(pc),a0
        add.l   d1,(H1_HEAPTOP,a0)
        bra     _heapch
_heapsub
        move.l  a0,-(a7)
        move.l  _hunk1(pc),a0
        sub.l   d1,(H1_HEAPTOP,a0)
        bra     _heapch
_heapset
        move.l  a0,-(a7)
        move.l  _hunk1(pc),a0
        move.l  d0,(H1_HEAPTOP,a0)
_heapch lea     _ovars(pc),a0
        st      O_FLUSH(a0)
        move.l  (a7)+,a0
        rts

; +$d0a0: a2 the object's image (its offset at (a2) added); flags as cmpi.b #24,(a2)
_objimg adda.l  (a2),a2
        cmp.b   #24,(a2)
        beq     .t
        cmp.b   #26,(a2)
        bne     .cmp
.t      movem.l d0-d3/a0-a1/a3,-(a7)
        lea     _ovars(pc),a3
        tst.b   O_FLUSH(a3)
        beq     .look
.empty  sf      O_FLUSH(a3)
        clr.l   O_N(a3)
        move.l  O_BUF(a3),O_FREE(a3)
.look   move.l  O_TAB(a3),a0
        move.l  O_N(a3),d0
        bra     .lt
.l      cmp.l   (a0),a2
        beq     .hit
        addq.l  #8,a0
.lt     dbf     d0,.l
        bsr     .size                   ; not there: its bytes
        cmp.l   #OBJMAX/2,d0
        bhi     .out
        cmp.l   #OSLOTS,O_N(a3)
        bhs     .empty
        move.l  a2,d2
        moveq   #15,d3
        and.l   d3,d2                   ; the image's address modulo 16
        move.l  O_FREE(a3),d1
        add.l   d3,d1
        and.w   #-16,d1
        add.l   d2,d1                   ; the copy
        add.l   #OMARGIN,d0             ; and the bytes after it
        move.l  d1,d3
        add.l   d0,d3
        addq.l  #3,d3
        cmp.l   O_END(a3),d3
        bhi     .empty
        move.l  d3,O_FREE(a3)
        move.l  a2,(a0)+                ; the new entry
        move.l  d1,(a0)
        subq.l  #4,a0
        addq.l  #1,O_N(a3)
        moveq   #3,d3
        and.l   d2,d3                   ; the offset in the first longword
        add.l   d3,d0
        addq.l  #3,d0
        lsr.l   #2,d0                   ; the longwords
        move.l  a2,a1
        suba.l  d3,a1
        move.l  d1,a3
        suba.l  d3,a3
        bra     .ct
.c      move.l  (a1)+,(a3)+
.ct     dbf     d0,.c
.hit
        IFD MAPCHECK
        bsr     .size
        lsr.l   #2,d0
        move.l  a2,a1
        move.l  4(a0),a3
        bra     .kt
.k      cmpm.l  (a1)+,(a3)+
        beq     .kt
        lea     _ovars(pc),a1           ; one count a call is enough
        addq.l  #1,O_BAD(a1)
        bra     .kd
.kt     dbf     d0,.k
.kd     lea     _ovars(pc),a3
        addq.l  #1,O_CALLS(a3)
        ENDC
        move.l  4(a0),a2
.out    movem.l (a7)+,d0-d3/a0-a1/a3
.cmp    cmp.b   #24,(a2)
        rts
; d0 the image's bytes, its header's too
.size   moveq   #0,d0
        move.w  2(a2),d0
        addq.l  #1,d0
        moveq   #0,d1
        move.w  4(a2),d1
        addq.l  #1,d1
        mulu.l  d1,d0
        addq.l  #OHEAD,d0
        rts

_ovars
_otab   dc.l    0                       ; the cache's entries: image, copy
_obuf   dc.l    0                       ; its room
_oend   dc.l    0                       ; and the room's end
_ofree  dc.l    0                       ; the next copy's room
_on     dc.l    0                       ; the entries
_obad   dc.l    0                       ; MAPCHECK: calls with a copy that differed
_ocalls dc.l    0                       ; MAPCHECK: calls with a copy
_oflush dc.b    0                       ; the heap changed: the cache to be emptied
        even
O_TAB   equ     _otab-_ovars
O_BUF   equ     _obuf-_ovars
O_END   equ     _oend-_ovars
O_FREE  equ     _ofree-_ovars
O_N     equ     _on-_ovars
O_BAD   equ     _obad-_ovars
O_CALLS equ     _ocalls-_ovars
O_FLUSH equ     _oflush-_ovars

        MC68000

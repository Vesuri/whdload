; CUSTOM2: triple buffering for the Road Drawer.
;
; The original drawer renders into the back View, shows it (h3 $175e through
; -32106(a4): LoadView and the front/back exchange), then waits for the next
; field (WaitTOF) before it may draw into the old front. Every frame lasts a
; whole number of fields and the drawer idles for the rest of the field it
; finishes in. With a third View it starts the next frame at once: the buffer
; it draws into next left the display one LoadView earlier.
;
; The game's two Views are V0 -22208(a4) and V1 -22190(a4), with RastPorts
; RP0 -20304(a4) and RP1 -20204(a4); the front and back View are -23344(a4)
; and -23350(a4), the front and back RastPort -23358(a4) and -22404(a4).
; The third View V2 and its bitmap live in one chip block that exists only
; while the drawer runs. The game frees its ViewPorts' intermediate copper
; lists after MrgCop, so V2's hardware copper list is a copy of the front
; View's (sprites, palette split at the dashboard) with the bitplane pointers
; moved to V2's planes, renewed every time V2 is shown. V0's and V1's lists
; differ only in those pointers.
;
; Three renderer states are per buffer. Two are indexed by -22472(a4) (0 for
; V0, 1 for V1): the gear-lever redraw handshake (desired -29902/-29901(a4),
; drawn -29900/-29899(a4); the simulation always sets both desired bytes
; alike) and the cluster cache (speed -26360(a4), RPM -26356(a4)); index 2
; selects V2's own copies, tb_ack, tb_speed and tb_rpm. The third is the
; steering-wheel image (h4 $2406): -29618(a4) holds the state drawn into this
; buffer, -29620(a4) the other buffer's, and the two swap after every frame.
; With three buffers tb_wheel keeps one state per buffer and loads this
; buffer's into -29618(a4) before the comparison.
;
; Whenever the simulation holds the drawer (-23376(a4): pause, crash, end of
; race), the drawer first returns to the two-buffer state. If V2 is on
; display, its picture and per-buffer state are copied into the back View,
; which is shown instead. Code outside the drawer only ever sees V0 and V1.

TB_GFX_BLTBITMAP = -30
TB_GFX_WAITBLIT = -228
TB_GFX_INITVIEW = -360
TB_GFX_INITBITMAP = -390
TB_EXEC_ALLOCMEM = -198
TB_EXEC_FREEMEM = -210

TB_VIEW = 0                    ; View, 18 bytes
TB_VPORT = 20                  ; ViewPort, 40 bytes
TB_RINFO = TB_VPORT+40         ; RasInfo, 12 bytes
TB_BITMAP = TB_RINFO+12        ; BitMap, 40 bytes
TB_RPORT = TB_BITMAP+40        ; RastPort, 100 bytes
TB_CPRLIST = TB_RPORT+100      ; struct cprlist, 10 bytes (+2)
TB_COPPER = TB_CPRLIST+12      ; hardware copper list
TB_COPPER_MAX = 256            ; instructions; the game's lists have 123
TB_PLANES = TB_COPPER+4*TB_COPPER_MAX ; five 320x200 planes
TB_PLANE = 8000
TB_SIZE = TB_PLANES+5*TB_PLANE

; Drawer loop top, h4 $00b88 (replaces the hold loop): wait while held as the
; original does, after returning to two buffers; start triple buffering when
; the hold ends. The drawer task is created held, but the simulation may
; release it before it first runs, so a start is due until one is tried.
tb_hold:
    tst.w -23376(a4)
    beq.b .run
    bsr tb_stop
.spin
    move.w #1,-22458(a4)      ; displaced hold acknowledgement
    tst.w -23376(a4)
    bne.b .spin
.run
    move.w tb_start_due(pc),d0
    beq.b .done
    bsr tb_start
.done
    rts

; Publication, h4 $00c0a (replaces "show the back View, WaitTOF").
tb_swap:
    move.l tb_mem(pc),d0
    bne.b .triple
    move.l -23350(a4),-(sp)
    jsr -32106(a4)            ; displaced: h3 $175e buffer exchange
    addq.w #4,sp
    jmp -32130(a4)            ; displaced: WaitTOF
.triple
    movem.l d2/a0-a2,-(sp)
    move.l -23350(a4),a2      ; the finished frame
    cmp.l tb_mem(pc),a2
    bne.b .show
    move.l -23344(a4),a0
    bsr tb_copper             ; V2 is off the display: renew its list
.show
    move.l a2,-(sp)
    jsr -32202(a4)            ; root $7aaa LoadView
    addq.w #4,sp
    move.l -31782(a4),d2      ; field counter at this LoadView
    move.l -23344(a4),a0      ; the previous front
    bsr tb_third              ; a1: next back, front before a0
    bsr tb_wait_free
    lea tb_loaded(pc),a0
    move.l d2,(a0)
    move.l a2,a0
    move.l a1,a2
    bsr tb_set
    movem.l (sp)+,d2/a0-a2
    rts

; Wait until the View that was front before the last LoadView (tb_loaded)
; is off the display. LoadView takes effect at the next vertical blank; two
; counted fields also cover a LoadView between the blank and the VBL server.
tb_wait_free:
    movem.l d0-d1/a0-a1,-(sp)
.wait
    move.l -31782(a4),d0
    sub.l tb_loaded(pc),d0
    cmp.l #2,d0
    bge.b .done
    jsr -32130(a4)            ; WaitTOF
    bra.b .wait
.done
    movem.l (sp)+,d0-d1/a0-a1
    rts

; a0: front View, a2: back View. Sets the game's front/back Views and
; RastPorts as h3 $175e does.
tb_set:
    move.l a0,-(sp)
    move.l a0,-23344(a4)
    move.l a2,-23350(a4)
    bsr tb_rport
    move.l a0,-23358(a4)
    move.l a2,a0
    bsr tb_rport
    move.l a0,-22404(a4)
    move.l (sp)+,a0
    rts

; a0, a2: two different Views of V0, V1 and V2. Out: a1 = the third.
tb_third:
    lea -22208(a4),a1
    cmp.l a0,a1
    beq.b .not0
    cmp.l a2,a1
    bne.b .done
.not0
    lea -22190(a4),a1
    cmp.l a0,a1
    beq.b .not1
    cmp.l a2,a1
    bne.b .done
.not1
    move.l tb_mem(pc),a1
.done
    rts

; a0: V0 or V1. Out: a1 = the other one.
tb_other:
    lea -22208(a4),a1
    cmp.l a0,a1
    bne.b .done
    lea -22190(a4),a1
.done
    rts

; a0: one of V0, V1 and V2. Out: a0 = its RastPort.
tb_rport:
    move.l a1,-(sp)
    lea -22208(a4),a1
    cmp.l a0,a1
    bne.b .not0
    lea -20304(a4),a0
    bra.b .done
.not0
    lea -22190(a4),a1
    cmp.l a0,a1
    bne.b .not1
    lea -20204(a4),a0
    bra.b .done
.not1
    move.l tb_mem(pc),a0
    lea TB_RPORT(a0),a0
.done
    move.l (sp)+,a1
    rts

; a0: V0 or V1. Out: d0.l = its per-buffer index.
tb_index_of:
    move.l a1,-(sp)
    moveq #0,d0
    lea -22208(a4),a1
    cmp.l a0,a1
    beq.b .done
    moveq #1,d0
.done
    move.l (sp)+,a1
    rts

; a0: source View, a1: destination View. Copies the whole picture.
tb_copy_picture:
    movem.l d0-d7/a0-a2/a6,-(sp)
    move.l (a0),a0
    move.l 36(a0),a0
    move.l 4(a0),a0           ; source BitMap
    move.l (a1),a1
    move.l 36(a1),a1
    move.l 4(a1),a1           ; destination BitMap
    moveq #0,d0
    moveq #0,d1
    moveq #0,d2
    moveq #0,d3
    move.l #320,d4
    move.l #200,d5
    move.l #$c0,d6
    moveq #-1,d7
    sub.l a2,a2
    move.l -31786(a4),a6
    jsr TB_GFX_BLTBITMAP(a6)
    jsr TB_GFX_WAITBLIT(a6)
    movem.l (sp)+,d0-d7/a0-a2/a6
    rts

; a0: V0 or V1, the front View. Copies its hardware copper list into V2's,
; moving each bitplane pointer by the distance between the two BitMaps'
; planes. A pointer is a move to BPLxPTH directly followed by the move to
; BPLxPTL. The first pass only checks, the second writes.
; Out: d0 = 1 and Z clear if copied, d0 = 0 and Z set if the list is not
; as expected (V2's list is then unchanged).
tb_copper:
    movem.l d1-d6/a0-a5,-(sp)
    move.l (a0),a1
    move.l 36(a1),a1
    move.l 4(a1),a1
    lea 8(a1),a1              ; a1: front planes
    move.l tb_mem(pc),a2
    lea TB_COPPER(a2),a3      ; a3: V2's list
    lea TB_BITMAP+8(a2),a2    ; a2: V2's planes
    move.l 4(a0),a0           ; v_LOFCprList
    move.l 4(a0),a0           ; a0: start of the front list
    moveq #0,d6               ; pass: 0 checks, 1 writes
.pass
    move.l a0,a4
    move.l a3,a5
    move.w #TB_COPPER_MAX,d5  ; instructions left
.next
    subq.w #1,d5
    bmi.b .bad
    move.l (a4)+,d0
    move.l d0,d1
    swap d1                   ; d1.w: first word
    btst #0,d1
    bne.b .copy               ; WAIT, SKIP or the end
    and.w #$1fe,d1
    sub.w #$e0,d1             ; BPL1PTH..BPL6PTL: $e0..$f6
    bcs.b .copy
    cmp.w #$16,d1
    bhi.b .copy
    btst #1,d1
    bne.b .bad                ; a PTL move without its PTH move
    cmp.w #$14,d1
    beq.b .bad                ; a sixth plane
    subq.w #1,d5
    bmi.b .bad
    move.l (a4)+,d2           ; must be the matching PTL move
    move.l d2,d3
    swap d3
    and.w #$1fe,d3
    sub.w #$e2,d3
    cmp.w d1,d3
    bne.b .bad
    move.w d0,d3              ; pointer: PTH data, PTL data
    swap d3
    move.w d2,d3
    sub.l (a1,d1.w),d3        ; offset into the front plane
    add.l (a2,d1.w),d3        ; the same offset into V2's plane
    tst.w d6
    beq.b .skip_pointer
    move.w d3,d2
    swap d3
    move.w d3,d0
    move.l d0,(a5)
    move.l d2,4(a5)
.skip_pointer
    addq.w #8,a5
    bra.b .next
.copy
    tst.w d6
    beq.b .skip_copy
    move.l d0,(a5)
.skip_copy
    addq.w #4,a5
    cmp.l #$fffffffe,d0
    bne.b .next
    tst.w d6
    bne.b .ok
    moveq #1,d6
    bra.w .pass
.ok
    moveq #1,d0
    bra.b .out
.bad
    moveq #0,d0
.out
    movem.l (sp)+,d1-d6/a0-a5
    tst.l d0
    rts

; Hold loop exit: allocate V2 and put it into the rotation with a copy of
; the front View's picture, display setup and per-buffer state. Without the
; chip block the drawer keeps its original two buffers.
tb_start:
    movem.l d0-d7/a0-a6,-(sp)
    lea tb_start_due(pc),a0
    clr.w (a0)
    move.l $4.w,a6
    move.l #TB_SIZE,d0
    move.l #$10002,d1         ; MEMF_CHIP|MEMF_CLEAR
    jsr TB_EXEC_ALLOCMEM(a6)
    tst.l d0
    beq.w .done
    move.l d0,a3
    move.l -31786(a4),a6      ; GfxBase
    lea TB_VIEW(a3),a1
    jsr TB_GFX_INITVIEW(a6)
    lea TB_BITMAP(a3),a0
    moveq #5,d0
    move.l #320,d1
    move.l #200,d2
    jsr TB_GFX_INITBITMAP(a6)
    lea TB_BITMAP+8(a3),a0
    lea TB_PLANES(a3),a1
    moveq #5-1,d0
.planes
    move.l a1,(a0)+
    lea TB_PLANE(a1),a1
    dbf d0,.planes
    ; View, ViewPort and RasInfo: copies of the front View's
    move.l -23344(a4),a5      ; front View, on display and complete
    move.l (a5),a0
    lea TB_VPORT(a3),a1
    moveq #40/4-1,d0
.vport
    move.l (a0)+,(a1)+
    dbf d0,.vport
    move.l (a5),a0
    move.l 36(a0),a0
    lea TB_RINFO(a3),a1
    move.l (a0)+,(a1)+
    move.l (a0)+,(a1)+
    move.l (a0)+,(a1)+
    lea TB_VPORT(a3),a0
    clr.l 8(a0)               ; vp_DspIns, SprIns, ClrIns, UCopIns: none
    clr.l 12(a0)
    clr.l 16(a0)
    clr.l 20(a0)
    lea TB_RINFO(a3),a1
    move.l a1,36(a0)          ; vp_RasInfo
    lea TB_BITMAP(a3),a1
    move.l a1,TB_RINFO+4(a3)  ; ri_BitMap
    move.l a0,TB_VIEW(a3)     ; v_ViewPort
    move.l 12(a5),TB_VIEW+12(a3) ; View DyOffset, DxOffset
    move.w 16(a5),TB_VIEW+16(a3) ; View Modes
    lea TB_CPRLIST(a3),a0
    move.l a0,TB_VIEW+4(a3)   ; v_LOFCprList; no SHF list
    lea TB_COPPER(a3),a1
    move.l a1,4(a0)           ; start
    move.w #TB_COPPER_MAX,8(a0) ; MaxCount
    lea tb_mem(pc),a0
    move.l a3,(a0)            ; tb_copper needs it
    move.l a5,a0
    bsr tb_copper
    beq.w .fail
    move.l a5,a0
    lea TB_VIEW(a3),a1
    bsr tb_copy_picture
    ; drawing state: the back RastPort's settings with V2's BitMap
    move.l -22404(a4),a0
    lea TB_RPORT(a3),a1
    moveq #100/4-1,d0
.rport
    move.l (a0)+,(a1)+
    dbf d0,.rport
    lea TB_BITMAP(a3),a0
    move.l a0,TB_RPORT+4(a3)  ; rp_BitMap
    ; per-buffer state of the copied picture
    move.l a5,a0
    bsr tb_index_of
    lea -29900(a4),a0
    lea tb_ack(pc),a1
    move.b (a0,d0.w),(a1)
    add.w d0,d0
    lea -26360(a4),a0
    lea tb_speed(pc),a1
    move.w (a0,d0.w),(a1)
    lea -26356(a4),a0
    lea tb_rpm(pc),a1
    move.w (a0,d0.w),(a1)
    lea tb_wheel(pc),a1       ; wheel: front's, back's, and V2 = front's
    move.w -29620(a4),(a1,d0.w)
    move.w -29620(a4),4(a1)
    move.l -23350(a4),a0
    bsr tb_index_of
    add.w d0,d0
    move.w -29618(a4),(a1,d0.w)
    ; the back View is free, as after the original exchange and WaitTOF
    lea tb_loaded(pc),a0
    move.l -31782(a4),d0
    subq.l #2,d0
    move.l d0,(a0)
.done
    movem.l (sp)+,d0-d7/a0-a6
    rts
.fail
    lea tb_mem(pc),a0         ; unexpected copper list: stay double buffered
    clr.l (a0)
    move.l a3,a1
    move.l #TB_SIZE,d0
    move.l $4.w,a6
    jsr TB_EXEC_FREEMEM(a6)
    bra.b .done

; Hold loop entry: return to two buffers and free V2.
tb_stop:
    movem.l d0-d7/a0-a6,-(sp)
    lea tb_start_due(pc),a0
    move.w #1,(a0)
    move.l tb_mem(pc),d0
    beq.w .done
    move.l d0,a3
    move.l -23344(a4),a0
    cmp.l a3,a0
    beq.b .copy
    ; V0 or V1 is in front: the other one becomes the back View
    bsr tb_other
    move.l a1,a2
    bsr tb_wait_free          ; it may have been front before this front
    bsr tb_set
    bra.b .free
.copy
    ; V2 is in front: copy it into the back View, which is free, and show it
    move.l -23350(a4),a2
    move.l a3,a0
    move.l a2,a1
    bsr tb_copy_picture
    move.l a2,a0
    bsr tb_index_of
    lea -29900(a4),a0
    move.b tb_ack(pc),(a0,d0.w)
    add.w d0,d0
    lea -26360(a4),a0
    move.w tb_speed(pc),(a0,d0.w)
    lea -26356(a4),a0
    move.w tb_rpm(pc),(a0,d0.w)
    lea tb_wheel(pc),a0
    move.w 4(a0),(a0,d0.w)
    move.l a2,-(sp)
    jsr -32202(a4)            ; root $7aaa LoadView
    addq.w #4,sp
    move.l -31782(a4),d2
    bsr tb_wait_free          ; the other of V0/V1 left with V2's LoadView
    lea tb_loaded(pc),a0
    move.l d2,(a0)
    bsr tb_wait_free          ; and V2 leaves the display now
    move.l a2,a0
    bsr tb_other
    move.l a1,a2
    bsr tb_set
.free
    move.l -23344(a4),a0      ; the wheel pair as after a two-buffer frame
    bsr tb_index_of
    add.w d0,d0
    lea tb_wheel(pc),a1
    move.w (a1,d0.w),-29620(a4)
    move.l -23350(a4),a0
    bsr tb_index_of
    add.w d0,d0
    move.w (a1,d0.w),-29618(a4)
    lea tb_mem(pc),a0
    clr.l (a0)
    move.l a3,a1
    move.l #TB_SIZE,d0
    move.l $4.w,a6
    jsr TB_EXEC_FREEMEM(a6)
.done
    movem.l (sp)+,d0-d7/a0-a6
    rts

; h4 $00aea: per-buffer index of the View being drawn (8(a5)).
tb_index:
    lea -22208(a4),a0         ; displaced: index 0 for V0, else 1
    move.l 8(a5),a1
    move.w #1,-22472(a4)
    cmp.l a0,a1
    bne.b .not0
    clr.w -22472(a4)
    rts
.not0
    cmp.l tb_mem(pc),a1
    bne.b .done
    move.w #2,-22472(a4)
.done
    rts

; h4 $03ae4: a0 = this buffer's desired lever byte, a1 = its drawn byte.
tb_lever:
    move.w -22472(a4),d0
    lea -29902(a4),a0
    cmp.w #2,d0
    beq.b .v2
    lea -29900(a4),a1
    add.w d0,a0
    add.w d0,a1
    rts
.v2
    lea tb_ack(pc),a1
    rts

; h4 $04246: d1 = word index, a0 = speed cache, a1 = RPM cache.
tb_gauge:
    move.w -22472(a4),d1
    cmp.w #2,d1
    beq.b .v2
    add.w d1,d1
    lea -26360(a4),a0
    lea -26356(a4),a1
    rts
.v2
    moveq #0,d1
    lea tb_speed(pc),a0
    lea tb_rpm(pc),a1
    rts

; h4 $04238: a new cluster invalidates every buffer's speed cache.
tb_gauge_reset:
    move.l #-1,-26360(a4)     ; displaced
    move.l a0,-(sp)
    lea tb_speed(pc),a0
    move.w #-1,(a0)
    move.l (sp)+,a0
    rts

; h4 $0240a: before the comparison, -29618(a4) = the state in this buffer.
tb_wheel_in:
    move.l tb_mem(pc),d0
    beq.b .displaced
    move.l a0,-(sp)
    lea tb_wheel(pc),a0
    move.w -22472(a4),d0
    add.w d0,d0
    move.w (a0,d0.w),-29618(a4)
    move.l (sp)+,a0
.displaced
    move.w -22364(a4),d0      ; displaced steering snapshot
    jmp -32562(a4)            ; displaced call

; h4 $02450: the displaced swap; with three buffers -29620(a4) now holds
; the state drawn into this buffer.
tb_wheel_out:
    move.w -29620(a4),d0
    move.w -29618(a4),-29620(a4)
    move.w d0,-29618(a4)
    move.l tb_mem(pc),d0
    beq.b .done
    move.l a0,-(sp)
    lea tb_wheel(pc),a0
    move.w -22472(a4),d0
    add.w d0,d0
    move.w -29620(a4),(a0,d0.w)
    move.l (sp)+,a0
.done
    rts

tb_mem: dc.l 0
tb_wheel: dc.w 0,0,0
tb_loaded: dc.l 0
tb_start_due: dc.w 1
tb_speed: dc.w -1
tb_rpm: dc.w -1
tb_ack: dc.b 0
    even

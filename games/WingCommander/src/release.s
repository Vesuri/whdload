; Translate public language/pacing options once before language selection.
; Internal CUSTOM1=3 is reserved for enhanced English; 0/1 are Psygore.
release_setcpu:
        movem.l d0-d2/a0-a1,-(sp)
        lea     slave+$1de4(pc),a0
        lea     slave+$1e04(pc),a1
        move.l  (a0),d2
        cmpi.l  #1,d2
        bhi.s   .bad
        move.l  (a1),d2
        cmpi.l  #4,d2
        bhi.s   .bad
        tst.l   d2
        beq.s   .enhanced
        subq.l  #1,(a1)          ; public 1..4 -> Psygore 0..3
        bra.s   .ready
.enhanced:
        tst.l   (a0)
        bne.s   .ready           ; German: normal until ported
        move.l  #3,(a0)
.ready:
        movem.l (sp)+,d0-d2/a0-a1
        bra.l   render_setcpu
.bad:
        movem.l (sp)+,d0-d2/a0-a1
        bra.w   timing_bad

; Full enhanced converter gate, including flight allocation fallback.
; Flight and the clocked world intro have no limiter; other scenes keep normal.
release_limit:
        tst.w   timing_active(pc)
        bne.l   release_convert_wait
        tst.w   intro_active(pc)
        bne.l   release_convert_wait
.nonflight:
        bsr.w   slave+$17b8
        rts

release_name:
        dc.b 'Wing Commander CD32',0
release_info:
        dc.b '2.0b (19.10.2026)',10
        dc.b 'Original slave: Psygore',10
        dc.b 'CD32 improvements: Vesuri',0
release_version:
        dc.b '$VER: WingCommanderCD32 2.0b (19.10.2026)',0
release_config:
        dc.b 'C1:L:Language:English,German;'
        dc.b 'C2:L:Cheats:Off,Enabled,Invincible;'
        dc.b 'C3:L:System:Default,Enyo,McAuliffe,Gateway,Gimle,Brimstone,Chengdu,Dakota,Port Hedland,Kurasawa,Rostov,Hubble''s Star,Venice,Hell''s Kitchen;'
        dc.b 'C4:L:Mission:1,2,3;'
        dc.b 'C5:L:Mode:Enhanced,Psygore normal,Psygore unlimited,Psygore relaxed,Psygore slow;',0
        cnop 0,4

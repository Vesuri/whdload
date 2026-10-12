; Diagnostic-only CACR observations. Included only by cache_probe.py's scratch
; build, never by a playable target. No cache-enable register is written.
cache_probe_record:
        dc.b 'CA60'
        dc.w 1,0 ; version, number of observations
        dc.w 0,0 ; Exec AttnFlags, has CACR
        dc.l -1,-1 ; after SetCPU, completed gameplay tick 200
cache_probe_boot:
        movem.l d0-d7/a0-a6,-(sp)
        lea (cache_probe_record,pc),a3
        move.l ($4).w,a6
        move.w (AttnFlags,a6),(8,a3)
        btst #1,(AttnFlags+1,a6) ; AFB_68020: never execute MOVEC on 68000
        beq .done
        move.w #1,(10,a3)
        lea (cache_probe_supervisor,pc),a5
        jsr (_LVOSupervisor,a6)
        move.l d0,(12,a3)
        move.w #1,(6,a3)
.done:  movem.l (sp)+,d0-d7/a0-a6
        rts
cache_probe_tick:
        movem.l d0-d7/a0-a6,-(sp)
        move.l (s60_ticks,pc),d0
        cmp.l #200,d0
        bne .done
        lea (cache_probe_record,pc),a3
        cmp.w #1,(6,a3)
        bne .done
        move.l ($4).w,a6
        lea (cache_probe_supervisor,pc),a5
        jsr (_LVOSupervisor,a6)
        move.l d0,(16,a3)
        move.w #2,(6,a3)
.done:  movem.l (sp)+,d0-d7/a0-a6
        rts
cache_probe_supervisor:
        dc.l $4e7a0002 ; MOVEC CACR,D0, reached only on 68020+
        rte

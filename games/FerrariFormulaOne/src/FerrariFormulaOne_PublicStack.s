; Optional MEMF_PUBLIC game-task stack. Kickstart 1.3 / 68000 safe.
; FF1PublicCall has the same game ABI as JSR 4(A3). It preserves the game's
; input and output registers while changing only its task stack. Single caller;
; the enclosing slave owns this context for the complete game invocation.
; Allocation failure calls the game on its original stack; the profile selector
; must reject the fine path when FF1PublicStackOwner is empty or not Fast.
 ifnd FF1_PUBLIC_STACK
FF1_PUBLIC_STACK equ 0
 endc
 ifne FF1_PUBLIC_STACK
 ifnd FF1_PUBLIC_STACK_BYTES
FF1_PUBLIC_STACK_BYTES equ 32768
 endc
FF1PublicCall:
 movem.l d0-d7/a0-a6,-(sp)
 lea FF1PublicStackOwner(pc),a0
 move.l #FF1_PUBLIC_STACK_BYTES,d0
 bsr.w FF1PublicAcquire
 tst.l d0
 beq.w .native
 lea FF1PublicStackContext(pc),a5
 move.l sp,(a5)
 move.l $4.w,a6
 suba.l a1,a1
 jsr -294(a6)                  ; FindTask(NULL)
 move.l d0,a4
 move.l a4,4(a5)
 move.l 58(a4),8(a5)           ; TC_SPLOWER (exec/tasks.i)
 move.l 62(a4),12(a5)          ; TC_SPUPPER
 move.l FF1PublicStackOwner(pc),a3
 move.l a3,a2
 adda.l #FF1_PUBLIC_STACK_BYTES,a2
 move.l sp,a0
 lea -60(a2),a1
 moveq #14,d0
.copy_in:
 move.l (a0)+,(a1)+
 dbra d0,.copy_in
 jsr -120(a6)                  ; Disable: bounds and SP change atomically
 move.l a3,58(a4)
 move.l a2,62(a4)
 lea -60(a2),sp
 jsr -126(a6)                  ; Enable, now on the public stack
 movem.l (sp)+,d0-d7/a0-a6
 jsr 4(a3)
 movem.l d0-d7/a0-a6,-(sp)
 lea FF1PublicStackContext(pc),a5
 move.l sp,a0
 move.l (a5),a1
 moveq #14,d0
.copy_out:
 move.l (a0)+,(a1)+
 dbra d0,.copy_out
 move.l $4.w,a6
 jsr -120(a6)
 move.l 4(a5),a4
 move.l 8(a5),58(a4)
 move.l 12(a5),62(a4)
 move.l (a5),sp
 jsr -126(a6)
 lea FF1PublicStackOwner(pc),a0
 bsr.w FF1PublicRelease         ; no reference to the released stack remains
 movem.l (sp)+,d0-d7/a0-a6
 rts
.native:
 movem.l (sp)+,d0-d7/a0-a6
 jsr 4(a3)
 rts
FF1PublicStackOwner: ds.l 2
FF1PublicStackContext: ds.l 4
 endc

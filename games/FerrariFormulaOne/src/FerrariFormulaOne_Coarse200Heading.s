; Four continuous heading increments for the integer 200/100 interval ratio.
; Native heading storage and all other native heading writers remain owners.
; Host supplies relocation, interrupt exclusion and patch ledger restoration.
FF1InstallCoarse200Heading:
 cmpi.w #$d1b9,$678de
 bne.w C1Fault
 cmpi.w #$0003,$678e0
 bne.w C1Fault
 cmpi.w #$2fb4,$678e2
 bne.w C1Fault
 cmpi.w #$d1b9,$67900
 bne.w C1Fault
 cmpi.w #$0003,$67902
 bne.w C1Fault
 cmpi.w #$2fb8,$67904
 bne.w C1Fault
 cmpi.w #$d1b9,$67948
 bne.w C1Fault
 cmpi.w #$0003,$6794a
 bne.w C1Fault
 cmpi.w #$2fb4,$6794c
 bne.w C1Fault
 cmpi.w #$d1b9,$67976
 bne.w C1Fault
 cmpi.w #$0003,$67978
 bne.w C1Fault
 cmpi.w #$2fb8,$6797a
 bne.w C1Fault
 lea C4Heading678de(pc),a0
 move.w #$4ef9,$678de
 move.l a0,$678e0
 lea C4Heading67900(pc),a0
 move.w #$4ef9,$67900
 move.l a0,$67902
 lea C4Heading67948(pc),a0
 move.w #$4ef9,$67948
 move.l a0,$6794a
 lea C4Heading67976(pc),a0
 move.w #$4ef9,$67976
 move.l a0,$67978
 rts

; Double only the continuous angular increment, retaining modular Q12 storage.
; D0 and all other registers survive. CCR reflects the second native addition;
; the native continuation overwrites CCR before any conditional use.
C4Heading678de:
 add.l d0,$32fb4
 add.l d0,$32fb4
 jmp $678e4
C4Heading67900:
 add.l d0,$32fb8
 add.l d0,$32fb8
 jmp $67906
C4Heading67948:
 add.l d0,$32fb4
 add.l d0,$32fb4
 jmp $6794e
C4Heading67976:
 add.l d0,$32fb8
 add.l d0,$32fb8
 jmp $6797c

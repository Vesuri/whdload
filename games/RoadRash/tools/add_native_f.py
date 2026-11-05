from pathlib import Path
p=Path('src/cpu_work.s');s=p.read_text();s+='''
; Native/Chip fallback: retain the original simulation, apply only leaf-save
; and in-place span reductions. These need no public data or per-frame cache.
f_native_init:
 movem.l d0-d7/a0-a6,-(a7)
 move.l _enhanced_framerate(pc),d0
 beq .done
 move.l expansion_memory(pc),d0
 cmpi.l #$80000,d0
 bne .done
 IFD VERIFY_F_CONTROL
 bra .done
 ENDC
 move.l #$80000,a5
 bsr f_saves_init
 bsr f_span_init
 move.l _resload(pc),a2
 jsr (resload_FlushCache,a2)
.done:
 movem.l (a7)+,d0-d7/a0-a6
 rts
''';p.write_text(s)
p=Path('src/RoadRashHD.s');s=p.read_text().replace('\tbsr public_main_init','\tbsr public_main_init\n\tbsr f_native_init',1);p.write_text(s)

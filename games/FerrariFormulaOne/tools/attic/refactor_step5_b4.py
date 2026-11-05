from pathlib import Path
import re
p=Path('Games/FerrariFormulaOne_UpdateHooks.s');s=p.read_text()
patterns=[(r' IFD FF1_PLAYER_HOOKS\n lea \((\w+)\.l,pc\),a0\n moveq #0,d0\n ELSE\n bsr.w (\w+)\n ENDC',r' FF1PlayerContext \1,\2'),(r' IFD FF1_LEAN_PLAYER\n movem.l ([^,\n]+),-\(sp\)\n ELSE\n movem.l d0-d7/a0-a6,-\(sp\)\n ENDC',r' FF1PlayerSave \1'),(r' IFD FF1_LEAN_PLAYER\n movem.l \(sp\)\+,([^\n]+)\n ELSE\n movem.l \(sp\)\+,d0-d7/a0-a6\n ENDC',r' FF1PlayerRestore \1')]
for pat,repl in patterns:s,count=re.subn(pat,repl,s);print(count,repl)
macros=r'''; B4 is the mode-8 player path only. Its native opponent guards precede these
; callbacks. VERIFY retains the broad trace ABI; lean saves each callback's
; clobbered registers. D0/D1 remain first when a callback returns through the
; saved frame. Component helpers keep their original arithmetic contracts.
FF1PlayerContext macro
 IFD FF1_PLAYER_HOOKS
 lea (\1.l,pc),a0
 moveq #0,d0
 ELSE
 bsr.w \2
 ENDC
 endm
FF1PlayerSave macro
 IFD FF1_LEAN_PLAYER
 movem.l \1,-(sp)
 ELSE
 movem.l d0-d7/a0-a6,-(sp)
 ENDC
 endm
FF1PlayerRestore macro
 IFD FF1_LEAN_PLAYER
 movem.l (sp)+,\1
 ELSE
 movem.l (sp)+,d0-d7/a0-a6
 ENDC
 endm

'''
s=s.replace('FF1UpdateWorkspace macro',macros+'FF1UpdateWorkspace macro',1)
s=s.replace('player_state_end:\n ELSE','player_state_end:\n ifne player_state_end-player_state-64\n fail "B4 player state must be 64 bytes"\n ENDC\n ELSE')
p.write_text(s)
for name,comment in [('Steering','; FF1_PLAYER_HOOKS uses cursor.b at +10; byte +11 belongs to fuel and\n; must survive both sampling and reset. History and quantum fields are unchanged.\n'),('Wear','; FF1_PLAYER_HOOKS stores the unsigned 0..4 carry in a byte; no adjacent\n; byte may be read or written. The default word ABI is unchanged.\n')]:
 p=Path('Games/FerrariFormulaOne_'+name+'.s');p.write_text(comment+p.read_text())
p=Path('tmp/dev/tools/build_step5_b4.py');s=p.read_text();Path('tmp/dev/tools/build_step5_b4_refactor.py').write_text(s.replace('b4-v4','b4-refactor'))

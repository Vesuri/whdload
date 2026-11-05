#!/usr/bin/env python3
"""Capture allocator error entry before its destructive system alert."""
from runtime_lifecycle_probe import cap,command,irq,snapshot
from profile_window import ROOT
snapshot('trap-before')
lines=['delete','set $steps=0','set $hit=0','break *0x4e07ba','commands','silent','set $hit=1','end','break *0x4e0704','condition $bpnum $a1==0xfffffffe','commands','silent','set $hit=2','end',f'break *{irq:#x}','commands','silent','set $steps=$steps+1','if $steps==10','monitor key 44 0','end','if $steps<1000','continue','end','end','monitor key 44 1','continue','printf "ALLOCATOR_HIT %u FIELDS %u\\n", $hit, $steps','info registers','x/80wx $sp','x/16i $pc-16',f'dump binary memory {(cap/"allocator-trap.bin").relative_to(ROOT)} 0x200000 0x600000','delete','monitor key 44 0']
p=cap/'trap.gdb';p.write_text('\n'.join(lines)+'\n');out=command('gdb source '+str(p.relative_to(ROOT)));(cap/'trap.log').write_text(out);print(out[-9000:])

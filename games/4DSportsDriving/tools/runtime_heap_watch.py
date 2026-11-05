#!/usr/bin/env python3
"""Observe the reproduced native transition; never modify guest RAM."""
from runtime_lifecycle_probe import cap,command,m,a,base,s,irq,snapshot
from profile_window import ROOT
before=snapshot('watch-before')
node=0x525fc0
b=(cap/'watch-before.bin').read_bytes();v=int.from_bytes(b[node-0x200000:node-0x200000+4],'big')
assert 0x510000<v<0x5a0000,hex(v)
steps=0;events=[]
for token in '45 44 4c 44 wait:100 4f 4f 44 wait:100 44 4f 44 wait:100 44 wait:300 44 wait:100'.split():
 if token.startswith('wait:'):steps+=int(token[5:]);continue
 key=int(token,16);events.append((steps+1,key,1));events.append((steps+11,key,0));steps+=20
lines=['delete','set $hit=0','set $steps=0',f'watch *(unsigned int *){node:#x}','commands','silent',f'printf "NODE pc=%08x sp=%08x value=%08x step=%u\\n", $pc, $sp, *(unsigned int *){node:#x}, $steps','x/8i $pc-12','info registers',f'if *(unsigned int *){node:#x}==0xfffffffe',f'dump binary memory {(cap/"first-invalid.bin").relative_to(ROOT)} 0x200000 0x600000','set $hit=1','else','continue','end','end',f'break *{irq:#x}','commands','silent','set $steps=$steps+1']
for field,key,state in events:lines += [f'if $steps=={field}',f'monitor key {key:x} {state}','end']
lines+= [f'if $steps<{steps+100}','continue','end','end','continue','printf "WATCH_HIT %u STEPS %u\\n", $hit, $steps','delete','monitor key 44 0','monitor key 45 0','monitor key 4c 0','monitor key 4f 0']
f=cap/'watch.gdb';f.write_text('\n'.join(lines)+'\n');out=command('gdb source '+str(f.relative_to(ROOT)));(cap/'watch.log').write_text(out);print(out[-8000:]);snapshot('watch-end')

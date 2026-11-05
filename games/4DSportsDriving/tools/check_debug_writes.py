#!/usr/bin/env python3
"""Verify reversible debugger RAM/PC writes before resuming any game code."""
import json,re
from pathlib import Path
import sys
from profile_window import command
p=Path(sys.argv[1]);m=json.loads((p/'anchor.json').read_text());b=(p/'memory.bin').read_bytes();address=m['memory_base']+b.index(b'4DA4PHYS')+12+8
script=f'''set $savedword=*(unsigned int *){address:#x}
set $savedpc=$pc
set $savedd7=$d7
set *(unsigned int *){address:#x}=0x12345678
set $d7=0x24681357
set $pc=$savedpc+2
maintenance flush register-cache
printf "WRITTEN %u %u %u\\n", *(unsigned int *){address:#x}, (unsigned int)$d7, (unsigned int)$pc
set *(unsigned int *){address:#x}=$savedword
set $d7=$savedd7
set $pc=$savedpc
maintenance flush register-cache
printf "RESTORED %u %u %u %u %u %u\\n", *(unsigned int *){address:#x}, (unsigned int)$d7, (unsigned int)$pc, (unsigned int)$savedword, (unsigned int)$savedd7, (unsigned int)$savedpc
'''
f=p/'write-check.gdb';f.write_text(script);out=command('gdb source '+str(f));(p/'write-check.txt').write_text(out)
a=list(map(int,re.search(r'^WRITTEN (.*)$',out,re.M)[1].split()));r=list(map(int,re.search(r'^RESTORED (.*)$',out,re.M)[1].split()));assert a==[0x12345678,0x24681357,r[-1]+2],(a,r,out);assert r[:3]==r[3:]
(p/'write-check.json').write_text(json.dumps({'passed':True,'written':a,'restored':r[:3],'scope':'Stopped target RAM/D7/PC round-trip, cache flushed before readback. No guest instruction executed between mutation and restoration.'},indent=2)+'\n');print('Verified RAM, D7 and PC writes, restored all three')

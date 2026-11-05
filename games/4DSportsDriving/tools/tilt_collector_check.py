#!/usr/bin/env python3
"""Validate the actual C520 baseline collector, register/X contract and vectors."""
import json,re,sys,capstone
from pathlib import Path
from profile_window import command,ROOT
from simulation_fixture import read_fixture,compare
cap=Path(sys.argv[1]).resolve();meta=json.loads((cap/'anchor.json').read_text());b=(cap/'memory.bin').read_bytes();g=meta['game_base'];n=100-meta['simulation_tick'];assert n>0 and meta['active_simulation_word']==50 and not meta['opponent']
syms={k:int(v,16) for k,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
base=meta['memory_base']+b.index(b'4DA4PHYS')+12-syms['sim_a4000_private'];entry=base+syms['sim_tilt_collect'];end=base+syms['sim_tilt_center'];scratch=base+syms['sim_tilt_wheels']
md=capstone.Cs(capstone.CS_ARCH_M68K,capstone.CS_MODE_BIG_ENDIAN|capstone.CS_MODE_M68K_000)
returns=[i.address for i in md.disasm(b[entry-meta['memory_base']:end-meta['memory_base']],entry) if i.mnemonic=='rts'];assert len(returns)==1
regs=[f'(unsigned int)${r}' for r in [*[f'd{i}' for i in range(8)],*[f'a{i}' for i in range(7)],'sp']]
common=['*(unsigned short *)($a4-0x940)','*(unsigned char *)($a5-3)','($sr &16)']+regs

def log(tag,expr):return 'printf "'+tag+' '+' '.join('%d' for _ in expr)+'\\n", '+', '.join(expr)+'\n'
script='gdb delete\nset $n=0\n'
for addr,tag in [(entry,'IN'),(returns[0],'OUT')]:
 script+=f'break *{addr:#x}\ncommands\nsilent\n'+log(tag,common)+'continue\nend\n'
expr=['*(unsigned short *)($a4-0x940)']+[f'*(int *)($a4+0xb9c+{i*4})' for i in range(3)]+[f'*(short *)(*(unsigned int *)($a5+8)+0x54+{i*2})' for i in range(4)]+[f'*(short *)($a4+0xbae+{i*2})' for i in range(9)]+[f'*(int *)($a5-0xe2+{i*4})' for i in range(12)]+[f'*(short *){scratch+i*2:#x}' for i in range(12)]
script+=f'break *{g+0xc60c:#x}\ncommands\nsilent\n'+log('BASIS',expr)+'continue\nend\n'
script+=f'break *{g+0xe7b4:#x}\ncommands\nsilent\nset $n=$n+1\nif $n<{n}\ncontinue\nend\nend\ncontinue\ninfo registers pc'
(cap/'collector-check.gdb').write_text(script);out=command(script);(cap/'collector-check.txt').write_text(out)
assert int(re.search(r'^pc\s+0x([0-9a-f]+)',out,re.M)[1],16)==g+0xe7b4
records={tag:[list(map(int,line.split())) for line in re.findall(r'^'+tag+r' (.*)$',out,re.M)] for tag in ('IN','OUT','BASIS')}
assert len(records['IN'])==len(records['OUT'])==4*n
assert records['IN']==records['OUT'],'Collector changed a register, SP or X flag'
assert len(records['BASIS'])==n
word=lambda v:(v+32768)%65536-32768
for row in records['BASIS']:
 origin=row[1:4];extension=row[4:8];matrix=row[8:17];old=row[17:29];expected=[]
 for wheel,e in enumerate(extension):
  expected += [word(old[wheel*3+i]-origin[i]+word((e+384)*matrix[3+i]//16384)) for i in range(3)]
 assert expected==row[29:41],(row[0],expected,row[29:41])
command(f'gdb delete\ntbreak *{g+0xe5f8:#x} if *(unsigned short *)($a4-0x940)==101\ncontinue\ndump binary memory {cap.relative_to(ROOT)}/collector-end.bin 0x200000 0x600000\ndelete')
r=compare(read_fixture(cap,'collector-end.bin'),read_fixture(ROOT/'tmp/prof/tilt-final-ramp-full'));assert r['equal_samples']==r['samples']==21
r.update(actual_collector_calls=4*n,body_bases=n,body_vectors=4*n,registers_sp_x_exact=True,x_values=sorted({row[2] for row in records['IN']}),baseline_vectors_exact=True)
(cap/'collector-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))

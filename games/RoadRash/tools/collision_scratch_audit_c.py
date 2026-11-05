import sys,json,os,struct
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 data=read_bytes(s,0x80000,0x40000)
 (s.out/'game.bin').write_bytes(data)
 refs={}
 for addr in [0x8b480,0xa59ca]:
  pattern=struct.pack('>I',addr);sites=[0x80000+i for i in range(0,len(data)-3,2) if data[i:i+4]==pattern];refs[hex(addr)]=[hex(a) for a in sites]
  for site in sites:
   (s.out/f'{site:x}.txt').write_text(s.cmd(f'disassemble {site-8:#x},{site+18:#x}'))
 (s.out/'tail.txt').write_text(s.cmd('disassemble 0x8cb70,0x8cbb0'))
 (s.out/'refs.json').write_text(json.dumps(dict(references=refs,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n');print(refs,flush=True)
finally:s.quit()

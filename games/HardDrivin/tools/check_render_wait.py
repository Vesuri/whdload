"""Compare original and selected wait: registers/CCR and controlled busy transitions."""
from pathlib import Path
import os,subprocess,struct,json,hashlib
exec(Path('tools/check_sweep_native.py').read_text().split('import subprocess,sys')[0])
source=Path('src/HardDrivinHD.s').read_text(encoding='latin1');old=source[source.index('\n_blitwait:')+1:source.index(';--------------------------------',source.index('\n_blitwait:')+1)]
newsrc=Path('src/HardDrivinRender.s').read_text();new=newsrc[newsrc.index('_render_wait:\n'):]
macro=(Path(os.environ['WHDLOAD'])/'Include/whdmacros.i').read_text().split('BLITWAIT MACRO',1)[1].split('ENDM',1)[0]
p=Path('tmp/s5-wait-contract');p.with_suffix('.s').write_text(' org $400100\nBLITWAIT MACRO'+macro+'ENDM\n_custom equ $dff000\n_ciaa equ $bfe001\ndmaconr equ 2\nvhposr equ 6\nDMAB_BLTDONE equ 14\n jmp _blitwait\n jmp _render_wait\n'+old+'\n_ct_ct2: dc.l 0\n'+new)
subprocess.run([os.environ['VASM'],'-m68000','-Fbin','-devpac','-I'+os.environ['WHDLOAD']+'/Include','-o',str(p.with_suffix('.bin')),str(p.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
write(0x400100,p.with_suffix('.bin').read_bytes());write(0x490000,bytes.fromhex('40f900470000'));ok(u.uc_mem_map(h,0xdff000,0x1000,7));ok(u.uc_mem_map(h,0xbfe000,0x1000,7));write(0xbfe001,b'\xff')
cbtype=C.CFUNCTYPE(None,P,I,U,I,C.c_int64,P);reads=0;busy=0;byte=0
@cbtype
def onread(uc,kind,addr,size,value,userdata):
 global reads
 reads+=1;write(0xdff002,bytes([byte|(64 if reads<=busy else 0)]))
u.uc_hook_add.argtypes=[P,C.POINTER(Z),I,P,P,U,U];u.uc_hook_add.restype=I
hook=Z();ok(u.uc_hook_add(h,C.byref(hook),1<<10,C.cast(onread,P),None,0xdff002,0xdff002))
cases=0
for byte in [x for x in range(256) if not x&64]:
 for ccr in range(32):
  for busy in [0,1,2,5]:
   results=[]
   for pc in [0x400100,0x400106]:
    reads=0
    for k in range(1,17):reg(k,k*0x1010101)
    reg(17,0x2000|ccr);reg(8,0x4ffff0);pack(0x4ffff0,'I',0x490000)
    ok(u.uc_emu_start(h,pc,0x490000,1000000,10000));assert reads>busy;ok(u.uc_emu_start(h,0x490000,0x490006,1000000,1));results.append(([reg(k) for k in range(1,17)],read(0x470000,2)))
   assert results[0]==results[1],(byte,ccr,busy,results)
   expected_regs=[k*0x1010101 for k in range(1,17)];expected_regs[7]=0x4ffff4
   expected_sr=0x2000|(ccr&16)|(4 if byte==0 else 8 if byte&128 else 0)
   assert results[0]==(expected_regs,struct.pack('>H',expected_sr)) if isinstance(results[0],tuple) else results[0]==[expected_regs,struct.pack('>H',expected_sr)]
   cases+=1
r=dict(passed=True,cases=cases,source_sha256=hashlib.sha256(newsrc.encode()).hexdigest(),scope='Independent Python register/CCR model and same-build original/candidate helper; all stable DMACONR high bytes, all CCR inputs, four busy-transition schedules; registers, stack and materialized CCR. Actual DMA timing requires machine profiles.')
Path('tmp/s5-wait-contract.json').write_text(json.dumps(r,indent=2)+'\n');print(r);ok(u.uc_close(h))

import sys,json,struct
from capture_demo import ROOT,command
out=ROOT/'tmp/prof'/sys.argv[1];state=json.loads((out/'layout.json').read_text())['state'];rel=out.relative_to(ROOT)
samples=[];seen=False
command('gdb delete\nbreak *0xcfb5a8')
for k in range(100):
 command('gdb set $hd_k=0\nwhile $hd_k < 25\ncontinue\nset $hd_k=$hd_k+1\nend')
 command(f'gdb dump binary memory {rel}/live.bin 0xd0ee16 0xd16016\ndump binary memory {rel}/tape-state.bin {state:#x} {state+20:#x}')
 b=(out/'live.bin').read_bytes();t=(out/'tape-state.bin').read_bytes()
 def r(o,f):return struct.unpack_from('>'+f,b,0x7100+o)[0]
 s=dict(field=struct.unpack_from('>I',t,4)[0],pose=[r(o,'H') for o in [-0x670a,-0x6708,-0x6706]],heading=r(-0x66b6,'h'),speed=r(-0x66d4,'h'),crash=r(-0x69fa,'B'),replay=r(-0x5229,'B'),checkpoint=hex(r(-0x5230,'I')))
 samples.append(s);print(s,flush=True)
 (out/'recovery.json').write_text(json.dumps(samples,indent=2))
 seen=seen or bool(s['replay'])
 if seen and not s['replay'] and not s['crash']:break
command('gdb delete')

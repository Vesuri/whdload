from unicorn_b import *
c=CPU();gb=0x200000;resload=0x70000
# Real resload ABI: d0/d1/a0/a1 are scratch. Poison them in the mock SetCPU.
c.put(resload+0x60,bytes.fromhex('6000')+struct.pack('>h',0x1000-0x62))
c.put(resload+0x64,bytes.fromhex('6000')+struct.pack('>h',0x1100-0x66))
c.put(resload+0x1000,bytes.fromhex('203c00003b3d72ff207ca0a0a0a0227ca1a1a1a14e75'))
c.put(resload+0x1100,bytes.fromhex('23c90008001023c8000800144e75'))
for i in range(9):
 a=gb+i*0x20000;nextseg=(gb+(i+1)*0x20000-4)//4 if i<8 else 0;c.put(a-4,struct.pack('>I',nextseg))
c.put(base+symbol('_verify_seed'),struct.pack('>I',1))
expected={r:0x13570000+r*0x100 for r in range(1,17) if r!=8};expected[1]=base+symbol('pl_gamemule_658');expected[2]=gb;expected[3]=resload
for r,v in expected.items():c.rw(r,v)
c.call(base+symbol('verify_dispatch'))
assert c.get(base+symbol('verify_marker')+72,4)==bytes.fromhex('00003b3d')
assert c.get(0x80010,8)==struct.pack('>II',gb,base+symbol('verify_game_patches'))
assert all(c.rr(r)==v for r,v in expected.items())
assert c.rr(8)==0x8f004
c.close();print('Cache-policy query preserves the original game patch target across resload scratch-register clobbers')

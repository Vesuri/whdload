from pathlib import Path
import json,struct,hashlib,zlib
root=Path('tmp/prof/p7-integration');save=root/'save';load=root/'reload';packet=(save/'a4test.rpl').read_bytes()
assert len(packet)==63912 and struct.unpack_from('>4H',packet,8)==(2,10,50,20)
assert zlib.crc32(packet[:-4])==int.from_bytes(packet[-4:],'big')
def state(cap,name):
 m=json.loads((cap/'anchor.json').read_text());b=(cap/name).read_bytes();a=m['data_base']+0x7ffe-m['memory_base'];v=b[a-0xa80:a-0x620]+b[a+0x228:a+0x22e]
 for tag,n in [(b'4DA4PHYS',152),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
  i=b.index(tag)+12;v+=b[i:i+n]
 assert len(v)==1510
 return v,b,a,m
matches=[]
for tick in (1500,1550,1600):
 x,*_=state(save,f'live-{tick}.bin');y,*_=state(load,f'play-{tick}.bin');assert x==y,(tick,[(hex(i),u,v)for i,(u,v)in enumerate(zip(x,y))if u!=v][:20])
 matches.append(dict(tick=tick,equal_semantic_bytes=1510,sha256=hashlib.sha256(x).hexdigest()))
_,b,a,m=state(save,'saved.bin');ptr=lambda off:struct.unpack_from('>I',b,a+off)[0]-m['memory_base'];route=b[ptr(-0x17a4):ptr(-0x17a4)+1802];assert route==packet[62104:63906]
_,b,a,m=state(load,'loaded.bin');ptr=lambda off:struct.unpack_from('>I',b,a+off)[0]-m['memory_base'];assert b[ptr(-0x17a4):ptr(-0x17a4)+1802]==route
r=dict(physics_abi=10,file_bytes=len(packet),file_sha256=hashlib.sha256(packet).hexdigest(),crc_valid=True,checkpoints=matches,route_bytes_equal=1802,scope='Production native Save Replay, fresh-process native Load and Play; exact unmasked semantic state including both cars and all private fractions.')
(root/'replay-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))

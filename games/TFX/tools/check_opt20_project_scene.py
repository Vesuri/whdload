import json,struct,sys
from pathlib import Path
import replay_flight
from amigaxdev import barto
r=Path(sys.argv[1]);a=r/'project-scene-off';b=r/'project-scene-on'
images=[]
for n in [1,10,30,45,57,200,400]:
 planes=[]
 for p in [a,b]:
  t=barto.load(p/f'swap-{n:03d}.trace');pub=json.loads((p/'publications.json').read_text())[n-1];c=pub['copper'];words=dict(struct.unpack_from('>HH',t.chip,o) for o in range(c,c+192,4));ptr=[words[0xe0+4*i]*65536+words[0xe2+4*i] for i in range(8)];planes.append(b''.join(t.chip[o:o+8000] for o in ptr))
 same=planes[0]==planes[1];png=(a/f'swap-{n:03d}.png').read_bytes()==(b/f'swap-{n:03d}.png').read_bytes();assert same and png
 images.append(dict(swap=n,planes_equal=same,png_equal=png))
changes={};clocks=[]
for i in range(3):
 x=(a/f'end-hunk{i}.bin').read_bytes();y=(b/f'end-hunk{i}.bin').read_bytes();diff={o for o,(u,v) in enumerate(zip(x,y)) if u!=v};allow=set()
 if i==0:
  allow.update(range(0x55e32,0x55e38));assert x[0x55e32:0x55e38].hex()=='53474cfa1c00' and y[0x55e32:0x55e34].hex()=='4ef9'
 for o in ([0x4d85a,0x4d884] if i==0 else [0x10678,0x13de0,0x17012] if i==1 else []):
  u=int.from_bytes(x[o:o+4],'big');v=int.from_bytes(y[o:o+4],'big');clocks.append(dict(hunk=i,offset=hex(o),off=u,on=v,delta=v-u));allow.update(range(o,o+4))
 changes[i]=dict(differing_bytes=len(diff),unexplained=[hex(o) for o in sorted(diff-allow)])

x=(a/'end-hunk0.bin').read_bytes();y=(b/'end-hunk0.bin').read_bytes()
assert int.from_bytes(x[0x4d77c:0x4d77e],'big')==int.from_bytes(y[0x4d77c:0x4d77e],'big')==0
assert x[0x4d694:0x4d696]==y[0x4d694:0x4d696]==bytes.fromhex('00a0')
audio_offsets={hex(o) for o in list(range(0x4d692,0x4d694))+list(range(0x4d7dc,0x4d7e6))}
assert set(changes[0]['unexplained'])<=audio_offsets
assert not changes[1]['unexplained'] and not changes[2]['unexplained']
report=dict(images=images,clocks=clocks,hunks=changes,strict_game_state_equal=False,audio=dict(queue_count=0,changed_record_index=9,changed_record_is_inactive=True,current_period_off=int.from_bytes(x[0x4d692:0x4d694],'big'),current_period_on=int.from_bytes(y[0x4d692:0x4d694],'big'),requested_period=160,period_copied_by_audio_interrupt='0x4d67e'),all_other_game_state_equal=True)
(r/'project-scene-comparison.json').write_text(json.dumps(report,indent=2));print(report)

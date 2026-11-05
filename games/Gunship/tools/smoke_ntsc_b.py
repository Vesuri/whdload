from session_a import Session
from route import run
from flight_profile import ROUTE,window
from pathlib import Path
import sys,json,struct
s=Session(sys.argv[1])
try:
 # Disposable runtime fixture: use the known live PAL pilot roster; NTSC archive pilots are all dead/missing.
 roster=Path('tmp/game/Gunship/data/Roster/Gunship_roster').read_bytes()
 (s.run/'dh1/data/Roster/Gunship_roster').write_bytes(roster)
 run(s,ROUTE);s.shot('start.png');window(s,s.fields);s.shot('end.png')
 mem=s.read(0x200000,0x800000);(s.out/'fast.bin').write_bytes(mem)
 # Locate the already-patched code by long stable slices and a segment header.
 original=Path('tmp/analysis/gamemule-1489.h0').read_bytes()
 sig=bytes.fromhex('4cdf4cfc');hits=[];pos=0
 while True:
  pos=mem.find(sig,pos)
  if pos<0:break
  base=pos-0x2f2a
  if base>=8 and int.from_bytes(mem[base-8:base-4],'big')==len(original)+8:hits.append(base)
  pos+=1
 assert len(hits)==1,hits
 off=hits[0];patches=[0x2d80,0x2ef6,0x30c2,0x3196,0x31e2,0x863e,0x88f0,0x8bee,0x8d56,0x8d92,0x91b0,0x925a,0x930e,0x9354]
 for p in patches:assert mem[off+p:off+p+2]==b'\x4e\xb9' and mem[off+p+6:off+p+8]==b'\x4e\x71'
 (s.out/'accepted.json').write_text(json.dumps(dict(live_hunk=off+0x200000,loops=len(patches),pixel_call=mem[off+0x82a6:off+0x82ac].hex()),indent=2))
 print('NTSC flight and all 14 runtime patches verified',flush=True)
finally:s.quit()

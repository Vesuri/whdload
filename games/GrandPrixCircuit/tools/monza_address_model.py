"""Exhaust the native grid and view arithmetic at every 64 KB alignment."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
raw=(root/'tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit/data/GrandPrixCircuit').read_bytes()[40:]
sites={0x9fc2:'5343',0xa020:'5d43',0xa054:'5240',0x8304:'d87c002829449e40',0xa7a4:'987c001441ecffa2'}
for off,b in sites.items():assert raw[off:off+len(bytes.fromhex(b))]==bytes.fromhex(b)
def word_add(a,n):return (a&~65535)|((a+n)&65535)
def grid(origin,add):
 p=origin+29;out=[]
 for _ in range(5):
  out.append(p);p=add(p,-1);out.append(p);p=add(p,-6)
 return out
expected=[29,28,22,21,15,14,8,7,1,0]
counts=dict(grid_alignments=0,player_rank_cases=0,forward_windows=0,rear_windows=0)
for low in range(65536):
 origin=0x980000+low;want=[origin+i for i in expected]
 fixed=grid(origin,lambda a,n:a+n);assert fixed==want
 old=grid(origin,word_add);counts['grid_alignments']+=old!=want
 for pos in want:
  assert pos+1-origin in [x+1 for x in expected]
  counts['player_rank_cases']+=word_add(pos,1)!=pos+1
 assert origin+40-(origin-20)==60
 counts['forward_windows']+=word_add(origin,40)!=origin+40
 counts['rear_windows']+=word_add(origin,-20)!=origin-20
examples={}
for low in [0xffe8,0xfff2]:
 origin=0x980000+low;examples[hex(low)]={'native_relative_grid':[p-origin for p in grid(origin,word_add)],'correct_relative_grid':expected,'pole_camera':hex(origin+30),'native_bucket_origin':hex(word_add(origin+30,-20)),'correct_bucket_origin':hex(origin+10)}
r={'alignments_checked':65536,'grid_rank_cases_checked':655360,'native_error_counts':counts,'examples':examples,'native_spans_verified':{hex(k):v for k,v in sites.items()}}
(root/'tmp/phase8/monza-address-model.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))

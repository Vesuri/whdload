import json
import replay_a
oldroute=replay_a.route
addr=None
def route(s):
 global addr
 r=oldroute(s);entry=replay_a.rd(s,0xb1996);code=replay_a.read_bytes(s,entry,512);offset=code.find(b'RREDGE01');assert offset>=0
 addr=entry+offset+8;return r
oldsnap=replay_a.snapshot
def snapshot(s):
 r=oldsnap(s)
 if r['field']==1600:
  count=replay_a.rd(s,addr);bad=replay_a.rd(s,addr+4);assert count>1000 and bad==0,(count,bad)
  (s.out/'edge-audit.json').write_text(json.dumps(dict(calls=count,mismatches=bad))+'\n');print('edge audit',count,bad,flush=True)
 return r
replay_a.route=route;replay_a.snapshot=snapshot;replay_a.main()

import sys,json
from harness_a import *
from amigaxdev.aprof import parse_profile
s=Session(sys.argv[1])
try:
 route(s);s.input('JOY2_UP',1);advance(s,300);before=counters(s,stats_address(s));s.cmd('monitor aprof start');advance(s,800);p=s.out/'aprof.txt';s.cmd(f'monitor aprof stop {p}');after=counters(s,stats_address(s));header,pcs,nodes=parse_profile(p.read_text())
 total=sum(v[0] for v in pcs.values());regions={}
 for label,lo,hi in [('physics',0x8b486,0x8eff8),('vsync_poll',0xaecf0,0xaecf6),('blit_b17',0xb17e0,0xb17f2),('blit_b18',0xb1868,0xb1880)]:
  rows=[v for pc,v in pcs.items() if lo<=pc<hi];regions[label]=dict(units=sum(v[0] for v in rows),executions=sum(v[1] for v in rows),chip_units=sum(v[2] for v in rows),chip_accesses=sum(v[3] for v in rows))
 r=dict(provenance=provenance(os.environ['SLAVE'],s),frames=after['frames']-before['frames'],total_units=total,regions=regions,top_chip=sorted((dict(pc=hex(pc),units=v[0],executions=v[1],chip_units=v[2],chip_accesses=v[3]) for pc,v in pcs.items()),key=lambda x:x['chip_units'],reverse=True)[:12]);(s.out/'profile.json').write_text(json.dumps(r,indent=2)+'\n');print('frames',r['frames'],'regions',regions,flush=True)
finally:s.quit()

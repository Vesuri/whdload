import json,os,shutil,struct,sys
from capture_demo import ROOT
from capture_session import Session
os.chdir(ROOT);out=ROOT/'tmp/prof'/sys.argv[1];out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s4-replay-audio-math.slave',out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x8520);s.env['WHD_ARGS']+=' CUSTOM1=1'
try:
 s.boot();hits=[]
 for _,b in s.dump_banks('audio-math'):
  i=b.find(b'HDRASND1')
  if i>=0:hits.append(b[i+8:i+8+512])
 assert len(hits)==1;raw=hits[0];cases=[]
 for case,count in enumerate([90,4,0,90]):
  expected=[i for i in range(count) if ((79+i)%90)%3==0]
  block=raw[case*128:(case+1)*128];events=[struct.unpack_from('>HH',block,i*4) for i in range(len(expected))]
  assert events==[(i,4) for i in expected],(case,events,expected)
  assert block[4*len(expected):120]==bytes.fromhex('deadbeef')*(30-len(expected))
  actual=struct.unpack_from('>HHI',block,120);assert actual==(len(expected),(count-1)&65535,len(expected)),(case,actual)
  cases.append(dict(count=count,events=events,visits=91 if case==3 else 10))
 r=dict(passed=True,cases=cases);(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(dict(passed=True,cases=4,requests=sum(len(c['events']) for c in cases)))
finally:s.close()

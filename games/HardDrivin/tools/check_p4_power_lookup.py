from pathlib import Path
exec(Path('tools/check_p4_first.py').read_text().split('try:\n',1)[0])
phase=Path('src/HardDrivinPhase.s').read_text();body=phase[phase.index('_phase_power:'):];addr=0x415000
source=f' org ${addr:x}\nPH_ACTIVE equ 2\n_phase_state equ ${symbols[1]["_phase_state"]:x}\n_drivetrain_power equ ${symbols[1]["_drivetrain_power"]:x}\n'+body
stem=Path('tmp/p4-power-lookup');stem.with_suffix('.s').write_text(source)
subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-L',str(stem.with_suffix('.lst')),'-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
write(addr,stem.with_suffix('.bin').read_bytes());lookupsy={n:int(v,16) for v,n in re.findall(r'^([0-9A-F]+) (_\w+)$',stem.with_suffix('.lst').read_text(),re.M)};symbols[1]['_phase_power']=addr
ratios=[(0,800),(7,800),(9,750),(10,600),(10,450)];counts={}
try:
 for variant in ['first','ready','inactive','mismatch']:
  count=0
  for gear in range(1,5):
   for byte in range(256):
    th=byte if byte<128 else byte-256;table=list(ratios)
    if variant=='mismatch':table[1+byte%4]=(table[1+byte%4][0],table[1+byte%4][1]+1)
    def setup(sy):
     reg(3,0x470000+4*gear);reg(6,0x470100);pack(0x4700f2,'H',0x1234)
     for k,pair in enumerate(table):pack(0x470000+4*k,'hh',*pair)
     pack(a4-0x66e4,'b',th);pack(a4-0x66ca,'H',gear);pack(sy['_phase_state']+2,'H',int(variant!='inactive'));pack(sy['_drivetrain_state']+6,'H',1);write(sy['_drivetrain_power_state'],bytes(24));pack(lookupsy['_phase_power_status'],'h',1 if variant=='ready' else 0)
    outs=[]
    for j,name in [(0,'_drivetrain_power'),(1,'_phase_power')]:
     z=run(j,name,setup=setup);outs.append(([v for k,v in enumerate(z[2]) if k not in [0,1,6,9]],read(0x4700f2,2)))
    assert outs[0]==outs[1],(variant,gear,th,outs)
    status=struct.unpack('>h',read(lookupsy['_phase_power_status'],2))[0]
    assert status==(-1 if variant=='mismatch' else 0 if variant=='inactive' else 1),(variant,status)
    count+=1
  counts[variant]=count
 report=dict(passed=True,cases=sum(counts.values()),paths=counts,scope='Complete assembled guarded lookup against original native power helper; all signed throttle bytes and four gears, first validation/cached validation/inactive/unexpected table paths; D0/D4/native local and preserved registers exact. D1/A0/A1 caller scratch and unused memo bookkeeping excluded.')
 Path('tmp/p4-power-lookup-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))

from pathlib import Path
p=Path(__file__).with_name('capture_hi25_profile.py');s=p.read_text().replace("kind='hi25-profile'","kind='h9-planes'")
a=s.index(" mode=os.environ.get('RENDER_CAPTURE'");b=s.index('\nfinally:',a)
s=s[:a]+'''
 cmd('delete');cmd(f'break *{addresses.map(0x6abcc)}')
 samples=[]
 for n in range(8):
  assert 'Breakpoint' in cmd('continue')
  regs=cmd('info registers')
  data=dump('prefill')
  u=lambda x:struct.unpack_from('>I',data,x)[0]
  w=lambda x:struct.unpack_from('>h',data,x)[0]
  ptr=u(addresses.map(0x226ae));planes=[u(ptr),u(ptr+4)]
  coords={hex(x):[w(addresses.map(x)+i*2) for i in range(30)] for x in [0x66cb8,0x66cf4,0x66d30,0x66d6c,0x66da8,0x66de4,0x66e20,0x66e5c,0x66e98,0x66ed4,0x66f10,0x66f4c]}
  for j,plane in enumerate(planes):(out/f'plane-{n}-{j}.bin').write_bytes(data[plane:plane+9600])
  samples.append(dict(planes=planes,height=100+w(addresses.map(0x66c8c)),coords=coords,caller=hex(addresses.map(u(val('$sp')),True)),regs=regs))
 report['samples']=samples;report['status']='passed';(out/'result.json').write_text(json.dumps(report,indent=2)+'\\n')
 print('captured',out,flush=True)
''' +s[b:]
exec(compile(s,str(p),'exec'))

from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'tools/test_production_smoke.py').read_text();s=s.replace("kind='production-smoke'","kind='production-state-'+os.environ.get('ARM','production')").replace("b=r/'tmp/build/production/FerrariFormulaOne.slave'","arm=os.environ.get('ARM','production');b=r/'tmp/build/production-matched/FerrariFormulaOne.slave' if arm=='production' else r/('tmp/build/step5-c4-divide-frame-r3g-v1-ab/000/candidate.slave' if profile.startswith('a500') else 'tmp/build/step5-c2/020/candidate.slave' if profile=='a1200' else 'tmp/build/step5-b8-v3-source/lean/fine.slave')")
a=s.index(" build=json.loads");z=s.index(" report.update(host=",a)
s=s[:a]+''' import re
 kind='000' if profile.startswith('a500') else '020' if profile=='a1200' else 'fine'
 if arm=='production':
  build=json.loads((b.parent/'build.json').read_text());hs=build['host_symbols'];module=build['payloads'][kind];sy=module['symbols'];host=marker-hs['FF1PublicMarker'];probe=host+module['offset']
 else:
  def symbols(path):return {n:int(v,16) for n,v in re.findall(r'^(\\w+)\\s+00:([0-9A-F]{8})$',path.read_text(errors='replace'),re.M)}
  hs=symbols(r/'tmp/build/step5-b7-loader-v3/build.list');sy=symbols(b.parent/'fine.list');host=marker-hs['FF1PublicMarker'];probe=host+len((r/'tmp/build/step5-b7-loader-v3/FerrariFormulaOne.slave').read_bytes())-36
'''+s[z:]
s=s.replace("selection=val(f'*(unsigned int*){host+hs[\"FF1ProfileMode\"]}')","arm=arm")
s=s.replace("faults=['FF1WrongVersion']","faults=['FF1WrongVersion'] if arm=='production' else []")
s=s.replace("sy['schedule_end' if kind=='fine' else 'C1Checkpoint']","sy['FF1PresentationAfterTick' if kind=='fine' else 'C1Checkpoint']")
a=s.index(" report['context_before']");z=s.index('\nfinally:',a)
s=s[:a]+''' from step5_b7_addresses import Addresses
 memory=dump('anchor');addresses=Addresses(memory,table)
 blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks']+[dict(name='gear',address='0x6bf84',bytes=4),dict(name='instrument_phase',address='0x6c942',bytes=6),dict(name='instrument_rates',address='0x66c88',bytes=4),dict(name='flag_counter',address='0x66be0',bytes=2),dict(name='pit_flags',address='0xd0dc',bytes=8)]
 (out/'blocks.json').write_text(json.dumps(blocks,indent=2));(out/'addresses.json').write_text(json.dumps(addresses.rows,indent=2))
 records=[];private=[]
 cmd('monitor warp 0')
 for step in range(100):
  if step:assert 'Breakpoint' in cmd('continue')
  memory=dump('sample');canonical=addresses.canonical_memory(memory)
  records.append(b''.join(canonical[int(x['address'],16):int(x['address'],16)+x['bytes']] for x in blocks))
  if kind=='fine':
   private.append({n:memory[probe+sy[n]:probe+sy[n]+size].hex() for n,size in [('velocity_shadow',12),('position_shadow',12),('heading_shadow',12),('speed_shadow',6),('steering_shadow',18),('wear_remainders',8),('fuel_remainders',2)]})
  if step%25==0:print(profile,arm,step,flush=True)
 (out/'records.bin').write_bytes(b''.join(records));(out/'private.json').write_text(json.dumps(private))
 report['context_after']=list(struct.unpack_from('>14I',memory,ctx));report['error']=val(f'*(unsigned int*){probe+sy["error"]}');report['status']='captured';report['steps']=100
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\\n');print(report,flush=True)
'''+s[z:]
(r/'tools/capture_production_states.py').write_text(s)

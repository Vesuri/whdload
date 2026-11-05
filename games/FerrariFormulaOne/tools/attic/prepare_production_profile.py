from pathlib import Path
import json,re,struct,shutil
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/production-matched';build=json.loads((b/'build.json').read_text());p=r/'tmp/build/production-profile'
for arm in ['accepted','production']:
 o=p/arm;o.mkdir(parents=True,exist_ok=True)
 if arm=='production':raw=(b/'FerrariFormulaOne.slave').read_bytes();info=build['payloads']['fine'];sy=info['symbols'];offset=info['offset'];listing=b/'fine/fine.list';hs=build['host_symbols']
 else:
  original=r/'tmp/build/step5-b8-v3-source/lean/fine.slave';raw=original.read_bytes();listing=original.with_suffix('.list');sy={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',listing.read_text(),re.M)};offset=len((r/'tmp/build/step5-b7-loader-v3/FerrariFormulaOne.slave').read_bytes())-36;hs={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',(r/'tmp/build/step5-b7-loader-v3/build.list').read_text(errors='replace'),re.M)}
 code=bytearray(raw[32:-4]);code+=bytes(build['bytes']-len(raw));header=bytearray(raw[:32]);struct.pack_into('>I',header,20,len(code)//4);struct.pack_into('>I',header,28,len(code)//4);struct.pack_into('>H',code,offset+sy['B8DrawEnabled'],0)
 (o/'fine.slave').write_bytes(header+code+bytes.fromhex('000003f2'));shutil.copy2(listing,o/'fine.list');(o/'fine.json').write_text(json.dumps({'symbols':sy,'offset':offset,'host_symbols':hs,'listing':str(o/'fine.list')}))
s=(r/'tools/capture_production_frames.py').read_text().replace("kind='production-frame-'","kind='production-profile-'").replace("b=r/f'tmp/build/production-frames/{arm}-{kind}.slave'","b=r/f'tmp/build/production-profile/{arm}/fine.slave'").replace("FSUAE=str(r/'tmp/step5-frame-observer-build/fs-uae'),FF1_FRAME_SENTINEL='0'","FSUAE=str(r/'tmp/step3/fs-uae')")
a=s.index(' from amigaxdev import barto');z=s.index('\nfinally:',a)
s=s[:a]+''' from step5_b7_addresses import Addresses
 cmd('monitor warp 0');cmd('ignore $bpnum 5');assert 'Breakpoint' in cmd('continue')
 memory=dump('start-raw');addresses=Addresses(memory,table);(out/'start.bin').write_bytes(addresses.canonical_memory(memory));(out/'addresses.json').write_text(json.dumps(addresses.rows,indent=2))
 cmd('delete');cmd(f'monitor profile 48 "" "{out}/detail.bin"')
 memory=dump('end-raw');(out/'end.bin').write_bytes(addresses.canonical_memory(memory));report['normalization']=addresses.normalize_trace(out/'detail.bin')
 report['slave']=str(b);report['status']='complete';report['error']=val(f'*(unsigned int*){probe+sy["error"]}');assert report['error']==0
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\\n');print(profile,arm,'profile captured',flush=True)
'''+s[z:]
(r/'tools/capture_production_profile.py').write_text(s)

from pathlib import Path
r=Path(__file__).resolve().parents[1];s=(r/'tools/capture_production_states.py').read_text();s=s.replace("kind='production-state-'","kind='production-frame-'")
a=s.index("arm=os.environ.get('ARM'");b=s.index(';profiles=json.loads',a)
s=s[:a]+"arm=os.environ.get('ARM','production');kind='000' if profile.startswith('a500') else '020' if profile=='a1200' else 'fine';b=r/f'tmp/build/production-frames/{arm}-{kind}.slave'"+s[b:]
a=s.index(" if arm=='production':\n  build=");b=s.index(' report.update(host=',a)
s=s[:a]+''' meta=json.loads(b.with_suffix('.json').read_text());hs=meta['host_symbols'];sy=meta['symbols'];host=marker-hs['FF1PublicMarker'];probe=host+meta['offset']
'''+s[b:]
a=s.index(' from step5_b7_addresses import Addresses');b=s.index('\nfinally:',a)
s=s[:a]+''' from amigaxdev import barto
 from PIL import Image
 listing=Path(meta['listing']).read_text();instruction='bsr.l B8Draw' if kind=='fine' else 'bsr.w B8Draw'
 matches=[int(m[1],16) for m in re.finditer(r'^00:([0-9A-F]{8}) [0-9A-F]+\\s+\\d+:\\s+'+re.escape(instruction)+r'$',listing,re.M)]
 assert len(matches)==1,matches
 draw_return=probe+matches[0]+(6 if kind=='fine' else 4)
 cmd('monitor warp 0');cmd('delete');cmd(f'break *{draw_return}');frames=[]
 for i in range(30):
  assert 'Breakpoint' in cmd('continue')
  completed=val(f'*(unsigned int*){ctx+24}')
  path=out/f'frame-{completed}.bin';cmd(f'monitor profile 1 "" "{path}"')
  _,pixels=barto.last_screenshot(path);png=path.with_suffix('.png');png.write_bytes(pixels);path.unlink()
  im=Image.open(png).convert('RGB');frames.append({'update':completed,'size':im.size,'pixel_sha256':hashlib.sha256(im.tobytes()).hexdigest()})
 report['frames']=frames;report['error']=val(f'*(unsigned int*){probe+sy["error"]}');report['status']='captured';assert report['error']==0
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\\n');print(profile,arm,'captured',len(frames),'frames',flush=True)
'''+s[b:]
s=s.replace("FSUAE=str(r/'tmp/step3/fs-uae-q03-final')","FSUAE=str(r/'tmp/step5-frame-observer-build/fs-uae'),FF1_FRAME_SENTINEL='0'")
(r/'tools/capture_production_frames.py').write_text(s)

from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'tools/capture_release_frames.py').read_text().replace("kind='release-frame-'","kind='h2-frame-'").replace("b=r/f'tmp/build/production-frames/{arm}-{kind}.slave'","b=Path(os.environ['H2_BUILD'])/'FerrariFormulaOne.slave'").replace("meta=json.loads(b.with_suffix('.json').read_text());", "build=json.loads((b.parent/'build.json').read_text());meta=dict(build['payloads'][kind],host_symbols=build['host_symbols'],listing=str(b.parent/kind/'fine.list')); ")
(r/'tools/capture_h2_frames.py').write_text(s)
s=(r/'tools/test_h2_timing.py').read_text();a=s.index(" report['fps_start']=context()");z=s.index(" report['error']=val",a)
s=s[:a]+''' report['fps_start']=context();intervals=[];last=report['fps_start'][0]
 for i in range(300):
  assert 'Breakpoint' in cmd('continue')
  now=val(f'*(unsigned int*){ctx}');intervals.append(now-last);last=now
 report['fps_end']=context();fields=sum(intervals)
 import statistics,math
 report['fps']=300/(fields*71051/3546895);report['fps_fields']=fields;report['interval_fields']=intervals;report['mean_ms']=statistics.mean(intervals)*71051/3546895*1000;report['p95_ms']=sorted(intervals)[math.ceil(len(intervals)*.95)-1]*71051/3546895*1000
 if 'HeavyFrames' in sy:
  report['heavy_frames']=val(f'*(unsigned int*){probe+sy['HeavyFrames']}');report['heavy_incomplete']=val(f'*(unsigned int*){probe+sy['HeavyIncomplete']}');assert report['heavy_incomplete']==0
'''+s[z:];s=s.replace('<=1 and simulated==60','<=.25 and simulated==60');(r/'tools/test_h2_timing.py').write_text(s)
a=s.index(" cmd('monitor warp 0');cmd('ignore $bpnum 9')");b=s.index(' listing=',a);s=s[:a]+" cmd('monitor warp 0')\n def context():return [val(f'*(unsigned int*){ctx+i*4}') for i in range(14)]\n"+s[b:];s=s.replace("kind='drive-timing'","kind='h2-fps'").replace("publication}');assert 'Breakpoint' in cmd('continue')","publication}');cmd('ignore $bpnum 99');assert 'Breakpoint' in cmd('continue')");(r/'tools/test_h2_fps.py').write_text(s)
s=(r/'tools/test_production_live.py').read_text().replace("b=r/'tmp/build/production/FerrariFormulaOne.slave'","b=Path(os.environ['H2_BUILD'])/'FerrariFormulaOne.slave'").replace("kind='production-live'","kind='h2-live'").replace("WHD_ARGS='CUSTOM1=1 CUSTOM2=1'","WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache'");(r/'tools/test_h2_live.py').write_text(s)
s=(r/'tools/run_release_modal.py').read_text().replace('test_release_live.py','test_h2_live.py').replace('release-modal-f10-replay.json','production-modal-replay.json');(r/'tools/run_h2_live.py').write_text(s)
s=(r/'tools/test_drive_manual.py').read_text().replace("b=r/'tmp/build/drive-fix/FerrariFormulaOne.slave'","b=Path(os.environ['H2_BUILD'])/'FerrariFormulaOne.slave'");(r/'tools/test_h2_manual.py').write_text(s)
s=(r/'tools/run_release_modal.py').read_text().replace('test_release_live.py','test_h2_manual.py').replace('   replay=subprocess.run(',"   subprocess.run([sys.executable,str(r/'tools/control_step5_c4_q03.py'),str(r/'tools/drive-select-f1.json')],check=True)\n   replay=subprocess.run(").replace('release-modal-f10-replay.json','drive-manual-test.json');(r/'tools/run_h2_manual.py').write_text(s)

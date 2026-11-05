from pathlib import Path
import json
r=Path(__file__).resolve().parents[1]
s=(r/'tools/test_h5_live.py').read_text().replace("kind='h5-live'","kind='h7-live'").replace("FSUAE=str(r/'tmp/step3/fs-uae-q03-final')","FSUAE=os.environ.get('RELEASE_FSUAE',str(r/'tmp/h7-irq-observer-build/fs-uae'))").replace("if profile.startswith('a1200') else os.environ['KICKSTART']","if not profile.startswith('a500') else os.environ['KICKSTART']").replace("else 0x600000","else 0x200000+int(os.environ['FAST_KB'])*1024")
s=s.replace("(struct.unpack_from('>H',m,probe+sy['C4BlitOwned'])[0] if kind=='000' else 0)","(struct.unpack_from('>H',m,probe+sy['FF1FineBlitActive'])[0] if 'FF1FineBlitActive' in sy else 0)")
s=s.replace("v['intena']=int(cmd('monitor irq-state').strip());report[label]=v;save();return m,v",'''v['intena']=val('*(unsigned short*)0xdff01c')
  v['saved_blit']=struct.unpack_from('>H',m,probe+sy['FF1FineBlitSaved'])[0] if 'FF1FineBlitSaved' in sy else 0
  v['blit_control']=struct.unpack_from('>H',m,probe+sy['FF1FineBlitControl'])[0] if 'FF1FineBlitControl' in sy else 0
  execbase=struct.unpack_from('>I',m,4)[0];server=struct.unpack_from('>III',m,execbase+84+6*12);v['blit_server']=[hex(x) for x in server]
  gfx=server[0];v['gfx_queue_heads']=[hex(struct.unpack_from('>I',m,gfx+x)[0]) for x in (0x3a,0x42)]
  v['irq_log_offset']=(r/'amiga/.run/fsuae/Cache/Logs/fs-uae.log.txt').stat().st_size
  report[label]=v;save();return m,v''')
s=s.replace(" cmd('monitor warp 0')\n key('KEY_SPACE',0x40)"," memory,entry=snapshot('demo-entry')\n cmd('monitor warp 0')\n key('KEY_SPACE',0x40)")
s=s.replace("memory,take=snapshot('takeover')","memory,take=snapshot('takeover')\n if take['blit_control']:assert take['owned']==1 and not take['intena']&64")
s=s.replace("advance_fields(50)","if take['blit_control']:assert paused['intena']&64==take['saved_blit']\n advance_fields(50)")
s=s.replace("report['pause_exact_debt_preserved']=True", "if take['blit_control']:assert resume['owned']==1 and not resume['intena']&64 and resume['saved_blit']==take['saved_blit']\n report['pause_exact_debt_preserved']=True")
s=s.replace("assert ex['owned']==0", "assert ex['owned']==0\n if take['blit_control']:assert ex['intena']&64==resume['saved_blit']")
s=s.replace("finally:\n", "finally:\n import shutil\n for artifact in ('launch.json','fsuae.log'):\n  if (r/'amiga/.run'/artifact).exists():shutil.copy(r/'amiga/.run'/artifact,out/artifact)\n")
s=s.replace(" if s.g:s.g.p.kill()"," if (r/'amiga/.run/fsuae/Cache/Logs/fs-uae.log.txt').exists():\n  with (r/'amiga/.run/fsuae/Cache/Logs/fs-uae.log.txt').open(errors='replace') as irqlog:(out/'irq-native.log').write_text(''.join(line for line in irqlog if 'H7_INTENA' in line))\n if s.g:s.g.p.kill()")
(r/'tools/test_h7_live.py').write_text(s)
s=(r/'tools/run_h5_live.py').read_text().replace('test_h5_live.py','test_h7_live.py').replace('h5-modal-replay.json','h7-modal-replay.json');(r/'tools/run_h7_live.py').write_text(s)
a=json.loads((r/'tools/h5-modal-replay.json').read_text())
for row in a:
 if row.get('op')=='exec' and "report['status']='passed'" in row['code']:
  row['code']=row['code'].replace("report['status']='passed'", "if take['blit_control']:assert settled['owned']==1 and not settled['intena']&64\nreport['status']='passed'")
(r/'tools/h7-modal-replay.json').write_text(json.dumps(a,indent=2)+'\n')

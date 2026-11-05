import sys,json,struct,re,hashlib
from pathlib import Path
root=Path(sys.argv[1]);other=Path(sys.argv[2]) if len(sys.argv)>2 else None
rows=[];differences={k:[] for k in ('state','front','tape')}
for p in sorted(root.glob('state-*.bin')):
 field=int(p.stem.split('-')[1]);b=p.read_bytes()
 def v(o,fmt):return struct.unpack_from('>'+fmt,b,0x7100+o)[0]
 t=(root/f'tape-{field:05d}.bin').read_bytes();assert struct.unpack_from('>I',t,4)[0]==field;assert t[2]==0,'keyboard overflow'
 row=dict(field=field,pose=[v(o,'H') for o in [-0x670a,-0x6708,-0x6706]],heading=v(-0x66b6,'h'),speed=v(-0x66d4,'h'),gear=v(-0x66ca,'h'),throttle=v(-0x66e4,'B'),crash=v(-0x69fa,'B'),replay=v(-0x5229,'B'),checkpoint=hex(v(-0x5234,'I')),countdown=b[0x7100-0x6868:0x7100-0x6864].hex(),lap=b[0x7100-0x6870:0x7100-0x686c].hex())
 rows.append(row)
 if other:
  for k in differences:
   fn=f'{k}-{field:05d}.bin'
   if (root/fn).read_bytes()!=(other/fn).read_bytes():differences[k].append(field)
assert rows and [r['field'] for r in rows]==list(range(1,rows[-1]['field']+1))
events=[(int(a,16),int(f)) for a,f in re.findall(r'^EVENT ([0-9a-f]+) (\d+)$',(root/'capture.log').read_text(),re.M)]
checkpoints=[rows[i]['field'] for i in range(1,len(rows)) if rows[i]['checkpoint']!=rows[i-1]['checkpoint']]
report=dict(fields=len(rows),swaps=sum(a==0xb4 for a,f in events),physics_calls=sum(a==0xcdae for a,f in events),replay_iterations=sum(a==0x10bb6 for a,f in events),checkpoint_changes=checkpoints,crash_fields=[r['field'] for r in rows if r['crash']],replay_fields=[r['field'] for r in rows if r['replay']],repeat_mismatches=differences if other else None)
(root/'state-summary.json').write_text(json.dumps(dict(summary=report,per_field=rows,events=events),indent=2)+'\n')
print(json.dumps({k:((min(v),max(v),len(v)) if k in ('crash_fields','replay_fields') and v else v) for k,v in report.items()},indent=2))

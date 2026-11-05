"""Validate changing input coverage from retained controls-entry snapshots."""
import json,re,struct,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/'src/HardDrivinVerify.s').read_text().split('_verify_drive_tape:\n',1)[1].split('\n\tdc.l -1',1)[0]
records=[tuple(map(int,m)) for m in re.findall(r'dc.l (\d+)\s+dc.w (\d+),(\d+),(\d+),(\d+)',s)]
assert records and all(r[4]==0 for r in records)
out=root/'tmp/prof'/sys.argv[1];meta=json.loads((out/'metadata.json').read_text());size=meta['snapshot_size'];raw=subprocess.check_output(['zstd','-qdc',str(out/'controls.bin.zst')]);count=len(raw)//size;assert len(raw)%size==0
indices=[];mouse=[]
for i in range(count):
 # Controls entry is before the fixture publishes this pass's input. It still
 # holds the previous pass's mouse position; native button clearing is separate.
 field=1+8*(i-1)
 selected=max((j for j,r in enumerate(records) if r[0]<=field),default=-1)
 expected=records[selected][1:3] if selected>=0 else (320,200)
 got=struct.unpack_from('>2h',raw,i*size+0x95fa-0x8002)
 assert got==expected,(i,field,got,expected)
 mouse.append(got);indices.append(selected)
assert set(range(len(records)))<=set(indices)
report=dict(passed=True,controls_entries=count,distinct_mouse_positions=len(set(mouse)),records=len(records),observed_record_indices=sorted(set(indices)),last_consumed_record_field=records[indices[-1]][0],scope='Previous-pass mouse state at native controls entry; paired world checker separately compares button/key inputs. Original field timing is not asserted.')
(out/'input-tape-coverage.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k!='observed_record_indices'})

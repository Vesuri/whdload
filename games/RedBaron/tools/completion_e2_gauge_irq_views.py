"""Continue the existing gauge flight with native CIA keyboard events."""
import socket
from pathlib import Path
s=Path('tools/completion_e2_gauge_views_resume.py').read_text()
exec(s[:s.index('rows=json.loads')])
def hardware(mode,key):
 with socket.socket(socket.AF_UNIX) as sock:
  sock.connect(str(Path('tmp/run/default/.run/completion-input.sock').resolve()))
  sock.sendall(f'{mode}:{sim},200588,{key}'.encode());answer=sock.recv(65536).decode()
  assert answer.startswith('OK '),answer
  print(answer,flush=True)
def fields(count):
 raw=r.command(f'gdb delete\nbreak *{sim+0x2d34e:#x}\nignore $bpnum {count-1}\ncontinue\ndelete')
 from completion_soak import check_segment
 check_segment(raw+'\nSOAK_SEGMENT_COMPLETE',sim+0x2d34e)
 return raw
def tap(key):
 hardware('irq-down',key);fields(10)
 hardware('irq-up',key);fields(10)
 print(advance(8),flush=True)
rows=json.loads((out/'views.json').read_text())
for label,key,v in [('rear',0x51,1),('left',0x52,2),('right',0x53,3),('front-return',0x50,0)]:
 tap(key);view(label,v)
from instrument_view_result import check as check_views
result=check_views((out/'front-instrument_cache_twin_result.bin').read_bytes(),(out/'front-instrument_cache_stats.bin').read_bytes(),rows)
(out/'view-result.json').write_text(json.dumps(result,indent=2)+'\n')
print('VIEW TRANSITIONS COMPLETE; flight paused for map check',flush=True)

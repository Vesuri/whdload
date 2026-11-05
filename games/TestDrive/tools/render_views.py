#!/usr/bin/env python3
"""Read-only row, traffic and scanline capture from an existing native session."""
import json,re,sys
from pathlib import Path
from harness import ROOT,server,command,dump

def capture(folder,rr):
 folder.mkdir(parents=True,exist_ok=False);h=rr['h4'];db=rr['td-data'];rel=folder.relative_to(ROOT)
 for view,entry,ret in [('main',0x1114,0x116a),('mirror',0x11a2,0x11f2)]:
  server.request('until '+hex(h+entry))
  text=command('\n'.join(['cd '+str(ROOT),f'break *{h+0x1a38:#x}',f'break *{h+0x1b54:#x}','set $td_row=0','continue',f'while $pc != {h+0x1b54:#x}',f'eval "dump binary memory {rel}/{view}-%02d.bin {db:#x} {db+0x32a4:#x}", $td_row',f'eval "dump binary memory {rel}/{view}-%02d-desc.bin $a2 $a2+4", $td_row','set $td_row=$td_row+1','continue','end','delete']))
  (folder/(view+'-gdb.txt')).write_text(text)
  dump(folder/(view+'-before.bin'),db,db+0x32a4)
  server.request('until '+hex(h+ret))
  dump(folder/(view+'-after.bin'),db,db+0x32a4)
 (folder/'metadata.json').write_text(json.dumps(rr,indent=2)+'\n')
if __name__=='__main__':
 p=Path(sys.argv[1]).resolve();meta=json.loads((p/'capture.json').read_text())
 capture(p/sys.argv[2],meta['regions'])

#!/usr/bin/env python3
"""C2 live gate from the diagnostic's actual world-boundary observations."""
import argparse,json,re,struct
from pathlib import Path
from cd32_runtime import ROOT

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--build',type=Path,required=True);p.add_argument('--layout',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists() or (ROOT/'tmp').resolve() not in a.output.resolve().parents:p.error('fresh tmp output required')
 meta=json.loads((a.run/'result.json').read_text());build=json.loads((a.build/'build.json').read_text());assert meta['fixture']['sha256']==build['sha256']
 sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
 base=json.loads(a.layout.read_text())['slave']-0x200000;ram=(a.run/'fast.bin').read_bytes()
 def value(name):return struct.unpack_from('>I',ram,base+sy[name])[0]
 result={k:value('translation_'+k) for k in ('fields','ticks_checked','position_corrections','camera_corrections')}
 assert result['ticks_checked']>=100 and result['fields']>=500,'insufficient motion coverage'
 assert result['position_corrections']==result['camera_corrections']==0,'world-tick correction detected'
 result.update(passed=True,held_key=meta['held_key'],machine=meta['machine'],ntsc=meta['ntsc'])
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()

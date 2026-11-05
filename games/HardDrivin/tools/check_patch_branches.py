"""Reject external direct branches into the middle of a newly replaced range."""
import re,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];source=root/'src';ranges=[]
for name in ['HardDrivinScalar.s','HardDrivinMotion.s','HardDrivinTraffic.s','HardDrivinPresentation.s','HardDrivinDispatch.s','HardDrivinEvents.s','HardDrivinReplay.s','HardDrivinScene.s','HardDrivinRecord.s','HardDrivinTimeline.s','HardDrivinAttract.s','HardDrivinPhantom.s','HardDrivinGhostRecord.s','HardDrivinGhostPlayback.s','HardDrivinGhostPost.s','HardDrivinInstructions.s','HardDrivinAudio.s','HardDrivinDrivetrain.s','HardDrivinSweep.s','HardDrivinPhase.s','HardDrivinRender.s','HardDrivinRotation.s']:
 for m in re.finditer(r'PERF_(?:EXISTING_)?RANGE (\w+) \$([0-9a-f]+) \$([0-9a-f]+)',(source/name).read_text(),re.I):
  gate,begin,size=m.groups();ranges.append((int(begin,16),int(begin,16)+int(size,16),gate,name))
errors=[]
for line in (root/'tmp/analysis/code.dis').read_text().splitlines():
 m=re.match(r'\s*([0-9a-f]+):.*\t((?:b(?:ra|sr|eq|ne|ge|gt|le|lt|hi|ls|cc|cs|pl|mi|vc|vs)|db\w+|jsr|jmp)[.\w]*)\s+(.*)',line)
 if not m:continue
 src=int(m[1],16)
 for t in re.findall(r'0x([0-9a-f]+)',m[3]):
  target=int(t,16)
  for start,end,gate,name in ranges:
   if start<target<end and not start<=src<end:errors.append(dict(source=hex(src),target=hex(target),range=[hex(start),hex(end)],file=name))
print(json.dumps(dict(passed=not errors,ranges=len(ranges),errors=errors),indent=2));assert not errors

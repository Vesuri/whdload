import os,sys,json
from pacing_c import *
s=Session(sys.argv[1])
try:
 route(s);before=c_records(s)
 s.cmd('monitor key 40 1');s.cmd('monitor fields 9');s.cmd('monitor key 40 0');s.cmd('monitor fields 999');paused=c_records(s)
 s.cmd('monitor key 40 1');s.cmd('monitor fields 9');s.cmd('monitor key 40 0');s.cmd('monitor fields 99');after=c_records(s)
 (s.out/'pause.json').write_text(json.dumps(dict(before=before,paused=paused,after=after),indent=2))
 print('before',before['records'][-3:],'paused',paused['records'][-3:],'after',after['records'][-10:])
finally:s.quit()

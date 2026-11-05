import json,sys
from pathlib import Path
from profile_window import command
p=Path(sys.argv[1]);s=command('gdb monitor cacheinfo');(p/'cache-state.txt').write_text(s);print(s)

import os,re
if os.environ.get('P3_REQUIRE_DCACHE')=='1':
 observed=dict(re.findall(r'(\w+)=([0-9a-fA-F]+)',s))
 assert observed.get('DCACHE_EMULATION')=='1' and observed.get('CE')=='1',observed
 assert int(observed['CACR'],16)&0x100,observed

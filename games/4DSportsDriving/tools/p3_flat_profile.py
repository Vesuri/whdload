import json,sys
from pathlib import Path
from profile_window import command,ROOT
p=Path(sys.argv[1]).resolve()
print(command('gdb delete\nmonitor fields 1\nmonitor aprof start'),flush=True)
for n in (249,):print(command(f'gdb monitor fields {n}'),flush=True)
print(command('gdb monitor aprof stop '+str(p/'flat-profile.txt')),flush=True)
assert (p/'flat-profile.txt').exists()
lines=(p/'flat-profile.txt').read_text().splitlines();meta={s.split()[0]:s.split()[1] for s in lines if not s.startswith(('P ','N ','AITD'))}
assert int(meta['vsyncs'])==250,meta
(p/'flat-profile-meta.json').write_text(json.dumps(meta,indent=2)+'\n')

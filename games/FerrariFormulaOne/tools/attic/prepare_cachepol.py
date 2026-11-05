# Cache-policy candidate fixtures: the B8-PAL matched-state, grid and stable
# scanout fixtures rebuilt from the current Games source (cache policy applied).
from pathlib import Path
import re,json,shutil,subprocess,sys,struct
r=Path(__file__).resolve().parents[1]
s=(r/'tools/build_drive_matched.py').read_text().replace('drive-matched','render-cachepol-matched')
exec(compile(s,str(r/'tools/build_drive_matched.py'),'exec'))
helpers=(r/'tools/prepare_b8pal.py').read_text();helpers=helpers[helpers.index('def control('):helpers.index("base=r/'tmp/build/render-b8pal';")]
exec(helpers)
s=(r/'tools/build_hi25_fixtures.py').read_text().replace('render-h5-matched-source','render-cachepol-matched-source').replace('render-hi25-','render-cachepol-')
sys.argv=['build_hi25_fixtures.py','grid'];exec(compile(s,str(r/'tools/build_hi25_fixtures.py'),'exec'))
s=(r/'tools/build_b8pal_stable_frames.py').read_text()
s=s[s.index('for scene in'):].replace('render-b8pal-','render-cachepol-')
exec(compile(s,'stable','exec'))

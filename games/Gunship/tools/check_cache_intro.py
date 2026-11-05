import os,sys
from session_b import Session
s=Session(sys.argv[1],dict(AMIGA_SETUP='a1200-040',DETERMINISTIC='0',EXTRA_ARGS='--video_driver=null '+os.environ.get('CACHE_EXTRA',''),WHD_ARGS='CUSTOM1=1 '+os.environ.get('CACHE_ARGS','')))
try:
 s.fields(2000)
 print(s.shot('intro.png'),flush=True)
finally:s.quit()

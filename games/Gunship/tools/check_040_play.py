import os,sys
from session_b import Session
s=Session(sys.argv[1],dict(AMIGA_SETUP='a1200-040',DETERMINISTIC='0',EXTRA_ARGS='--video_driver=null '+os.environ.get('CACHE_EXTRA',''),WHD_ARGS='CUSTOM1=1 '+os.environ.get('CACHE_ARGS','')))
try:
 from route import run
 from flight_profile import ROUTE
 run(s,ROUTE[:ROUTE.index('t:n1')])
 print(s.shot('cockpit.png'),flush=True)
 run(s,ROUTE[ROUTE.index('t:n1'):])
 from flight_profile import window
 window(s,lambda fields:s.fields(fields))
 print(s.shot('flight.png'),flush=True)
finally:s.quit()

#!/usr/bin/env python3
"""Generate the fine mouse quarter-wave table from mathematics, never game data."""
import math
from pathlib import Path
import sys
values = [round((1<<30)*math.sin(math.radians(i/64))) for i in range(90*64+1)]
Path(sys.argv[1]).write_text('; Generated mathematical Q30 sine, 0..90 degrees at 1/64 degree.\n'+
    ''.join(' dc.l '+','.join(map(str,values[i:i+16]))+'\n' for i in range(0,len(values),16)))

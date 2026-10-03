#!/usr/bin/env python3
"""Exit 0 if the screenshot shows the driving view (sky blue above the dashboard)."""
import sys
from PIL import Image
im = Image.open(sys.argv[1]).convert('RGB')
w, h = im.size
pts = [(int(w * x), int(h * 0.12)) for x in (0.2, 0.4, 0.6)]
sky = sum(1 for p in pts if (lambda r, g, b: b > 200 and 120 < g < 230 and r < 120)(*im.getpixel(p)))
sys.exit(0 if sky >= 2 else 1)

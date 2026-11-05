#!/usr/bin/env python3
"""Exit 0 if the screenshot shows the attract demo (yellow "CLICK TO DRIVE" above the 3D view)."""
import sys
from PIL import Image
im = Image.open(sys.argv[1]).convert('RGB')
w, h = im.size
yellow = sum(1 for y in range(int(h * 0.05), int(h * 0.09)) for x in range(int(w * 0.37), int(w * 0.67), 2)
             if (lambda r, g, b: r > 200 and g > 150 and b < 80)(*im.getpixel((x, y))))
sys.exit(0 if yellow > 100 else 1)

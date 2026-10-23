#!/usr/bin/env python3
"""Validate the follow-name predicate against retained tow/follow screenshots.
Usage: test_profile_anchor.py CAPTURE [CAPTURE...]
Fixtures are user-derived evidence under tmp/, never committed.
"""
from pathlib import Path
import sys
from PIL import Image
import f1gp
from race_profile import viewing_driver

for directory in sys.argv[1:]:
    root = Path(directory)
    tow = Image.open(root/'anchor-tow.png').convert('RGB')
    follow = Image.open(root/'anchor-follow.png').convert('RGB')
    first = viewing_driver(f1gp, tow)
    second = viewing_driver(f1gp, follow)
    assert first and second and first != second, directory
    assert viewing_driver(f1gp, tow.copy()) == first
    # A moving scene beneath the same banner must not create a camera transition.
    changed = tow.copy()
    changed.paste((255, 0, 255), (0, 102, changed.width, changed.height))
    assert viewing_driver(f1gp, changed) == first
    # A label without a name is not enough, nor is a name without the Viewing label.
    changed = tow.copy(); changed.paste((0, 0, 0), (300, 70, 640, 94))
    assert viewing_driver(f1gp, changed) is None
    changed = tow.copy(); changed.paste((0, 0, 0), (180, 70, 290, 94))
    assert viewing_driver(f1gp, changed) is None
    print(directory, 'PASS: distinct names; repeated banner, scene motion and incomplete banners rejected')
if len(sys.argv) < 2:
    raise SystemExit(__doc__)

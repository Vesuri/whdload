-- The game's own control set-up, which it runs at boot when the EEPROM
-- checksum is bad: pot rest values, steering limits (MAME range 0x010..0xff0),
-- shifter first/fourth, seat (fixed in MAME), and the force brake: release
-- level, then a press of amount 0xc00. The game only grades braking when the
-- range is below the learned release level (about 0xffb); a full press
-- (range 4095) makes every press full braking.
return { events = {
  {t=10, key=1}, {t=10.3, key=0},
  {t=11, wheel=0x010}, {t=12, key=1}, {t=12.3, key=0},
  {t=13, wheel=0xff0}, {t=14, key=1}, {t=14.3, key=0}, {t=15, wheel=0x800},
  {t=16, shiftx=0, shifty=0}, {t=17, key=1}, {t=17.3, key=0},
  {t=19, shiftx=255, shifty=255}, {t=20, key=1}, {t=20.3, key=0}, {t=22, shiftx=0x80, shifty=0x80},
  {t=23, key=1}, {t=23.3, key=0}, {t=25, key=1}, {t=25.3, key=0},
  {t=31, brake=0xc00}, {t=32, brake=0}, {t=33, snap=true}, {t=40, exit=true} } }

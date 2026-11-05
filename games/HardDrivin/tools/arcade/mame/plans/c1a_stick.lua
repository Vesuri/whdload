-- C1a stick: launch in first on the heading, hold each gear past the rev
-- limit, then coast in neutral.
local C = dofile(os.getenv("HD_TOOLS") .. "/plans/c.lua")
local g = C.S.gears
return C.plan({ {t=25, clutch=255, head=C.head}, {t=25.3, shiftx=g[1][1], shifty=g[1][2]},
  {t=25.6, gas=255}, {t=25.8, ramp={"clutch", 0, 0.6}},
  C.shift(34, 2), C.shift(46, 3), C.shift(61, 4), C.shift(96, 0, 0), {t=126, exit=true} },
  { stick = true, no_approach = true })

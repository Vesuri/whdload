-- C1a automatic: stop, full throttle for 50 s on the heading, then coast 40 s.
local C = dofile(os.getenv("HD_TOOLS") .. "/plans/c.lua")
return C.plan({ {t=33, cruise=false, brake=0xfff}, {t=37, brake=0, gas=255},
  {t=87, gas=0}, {t=127, exit=true} })

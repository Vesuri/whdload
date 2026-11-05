-- A4: a short drive (throttle, a steer, a brake) for the repeatability check.
local S = dofile(os.getenv("HD_TOOLS") .. "/plans/start.lua")
return S.plan({ {t=24.5, log=true}, {t=25, gas=255}, {t=31, wheel=0xa00}, {t=33, wheel=0x800},
  {t=35, gas=0, brake=0x800}, {t=38, brake=0}, {t=38.5, snap=true}, {t=39, exit=true} })

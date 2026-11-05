-- B2: straight acceleration, a right then a left steer, coast, brake, stop.
local S = dofile(os.getenv("HD_TOOLS") .. "/plans/start.lua")
return S.plan({ {t=24.5, log=true}, {t=25, gas=255},
  {t=33, wheel=0x900}, {t=36, wheel=0x800}, {t=37, wheel=0x700}, {t=39, wheel=0x800},
  {t=40, gas=0}, {t=41, brake=0x800}, {t=46, brake=0}, {t=47, exit=true} })

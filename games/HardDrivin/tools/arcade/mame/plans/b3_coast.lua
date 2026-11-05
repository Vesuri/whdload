-- B3 experiment, see ARCADE_ROMS.md (Time step and units).
local S = dofile(os.getenv("HD_TOOLS") .. "/plans/start.lua")
local e = { {t=24.5, log=true}, {t=25, gas=255}, {t=27.2, gas=0}, {t=29.5, snap=true}, {t=30.5, snap=true}, {t=31.5, snap=true},
  {t=32.5, gas=255}, {t=35, gas=0}, {t=37, snap=true}, {t=38, snap=true}, {t=39, snap=true}, {t=39.2, exit=true} }
return S.plan(e)

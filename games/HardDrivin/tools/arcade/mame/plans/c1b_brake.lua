-- C1b: brake to a stop from 60 and from 100 MPH, pedal amount HD_BRAKE
-- (default 0xfff, full).
local C = dofile(os.getenv("HD_TOOLS") .. "/plans/c.lua")
local b = tonumber(os.getenv("HD_BRAKE") or "4095")
return C.plan({ {t=33, cruise=60}, {t=45, cruise=false, brake=b}, {t=52, brake=0, cruise=100},
  {t=82, cruise=false, brake=b}, {t=92, brake=0}, {t=93, exit=true} })

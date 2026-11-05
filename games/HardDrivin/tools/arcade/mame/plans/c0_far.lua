-- C0 long terrain probe with plan.road: turn to HD_HEAD at 25 MPH, then hold
-- it at 90 MPH until script time 95.
local S = dofile(os.getenv("HD_TOOLS") .. "/plans/start.lua")
local h = tonumber(os.getenv("HD_HEAD"))
local p = S.plan({ {t=24.5, log=true}, {t=25, cruise=25}, {t=26, head=h},
  {t=34, cruise=90}, {t=95, exit=true} })
p.road = true
return p

-- C0 terrain probe with plan.road: turn to heading HD_HEAD at 25 MPH, then
-- hold it at 60 MPH for 25 s. Logs positions, heights and surface types.
local S = dofile(os.getenv("HD_TOOLS") .. "/plans/start.lua")
local h = tonumber(os.getenv("HD_HEAD"))
local p = S.plan({ {t=24.5, log=true}, {t=25, cruise=25}, {t=26, head=h},
  {t=34, cruise=60}, {t=59, exit=true} })
p.road = true
return p

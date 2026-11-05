-- C1d: step steer at HD_MPH. Wheel left by HD_SMALL (raw), centre, then left
-- by HD_LARGE, centre; 3 s each.
local C = dofile(os.getenv("HD_TOOLS") .. "/plans/c.lua")
local v = tonumber(os.getenv("HD_MPH"))
local small, large = tonumber(os.getenv("HD_SMALL")), tonumber(os.getenv("HD_LARGE"))
local t = 33 + 6 + v / 6
return C.plan({ {t=33, cruise=v}, {t=t, head=false}, {t=t+1, wheel=0x800-small}, {t=t+4, wheel=0x800},
  {t=t+7, wheel=0x800-large}, {t=t+10, wheel=0x800}, {t=t+13, exit=true} })

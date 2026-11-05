-- C1c: steady-state steering at HD_MPH. Hold the speed, then ramp the wheel
-- left from centre to HD_LOCK (fraction of full lock) over 16 s.
local C = dofile(os.getenv("HD_TOOLS") .. "/plans/c.lua")
local v = tonumber(os.getenv("HD_MPH"))
local lock = tonumber(os.getenv("HD_LOCK"))
local t = 33 + 6 + v / 6    -- time to reach and settle at the speed
return C.plan({ {t=33, cruise=v}, {t=t, head=false}, {t=t+0.1, ramp={"wheel", math.floor(0x800 - 0x7f0 * lock), 16}},
  {t=t+16.5, wheel=0x800}, {t=t+18, exit=true} })

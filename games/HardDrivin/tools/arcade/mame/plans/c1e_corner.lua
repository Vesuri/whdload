-- C1e: steady left corner at HD_MPH with the wheel HD_WHEEL (raw) left of
-- centre, then HD_ACTION for 3 s: lift (gas off), brake (amount 1500, about
-- half) or power (full gas).
local C = dofile(os.getenv("HD_TOOLS") .. "/plans/c.lua")
local v, w, a = tonumber(os.getenv("HD_MPH")), tonumber(os.getenv("HD_WHEEL")), os.getenv("HD_ACTION")
local t = 33 + 6 + v / 6
local act = ({ lift = {cruise=false, gas=0}, brake = {cruise=false, gas=0, brake=1500},
  power = {cruise=false, gas=255} })[a]
act.t = t + 4.5
return C.plan({ {t=33, cruise=v}, {t=t, head=false}, {t=t+0.1, wheel=0x800-w}, act,
  {t=t+7.5, wheel=0x800, brake=0, gas=0}, {t=t+9, exit=true} })

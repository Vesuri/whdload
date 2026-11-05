-- C1h (H3, the user's "rear end getting loose while coasting and steering"):
-- cruise at HD_MPH, then at once shut the gas (no brake) and turn the wheel
-- left by HD_WHEEL (raw), held for 7 s.
local C = dofile(os.getenv("HD_TOOLS") .. "/plans/c.lua")
local v, w = tonumber(os.getenv("HD_MPH")), tonumber(os.getenv("HD_WHEEL"))
local t = 33 + 6 + v / 6
return C.plan({ {t=33, cruise=v}, {t=t, head=false}, {t=t+0.5, wheel=0x800-w, cruise=false, gas=0}, {t=t+7.5, exit=true} })

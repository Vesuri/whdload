-- C1f: try to start a slide at HD_MPH. Wheel left by HD_WHEEL (raw) for
-- HD_HOLD s, with full brake too if HD_BRAKE=1; then HD_ACTION: counter
-- (wheel right by half as much for 1 s, then centre), hold (keep the wheel)
-- or release (centre).
local C = dofile(os.getenv("HD_TOOLS") .. "/plans/c.lua")
local v, w = tonumber(os.getenv("HD_MPH")), tonumber(os.getenv("HD_WHEEL"))
local hold, a = tonumber(os.getenv("HD_HOLD") or "1"), os.getenv("HD_ACTION")
local brake = os.getenv("HD_BRAKE") == "1"
local t = 33 + 6 + v / 6
local t1 = t + 0.5 + hold
local e = { {t=33, cruise=v}, {t=t, head=false}, {t=t+0.5, wheel=0x800-w}, {t=t+7, exit=true} }
if brake then e[#e+1] = {t=t+0.5, cruise=false, gas=0, brake=0xfff}; e[#e+1] = {t=t1, brake=0} end
if a == "counter" then e[#e+1] = {t=t1, wheel=0x800+math.floor(w/2)}; e[#e+1] = {t=t1+1, wheel=0x800}
elseif a == "release" then e[#e+1] = {t=t1, wheel=0x800} end
return C.plan(e)

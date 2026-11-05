-- Traffic at the start: the car idles on the start line; snapshots every 0.5 s.
local S = dofile(os.getenv("HD_TOOLS") .. "/plans/start.lua")
local e = {}
for i = 0, 28 do e[#e+1] = {t=21 + i * 0.5, snap=true} end
e[#e+1] = {t=36, exit=true}
return S.plan(e)

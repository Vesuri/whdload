-- B3 experiment, see ARCADE_ROMS.md (Time step and units).
local S = dofile(os.getenv("HD_TOOLS") .. "/plans/start.lua")
local e = { {t=24.5, log=true, snap=true}, {t=25, gas=255} }
for _, s in ipairs({25.8, 26.4, 27, 27.6, 28.3, 29, 29.8, 30.6, 31.5, 32.4, 33.4, 34.6, 36}) do e[#e+1] = {t=s, snap=true} end
e[#e+1] = {t=36.2, exit=true}
return S.plan(e)

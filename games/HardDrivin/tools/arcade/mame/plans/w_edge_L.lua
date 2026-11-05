-- Road width probe: from the start line at 15 MPH, steer L until off the road.
local S = dofile(os.getenv("HD_TOOLS") .. "/plans/start.lua")
return S.plan({ {t=24.5, log=true}, {t=25, cruise=15}, {t=28, wheel=0x600}, {t=36, exit=true} })

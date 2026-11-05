-- C1g: low-speed steering. Slow down, then hold the wheel left at 25%, 50%,
-- 75% and full lock at 5 MPH, full left lock at 10 and 15 MPH, and full right
-- lock at 5 MPH.
local C = dofile(os.getenv("HD_TOOLS") .. "/plans/c.lua")
local function left(f) return math.floor(0x800 - 0x7f0 * f) end
return C.plan({ {t=33, cruise=false, brake=0x800}, {t=35.5, brake=0, cruise=5}, {t=37, head=false},
  {t=37.1, wheel=left(0.25)}, {t=47, wheel=left(0.5)}, {t=57, wheel=left(0.75)}, {t=67, wheel=0x010},
  {t=82, cruise=10}, {t=94, cruise=15}, {t=106, cruise=5, wheel=0xff0}, {t=121, exit=true} })

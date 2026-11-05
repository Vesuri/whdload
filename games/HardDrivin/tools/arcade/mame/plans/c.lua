-- Step C manoeuvres. After the boot (start.lua) the car turns left onto
-- heading C.head at 25 MPH, into the open flat ground behind and to the left
-- of the start line (see ARCADE_ROMS.md, "Feel measurements"), and holds that
-- heading until a plan turns the heading control off. plan.road is on, so the
-- grass there is road. Plan times are script times; HD_SHIFT (seconds) delays
-- everything after the boot, for the repeat runs.
local S = dofile(os.getenv("HD_TOOLS") .. "/plans/start.lua")
local C = { head = -145, S = S }

-- events for a stick-shift change to GEAR at time T, gas G afterwards
function C.shift(t, gear, g)
  local p = S.gears[gear]
  return { {t=t, clutch=255, gas=0}, {t=t+0.15, shiftx=p[1], shifty=p[2]}, {t=t+0.35, clutch=0, gas=g or 255} }
end

function C.plan(after, opts)
  opts = opts or {}
  local sh = tonumber(os.getenv("HD_SHIFT") or "0")
  local e = { {t=24.5, log=true} }
  if not opts.no_approach then e[#e+1] = {t=25, cruise=25, head=C.head} end
  local function add(v)
    if v.t then
      local c = {}
      for k, x in pairs(v) do c[k] = x end
      c.t = v.t + sh
      e[#e+1] = c
    else
      for _, w in ipairs(v) do add(w) end
    end
  end
  add(after)
  local p = S.plan(e, opts.stick)
  p.road = true
  return p
end
return C

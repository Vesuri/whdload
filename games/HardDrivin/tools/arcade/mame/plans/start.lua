-- Boot to a race. Coin; key on the transmission screen (automatic); full gas
-- and clutch once on the start line so the pedal auto-calibration learns the
-- whole range; hold the key until the engine runs (the race starts with it).
-- The car is idling on the start line, brakes released, at script time 24.5.
-- M.plan(after, true) picks the stick shift instead: the wheel is held right
-- through the key press, and the engine starts in neutral with the clutch in.
-- Shifter positions (shiftx, shifty): 1 = (0,255), 2 = (0,0), 3 = (255,255),
-- 4 = (255,0), N = (128,128).
local M = { at = 24.5 }
M.boot = { {t=16, coin=1}, {t=16.3, coin=0}, {t=19, key=1}, {t=19.3, key=0},
  {t=20, gas=255, clutch=255}, {t=20.5, gas=0, clutch=0},
  {t=21, key=1}, {t=23.5, key=0} }
M.stick_boot = { {t=16, coin=1}, {t=16.3, coin=0}, {t=17, wheel=0xc00}, {t=19, key=1}, {t=19.3, key=0},
  {t=19.5, wheel=0x800}, {t=20, gas=255, clutch=255}, {t=20.5, gas=0},
  {t=20.6, shiftx=128, shifty=128}, {t=21, key=1}, {t=23.5, key=0} }
M.gears = { [0] = {128, 128}, {0, 255}, {0, 0}, {255, 255}, {255, 0} }
function M.plan(after, stick)
  local e = {}
  for _, v in ipairs(stick and M.stick_boot or M.boot) do e[#e+1] = v end
  for _, v in ipairs(after) do e[#e+1] = v end
  table.sort(e, function(a, b) return a.t < b.t end)
  return { events = e }
end
return M

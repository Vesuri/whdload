-- B3 experiment, see ARCADE_ROMS.md (Time step and units).
-- B3 experiment: count MSP tick-input reads (one per MSP frame, in $723900),
-- host writes of the tick input, and 68010 result reads, per emulated second.
local S = dofile(os.getenv("HD_TOOLS") .. "/plans/start.lua")
local m = manager.machine
local msp = m.devices[":mainpcb:msp"].spaces["program"]
local main = m.devices[":mainpcb:maincpu"].spaces["program"]
local n = { mspread = 0, hostwrite = 0, result = 0 }
local out = io.open(os.getenv("HD_RUN") .. "/count.txt", "w")
b3_r = msp:install_read_tap(0x7940a0, 0x7940af, "b3r", function(o, d, mk) n.mspread = n.mspread + 1 end)
b3_w = msp:install_write_tap(0x7940a0, 0x7940af, "b3w", function(o, d, mk) n.hostwrite = n.hostwrite + 1 end)
b3_x = main:install_write_tap(0xff8eca, 0xff8ecb, "b3x", function(o, d, mk) n.result = n.result + 1 end)
local last = 0
b3_f = emu.add_machine_frame_notifier(function()
  local t = math.floor(m.time:as_double())
  if t ~= last then
    out:write(string.format("%d mspread=%d hostwrite=%d result=%d\n", t, n.mspread, n.hostwrite, n.result)); out:flush()
    n.mspread, n.hostwrite, n.result = 0, 0, 0; last = t
  end
end)
return S.plan({ {t=25, gas=255}, {t=31, exit=true} })

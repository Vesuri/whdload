-- Traffic at the start: dump the 68010's RAM $FF0000..$FFFFFF at times around
-- the green light, the car idling on the start line (logging its results).
local S = dofile(os.getenv("HD_TOOLS") .. "/plans/start.lua")
local m = manager.machine
local main = m.devices[":mainpcb:maincpu"].spaces["program"]
local n = 0
local function dump()
  local f = io.open(string.format("%s/ram%02d.bin", os.getenv("HD_RUN"), n), "wb")
  n = n + 1
  local t = {}
  for a = 0xff0000, 0xfffffe, 2 do
    local w = main:read_u16(a)
    t[#t + 1] = string.char(w >> 8, w & 255)
  end
  f:write(table.concat(t)); f:close()
end
local e = { {t=21, log=true} }
for i = 0, 30 do e[#e + 1] = {t=21.5 + i * 0.25, call=dump} end
e[#e + 1] = {t=30, exit=true}
return S.plan(e)

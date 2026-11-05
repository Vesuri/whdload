-- Traffic over a whole race with the car idling on the start line: the 7 traffic
-- records ($FF87E6, 0x7C each) every 0.25 s into HD_RUN/traffic.bin, one RAM
-- dump at 40 s, snapshots every second from 22 to 80 s.
local S = dofile(os.getenv("HD_TOOLS") .. "/plans/start.lua")
local m = manager.machine
local main = m.devices[":mainpcb:maincpu"].spaces["program"]
local tf = io.open(os.getenv("HD_RUN") .. "/traffic.bin", "wb")
local function rec()
  local t = {}
  for a = 0xff87e6, 0xff87e6 + 7 * 0x7c - 2, 2 do
    local w = main:read_u16(a)
    t[#t + 1] = string.char(w >> 8, w & 255)
  end
  tf:write(table.concat(t)); tf:flush()
end
local function dump()
  local f = io.open(os.getenv("HD_RUN") .. "/ram40.bin", "wb")
  local t = {}
  for a = 0xff0000, 0xfffffe, 2 do
    local w = main:read_u16(a)
    t[#t + 1] = string.char(w >> 8, w & 255)
  end
  f:write(table.concat(t)); f:close()
end
local e = { {t=21, log=false} }
for i = 0, 388 do e[#e + 1] = {t=21 + i * 0.25, call=rec} end
for i = 22, 80 do e[#e + 1] = {t=i + 0.1, snap=true} end
e[#e + 1] = {t=40.05, call=dump}
e[#e + 1] = {t=118.5, exit=true}
return S.plan(e)

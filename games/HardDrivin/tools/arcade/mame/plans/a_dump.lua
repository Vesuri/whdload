-- Attract mode's first demo through the loop (about 70-82 s from power-on):
-- dump the 68010's RAM $FF0000..$FFFFFF every 0.1 s and snap every 0.5 s.
local m = manager.machine
local main = m.devices[":mainpcb:maincpu"].spaces["program"]
local n = 0
local function dump()
  local f = io.open(string.format("%s/ram%03d.bin", os.getenv("HD_RUN"), n), "wb")
  n = n + 1
  local t = {}
  for a = 0xff0000, 0xfffffe, 2 do
    local w = main:read_u16(a)
    t[#t + 1] = string.char(w >> 8, w & 255)
  end
  f:write(table.concat(t)); f:close()
end
local e = {}
for i = 0, 139 do e[#e + 1] = {t=68 + i * 0.1, call=dump, snap=(i % 5 == 0)} end
e[#e + 1] = {t=82.1, exit=true}
return { events = e }

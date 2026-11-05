-- Race-time operator settings with the pristine EEPROM, on the start line:
-- HD_RUN/settings.txt gets the time-setting nibbles $FF9764..$FF9767, the
-- difficulty term $FF9760, best lap $FF4556, championship qualification
-- $FF455A, initial time left $FF9822 and the EEPROM-loaded copy at $FF4430..
local S = dofile(os.getenv("HD_TOOLS") .. "/plans/start.lua")
local m = manager.machine
local main = m.devices[":mainpcb:maincpu"].spaces["program"]

local function dump()
  local out = io.open(os.getenv("HD_RUN") .. "/settings.txt", "w")
  local function w(name, addr, n)
    local t = {}
    for i = 0, n - 1 do t[#t + 1] = string.format("%02x", main:read_u8(addr + i)) end
    out:write(string.format("%s %06x %s\n", name, addr, table.concat(t)))
  end
  w("times", 0xff9764, 4)
  w("difficulty", 0xff9760, 4)
  w("best_lap", 0xff4556, 4)
  w("champ_qual", 0xff455a, 4)
  w("left", 0xff9822, 4)
  w("eeprom_copy", 0xff4400, 0x80)
  out:close()
end

return S.plan({ {t=24.5, call=dump}, {t=25, exit=true} })

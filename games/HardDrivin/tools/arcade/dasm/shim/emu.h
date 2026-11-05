#pragma once
// Minimal stand-in for MAME's emu.h so single CPU disassemblers build alone.
#include <cstdint>
#include <ostream>
#include <string>
#include "osdcomm.h"
#include "disasmintf.h"
#include "strformat.h"
using u8=uint8_t; using u16=uint16_t; using u32=uint32_t; using u64=uint64_t;
using s8=int8_t; using s16=int16_t; using s32=int32_t; using s64=int64_t;
using offs_t=uint32_t;
#define BIT(x,n) (((x)>>(n))&1)

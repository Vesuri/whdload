# Source from the repository root before using shared Amiga tools.
if [ ! -f "${AMIGA_ENV:-$HOME/.local/share/amiga/env.sh}" ]; then
    echo "Missing shared Amiga environment; install it with AmigaXDev." >&2
    return 1
fi
. "${AMIGA_ENV:-$HOME/.local/share/amiga/env.sh}"

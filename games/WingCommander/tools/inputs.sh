#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
action=${1:-verify}
case "$action" in fetch|verify|prepare) ;; *) echo "Usage: $0 fetch|verify|prepare" >&2; exit 2 ;; esac
mkdir -p tmp/downloads
while IFS="$(printf '\t')" read -r variant filename expected url; do
    case "$variant" in ''|\#*) continue ;; esac
    archive="tmp/downloads/$filename"
    if [ ! -f "$archive" ] && [ "$action" = fetch ]; then
        # Keep interrupted downloads separate; never overwrite an existing input.
        part=$(mktemp "tmp/downloads/.download.XXXXXX")
        curl --fail --location --retry 2 --output "$part" "$url"
        actual=$(shasum -a 256 "$part"); actual=${actual%% *}
        if [ "$actual" != "$expected" ]; then
            echo "Checksum mismatch: $filename; retained $part" >&2; exit 1
        fi
        mv -n "$part" "$archive"
    fi
    if [ ! -f "$archive" ]; then
        echo "Missing $archive; run make fetch" >&2; exit 1
    fi
    actual=$(shasum -a 256 "$archive"); actual=${actual%% *}
    if [ "$actual" != "$expected" ]; then
        echo "Checksum mismatch: $archive; original retained" >&2; exit 1
    fi
    echo "$variant: checksum OK"
    if [ "$action" = prepare ]; then
        destination="tmp/originals/$variant"
        if [ -e "$destination" ]; then
            echo "$destination already exists; left untouched"
        else
            mkdir -p tmp/originals
            staging=$(mktemp -d "tmp/originals/.extract.XXXXXX")
            (cd "$staging" && lha xq "../../downloads/$filename")
            mv -n "$staging" "$destination"
            echo "Prepared $destination"
        fi
    fi
done < manifest/inputs.tsv

#!/usr/bin/env bash
# Yetkin360 local launcher for macOS (double-click in Finder) and Linux (./baslat.command).
# All logic lives in scripts/baslat.sh. Keys: [B] browser  [H] summary  [Q] / Ctrl+C stop.
# Options: ./baslat.command --no-browser
# This file must keep LF line endings and the executable bit (see .gitattributes).
cd "$(dirname "$0")" || exit 1
bash scripts/baslat.sh "$@"
status=$?
if [ $status -ne 0 ]; then
    echo
    read -r -p "  Kapatmak için Enter'a basın..." _
fi
exit $status

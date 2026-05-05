#!/usr/bin/env bash
set -e
python "$(dirname "$0")/download_fonts.py" "$@"

#!/usr/bin/env bash
# Fetch the title fonts from npm (GitHub release downloads are blocked in the cloud sandbox).
# Usage: bash setup_fonts.sh FONTS_DIR
set -e
D=${1:?fonts dir}; mkdir -p "$D"; cd "$D"
for pkg in lxgw-wenkai-webfont @fontsource/playfair-display; do
  name=$(echo "$pkg" | sed 's#^@##; s#/#-#')
  if ! ls -d ${name}-* >/dev/null 2>&1; then
    f=$(npm pack "$pkg" --silent | tail -1); tar xzf "$f"; mv package "${f%.tgz}"; rm "$f"
  fi
done
ls -d */

#!/usr/bin/env bash
# ArcVox Private Studio — optional brand-font self-hosting.
#
# The app ships with system-font fallbacks and makes ZERO external font
# requests by default (a privacy studio must not leak visitor IPs to a
# font CDN on every page load).
#
# If you want the exact brand faces (Clash Display / Manrope / JetBrains
# Mono), run this on a machine whose network allows the font hosts, then
# commit the downloaded files. They will be served from your own origin.
set -euo pipefail

FONT_DIR="$(cd "$(dirname "$0")/.." && pwd)/frontend/src/fonts"
mkdir -p "$FONT_DIR"

cat <<'EOF'
To self-host the brand fonts:

1. Download the woff2 files (on a network that allows the hosts):
     Clash Display : https://www.fontshare.com/fonts/clash-display
     Manrope       : https://fonts.google.com/specimen/Manrope
     JetBrains Mono: https://fonts.google.com/specimen/JetBrains+Mono

2. Place the .woff2 files in: frontend/src/fonts/

3. Add @font-face blocks to the top of frontend/src/index.css, e.g.:

     @font-face {
       font-family: 'Clash Display';
       src: url('./fonts/ClashDisplay-Semibold.woff2') format('woff2');
       font-weight: 600; font-display: swap;
     }

4. Rebuild the frontend. The fonts now load from your own server only.
EOF

echo "Font directory ready at: $FONT_DIR"

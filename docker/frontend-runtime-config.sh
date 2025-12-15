#!/bin/sh
set -eu

OUTPUT="/usr/share/nginx/html/runtime-config.js"
API_BASE_URL=${PUBLIC_API_BASE_URL:-}

# Escape any double quotes so the generated JS stays valid
ESCAPED_API_BASE_URL=$(printf '%s' "$API_BASE_URL" | sed 's/"/\\"/g')

cat > "$OUTPUT" <<EOF
window.__ENV__ = {
  PUBLIC_API_BASE_URL: "$ESCAPED_API_BASE_URL"
};
EOF

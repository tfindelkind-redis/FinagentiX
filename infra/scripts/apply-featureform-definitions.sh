#!/bin/bash
set -e

# Legacy entrypoint retained for compatibility.
# This now delegates to the VM-based workflow defined in connect-and-apply.sh.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================="
echo "Apply Featureform Definitions"
echo "========================================="
echo ""
echo "Info: The debug pod pathway has been retired. Using the debug VM instead."
echo ""

"$SCRIPT_DIR/connect-and-apply.sh" "$@"

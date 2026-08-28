#!/usr/bin/env bash
# Validate every Mermaid diagram (*.mmd) under a path by compiling it with mermaid-cli.
# A diagram that fails to parse/render exits non-zero, so CI fails on a broken diagram.
#
# Usage:
#   scripts/diagrams/validate.sh [path]     # default path: docs/specs
#
# mmdc resolution (first match wins):
#   $MMDC env  ->  mmdc on PATH  ->  npx -y @mermaid-js/mermaid-cli
# Puppeteer:
#   uses scripts/diagrams/puppeteer-config.json (--no-sandbox) so it runs headless in CI.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SEARCH_PATH="${1:-$ROOT/docs/specs}"
PPTR_CONFIG="${PUPPETEER_CONFIG:-$ROOT/scripts/diagrams/puppeteer-config.json}"

if [[ -n "${MMDC:-}" ]]; then
  MMDC_CMD=("$MMDC")
elif command -v mmdc >/dev/null 2>&1; then
  MMDC_CMD=(mmdc)
else
  MMDC_CMD=(npx -y @mermaid-js/mermaid-cli)
fi

tmp_out="$(mktemp -d)"
trap 'rm -rf "$tmp_out"' EXIT

files=()
while IFS= read -r line; do files+=("$line"); done < <(find "$SEARCH_PATH" -type f -name '*.mmd' | sort)
if (( ${#files[@]} == 0 )); then
  echo "diagrams: no .mmd files found under $SEARCH_PATH"
  exit 0
fi

rc=0
for f in "${files[@]}"; do
  if "${MMDC_CMD[@]}" -i "$f" -o "$tmp_out/out.svg" -p "$PPTR_CONFIG" -q >"$tmp_out/log" 2>&1; then
    echo "  ✓ ${f#"$ROOT/"}"
  else
    echo "  ✗ ${f#"$ROOT/"}"
    sed 's/^/      /' "$tmp_out/log"
    rc=1
  fi
done

if (( rc != 0 )); then
  echo "diagrams: validation FAILED" >&2
fi
exit $rc

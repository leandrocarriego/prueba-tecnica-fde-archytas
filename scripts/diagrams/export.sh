#!/usr/bin/env bash
# Export Mermaid diagrams (*.mmd) to shareable images and regenerate a single
# rendered Markdown per diagrams/ folder (for GitHub viewing and client sharing).
#
# Usage:
#   scripts/diagrams/export.sh [path] [formats]
#     path     a feature dir, a diagrams/ dir, or a parent to scan (default: docs/specs)
#     formats  comma-separated subset of: pdf,png,svg            (default: pdf,png,svg)
#
# For every diagrams/ folder found it produces:
#   dist/diagramas/<feature>/<name>.<fmt>   client-ready images (white background)
#   diagrams/README.md              all diagrams inlined as ```mermaid``` (renders on GitHub)
#
# mmdc resolution: $MMDC -> mmdc on PATH -> npx -y @mermaid-js/mermaid-cli
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET="${1:-$ROOT/docs/specs}"
FORMATS="${2:-pdf,png,svg}"
PPTR_CONFIG="${PUPPETEER_CONFIG:-$ROOT/scripts/diagrams/puppeteer-config.json}"

if [[ -n "${MMDC:-}" ]]; then
  MMDC_CMD=("$MMDC")
elif command -v mmdc >/dev/null 2>&1; then
  MMDC_CMD=(mmdc)
else
  MMDC_CMD=(npx -y @mermaid-js/mermaid-cli)
fi

# Collect diagrams/ folders: TARGET may BE one, contain .mmd, or be a parent to scan.
declare -a dirs=()
if [[ -d "$TARGET" && "$(basename "$TARGET")" == "diagrams" ]]; then
  dirs=("$TARGET")
elif [[ -d "$TARGET/diagrams" ]]; then
  dirs=("$TARGET/diagrams")
else
  while IFS= read -r line; do dirs+=("$line"); done < <(find "$TARGET" -type d -name diagrams | sort)
fi

if (( ${#dirs[@]} == 0 )); then
  echo "diagrams: no diagrams/ folder found under $TARGET"
  exit 0
fi

title_of() { sed -n 's/^title:[[:space:]]*//p' "$1" | head -n1; }

for d in "${dirs[@]}"; do
  files=()
  while IFS= read -r line; do files+=("$line"); done < <(find "$d" -maxdepth 1 -type f -name '*.mmd' | sort)
  (( ${#files[@]} == 0 )) && continue
  # Generated binaries live under dist/, never inside docs/: one root for
  # everything regenerable, so `docs/` only holds sources and the rendered
  # README.md that GitHub shows. `feature` is the folder that owns diagrams/.
  feature="$(basename "$(dirname "$d")")"
  out="$ROOT/dist/diagramas/$feature"
  mkdir -p "$out"
  echo "diagrams: ${d#"$ROOT/"} (${#files[@]} diagrams)"

  # 1) images
  IFS=',' read -ra fmts <<< "$FORMATS"
  for f in "${files[@]}"; do
    base="$(basename "${f%.mmd}")"
    for fmt in "${fmts[@]}"; do
      "${MMDC_CMD[@]}" -i "$f" -o "$out/$base.$fmt" -p "$PPTR_CONFIG" -b white -q >/dev/null 2>&1
      echo "  ✓ ${out#"$ROOT/"}/$base.$fmt"
    done
  done

  # 2) combined rendered markdown (canonical source stays the .mmd files).
  #    Named README.md so GitHub renders it when the diagrams/ folder is opened.
  md="$d/README.md"
  {
    echo "<!-- GENERADO por scripts/diagrams/export.sh — NO editar a mano."
    echo "     Fuente: los .mmd de esta carpeta. Regenerar: scripts/diagrams/export.sh -->"
    echo
    echo "# Diagramas"
    echo
    echo "> Vista renderizada de los diagramas de esta feature. Fuente: los \`.mmd\` de esta"
    echo "> carpeta. Convención: \`docs/specs/DIAGRAMS.md\`. Las imágenes para el cliente se"
    echo "> generan en \`dist/diagramas/\` con \`make diagrams\`."
    echo
    for f in "${files[@]}"; do
      t="$(title_of "$f")"; [[ -z "$t" ]] && t="$(basename "${f%.mmd}")"
      echo "## $t"
      echo
      echo '```mermaid'
      cat "$f"
      echo '```'
      echo
    done
  } > "$md"
  echo "  ✓ ${md#"$ROOT/"}"
done

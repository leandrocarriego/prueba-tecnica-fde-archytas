#!/bin/bash
# Frontend dependency security gate.
#
# Blocks the commit when `npm audit` reports vulnerabilities at or above a
# threshold. Wired as a local pre-commit hook that fires when
# frontend/package.json or package-lock.json change (see .pre-commit-config.yaml).
#
# Policy: fail CLOSED on vulnerabilities (block the commit), but fail OPEN when
# the audit itself cannot run (no network, registry down, unreadable report) —
# an infrastructure problem must not hold the team hostage.
#
# Threshold: NPM_AUDIT_LEVEL = info|low|moderate|high|critical
# (default: low — any vulnerability that matters).
set -euo pipefail

AUDIT_LEVEL="${NPM_AUDIT_LEVEL:-low}"

cd "$(dirname "$0")/../frontend"

if [ ! -f package-lock.json ]; then
  echo "audit-gate: no hay frontend/package-lock.json; se omite."
  exit 0
fi

# `npm audit --json` is not trusted for its exit code here; we parse the report.
report="$(npm audit --json 2>/dev/null || true)"

if [ -z "$report" ]; then
  echo "⚠ audit-gate: no se pudo ejecutar 'npm audit' (¿sin red?). Se permite el commit."
  exit 0
fi

# Count vulnerabilities at or above the threshold with node (always
# available in the frontend). Prints "TOTAL  detail" or "ERR ...".
result="$(printf '%s' "$report" | node -e '
let s=""; process.stdin.on("data",d=>s+=d).on("end",()=>{
  try{
    const j=JSON.parse(s);
    if(j.error){ console.log("ERR red/registry"); return; }
    const v=(j.metadata&&j.metadata.vulnerabilities)||{};
    const order=["info","low","moderate","high","critical"];
    const idx=Math.max(0, order.indexOf(process.argv[1]));
    let total=0; const parts=[];
    order.forEach((k,i)=>{ const c=v[k]||0; if(i>=idx) total+=c; if(c) parts.push(c+" "+k); });
    console.log(total+"  "+(parts.join(", ")||"ninguna"));
  }catch(e){ console.log("ERR parse"); }
});
' "$AUDIT_LEVEL")"

total="${result%%  *}"
detail="${result#*  }"

if [ "$total" = "ERR" ]; then
  echo "⚠ audit-gate: no se pudo interpretar el reporte de npm audit ($detail). Se permite el commit."
  exit 0
fi

if [ "$total" -gt 0 ] 2>/dev/null; then
  echo "✖ audit-gate: $detail (umbral: >= $AUDIT_LEVEL)."
  echo "  Commit BLOQUEADO por vulnerabilidades en dependencias del frontend."
  echo "  Detalle:                  cd frontend && npm audit"
  echo "  Arreglo automático:       cd frontend && npm audit fix"
  echo "  Si requiere override:     agregá \"overrides\" en frontend/package.json"
  echo "  Saltear (no recomendado): git commit --no-verify"
  exit 1
fi

echo "✓ audit-gate: 0 vulnerabilidades (>= $AUDIT_LEVEL)."
exit 0

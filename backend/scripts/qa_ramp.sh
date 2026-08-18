#!/usr/bin/env bash
# Driver de ramp-up do Agente L. Roda qa_load.py em degraus e coleta JSON.
# Uso: scripts/qa_ramp.sh <base_url> <server_pid> <scenario> <dur> <vu1> <vu2> ...
set -u
BASE="${1:?base}"; PID="${2:?pid}"; SC="${3:?scenario}"; DUR="${4:?dur}"; shift 4
PY="./venv/bin/python"
echo "# ramp scenario=$SC dur=${DUR}s pid=$PID base=$BASE"
for VU in "$@"; do
  $PY scripts/qa_load.py --base "$BASE" --server-pid "$PID" --scenario "$SC" --vus "$VU" --duration "$DUR"
  AVAIL=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
  # trava de segurança: aborta o ramp se a RAM disponível cair demais
  if [ "$AVAIL" -lt 600 ]; then
    echo "# ABORT: MemAvailable ${AVAIL}MB < 600MB — parando ramp-up"
    break
  fi
  sleep 2
done

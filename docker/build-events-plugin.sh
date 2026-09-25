#!/usr/bin/env bash
# Compila o plugin Cs2TrackerEvents (docker/plugins-src/Cs2TrackerEvents)
# usando a imagem oficial do SDK .NET via Docker — não precisa instalar
# nada além do Docker no host. Resultado vai pra docker/plugins/Cs2TrackerEvents/,
# já no formato esperado pelo CounterStrikeSharp (mesmo padrão de
# docker/plugins/DefaultAgents/, montado no docker-compose.yml).
set -euo pipefail
cd "$(dirname "$0")/.."

SRC_DIR="docker/plugins-src/Cs2TrackerEvents"
OUT_DIR="docker/plugins/Cs2TrackerEvents"

echo "[BUILD] Compilando $SRC_DIR via dotnet/sdk:10.0 (Docker)..."
docker run --rm \
  -v "$(pwd)/$SRC_DIR:/src" \
  -w /src \
  mcr.microsoft.com/dotnet/sdk:10.0 \
  dotnet publish -c Release -o /src/bin/publish

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"
cp "$SRC_DIR"/bin/publish/Cs2TrackerEvents.dll "$OUT_DIR"/
cp "$SRC_DIR"/bin/publish/Cs2TrackerEvents.deps.json "$OUT_DIR"/ 2>/dev/null || true
cp "$SRC_DIR"/bin/publish/Cs2TrackerEvents.pdb "$OUT_DIR"/ 2>/dev/null || true

echo "[BUILD] OK -> $OUT_DIR"

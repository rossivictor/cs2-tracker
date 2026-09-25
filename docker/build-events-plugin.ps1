# Compila o plugin Cs2TrackerEvents (docker/plugins-src/Cs2TrackerEvents)
# usando a imagem oficial do SDK .NET via Docker — não precisa instalar
# nada além do Docker no host. Resultado vai pra docker/plugins/Cs2TrackerEvents/,
# já no formato esperado pelo CounterStrikeSharp (mesmo padrão de
# docker/plugins/DefaultAgents/, montado no docker-compose.yml).
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$srcDir = "docker/plugins-src/Cs2TrackerEvents"
$outDir = "docker/plugins/Cs2TrackerEvents"

Write-Host "[BUILD] Compilando $srcDir via dotnet/sdk:10.0 (Docker)..."
docker run --rm `
  -v "${root}\${srcDir}:/src" `
  -w /src `
  mcr.microsoft.com/dotnet/sdk:10.0 `
  dotnet publish -c Release -o /src/bin/publish
if ($LASTEXITCODE -ne 0) { throw "dotnet publish falhou (exit $LASTEXITCODE)" }

if (Test-Path $outDir) { Remove-Item -Recurse -Force $outDir }
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Copy-Item "$srcDir/bin/publish/Cs2TrackerEvents.dll" $outDir
Copy-Item "$srcDir/bin/publish/Cs2TrackerEvents.deps.json" $outDir -ErrorAction SilentlyContinue
Copy-Item "$srcDir/bin/publish/Cs2TrackerEvents.pdb" $outDir -ErrorAction SilentlyContinue

Write-Host "[BUILD] OK -> $outDir"

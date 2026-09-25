#!/bin/bash
source "${HOMEDIR}/xbirdcs2matchzy/start.sh"

# CS2 Tracker — registra overrides/botprofile.vpk como search path do jogo.
#
# O CS2-Bot-Improver instala o VPK com os perfis pro em
# game/csgo/overrides/botprofile.vpk, mas o dedicated server (srcds) nunca
# monta esse arquivo sozinho — o dump de boot (GAME/MOD/PLATFORM em
# docker logs) só lista pak01.vpk/shaders_vulkan.vpk de csgo/, csgo_imported/,
# csgo_core/ e core/. Sem essa entrada, bot_add_ct com nome de pro falha com
# "no profile for '<nome>' exists.", mesmo com o VPK correto instalado.
# Ver docs/SPEC.md §10 (Passo 0, 2026-09-19) pro diagnóstico completo.
#
# Idempotente: só insere se ainda não estiver presente, então sobrevive a
# reinícios sem duplicar a linha.
GAMEINFO="${STEAMAPPDIR}/game/csgo/gameinfo.gi"

if [[ -f "$GAMEINFO" ]] && ! grep -q "overrides/botprofile.vpk" "$GAMEINFO"; then
    python3 - "$GAMEINFO" <<'PYEOF'
import re
import sys

path = sys.argv[1]
with open(path, "rb") as f:
    data = f.read()

# Casa a linha inteira do search path do Metamod, com qualquer final de
# linha (\n, \r\n ou até \n\r visto num boot anterior), pra não depender
# de um formato exato de quebra de linha.
pattern = re.compile(rb"(Game\tcsgo/addons/metamod)(\r?\n)")
match = pattern.search(data)
if not match:
    print("[cs2-tracker] AVISO: marcador 'Game csgo/addons/metamod' nao encontrado em gameinfo.gi — patch nao aplicado")
    sys.exit(0)

insertion = match.group(1) + match.group(2) + b"\t\t\tGame\tcsgo/overrides/botprofile.vpk" + match.group(2)
data = data[:match.start()] + insertion + data[match.end():]

with open(path, "wb") as f:
    f.write(data)
print("[cs2-tracker] gameinfo.gi patched: overrides/botprofile.vpk registrado como search path")
PYEOF
else
    echo "[cs2-tracker] gameinfo.gi ja tem o search path de overrides/botprofile.vpk, nada a fazer"
fi

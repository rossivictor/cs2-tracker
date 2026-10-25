#!/usr/bin/env python3
"""
Confere offline os 6 plugins de bot numa cópia do libserver.so (card B1.13).

Para cada plugin: as assinaturas Linux próprias (tabela ASSINATURAS, tirada das
fontes que o compose monta: os forks e o clone de 26/09), cada uma casando 1 vez
na `.text`, com a âncora de string (`lea reg,[rip+x]` para a string esperada no
começo da função), o byte original do patch e os disp32 de offset que a função
lê; as assinaturas Linux do `server` no gamedata da CSSharp de que o plugin
depende (DEPENDE); o BotAI pela saída do conferir_botai_2000930.py do B1.7b
(`RESULTADO: OK` sobre o mesmo sha256); e as 3 assinaturas Linux do NadeSystem.cs
do fork, que têm de ser as da tabela. O que não se prova offline sai em
"sem prova offline" e fica para o G6.

Saída 0 com `RESULTADO: OK`, 1 com divergência e 2 se o insumo não for o
esperado (tamanho, sha256, ELF, arquivo). Só biblioteca padrão. Uso:

    C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/conferir_plugins_bot.py \\
      --lib <libserver.so> --sha <sha256> --tamanho <bytes> --gamedata <gamedata.json> \\
      --botai-saida <saída do conferir_botai> --nadesystem-fonte <fork>/NadeSystem.cs

Método e resultado na 2000935: docs/runbooks/b1.13-plugins-de-bot-2000935.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

CURINGA16 = " ".join(["?"] * 16)
SMOKE_B113 = ("55 4C 89 C1 48 89 E5 41 57 " + CURINGA16
              + " 48 81 EC 78 01 00 00 48 89 95 78 FE FF FF 48 89 F2 48 89 FE 48 8D 3D")
FOV_DESLIGA = "não casa: o plugin desliga o FOV 360 da busca de defuse sem escrever"

# (plugin, nome, padrão, verificações). Verificações: ancora (prefixo da string
# referida por lea rip-relativo nos primeiros 0x300 bytes), disp32 [(deslocamento,
# valor)], contem_disp32 [valores nos primeiros 0x200 bytes], byte_em (deslocamento,
# valor original) e zero_desliga (0 casamentos é degradação do próprio plugin).
ASSINATURAS = [
    ("NadeSystem", "CSmokeGrenadeProjectile::Create", SMOKE_B113,
     {"ancora": "smokegrenade_projectile"}),
    ("NadeSystem", "CHEGrenadeProjectile::Create",
     "55 4C 89 C1 48 89 E5 41 57 49 89 FF 41 56 49 89 D6 48 89 F2 48 89 FE 41 55",
     {"ancora": "hegrenade_projectile"}),
    ("NadeSystem", "CMolotovProjectile::Create",
     "55 48 8D 05 ? ? ? ? 48 89 E5 41 57 41 56 41 55 41 54 49 89 FC 53 48 81 EC ? ? ? ? 4C 8D 35",
     {"ancora": "molotov_projectile"}),
    ("BotAimImprover", "CCSBot::PickNewAimSpot",
     "55 48 89 E5 41 55 41 54 53 48 89 FB 48 83 EC 58 8B 8F ? ? 00 00 83 F9 FF",
     {"disp32": [(18, 0x59D8)], "contem_disp32": [0x59DC, 0x596C]}),
    ("BotRandomizer", "SetOrAddAttributeValueByName",
     "55 48 89 E5 41 57 41 56 41 55 49 89 FD 41 54 53 48 89 F3 48 83 EC ? F3 0F 11 85", {}),
    ("BotRandomizer", "CEconItemView::CEconItemView",
     "55 48 8D 05 ? ? ? ? 66 0F EF C0 48 89 E5 41 57 41 56 4C 8D 35 ? ? ? ? 41 55 41 54 45 31 E4", {}),
    ("BotState", "CCSBot::DefuseBomb", "48 8D B7 00 04 00 00 E9 ? ? ? ?", {}),
    ("BotState", "CCSBot::Blind", "55 48 8D 35 ? ? ? ? B8 ? ? ? ? F3 0F 5A D2",
     {"ancora": "Blinded: holdTime"}),
    ("BotState", "IsVisiblePos_IgnoreFOV",
     "80 BD ? ? ? ? 00 74 ? 48 8B 7B 18 48 8B B5 ? ? ? ? 48 8B 07 FF 90 A0 09 00 00 84 C0 74 ?",
     {"byte_em": (7, 0x74), "zero_desliga": FOV_DESLIGA}),
    ("BotState", "IsVisiblePlayer_IgnoreFOV",
     "45 84 F6 74 ? 49 8B 54 24 18 48 89 DF 48 8B 0A 48 89 55 98 48 8B 89 A0 09 00 00 48 89 4D A0 FF 90 B8 02 00 00",
     {"byte_em": (3, 0x74), "zero_desliga": FOV_DESLIGA}),
]
PLUGINS = ("BotAI", "BotAimImprover", "BotRandomizer", "BotBuy", "BotState", "NadeSystem")
# Chaves do gamedata da CSSharp que a API usa por baixo das chamadas de cada fonte.
DEPENDE = {
    "NadeSystem": ["UTIL_CreateEntityByName", "CBaseEntity_DispatchSpawn", "CBaseEntity_Teleport",
                   "CBaseEntity_EmitSoundFilter", "CEntityInstance_AcceptInput", "UTIL_Remove",
                   "NetworkStateChanged", "SetStateChanged"],
    "BotBuy": ["GiveNamedItem", "CBasePlayerPawn_RemovePlayerItem", "UTIL_Remove", "ClientPrint",
               "NetworkStateChanged", "SetStateChanged"],
    "BotRandomizer": ["GiveNamedItem", "CEntityInstance_AcceptInput", "CBaseModelEntity_SetModel",
                      "NetworkStateChanged", "SetStateChanged"],
}
SEM_PROVA = {
    "BotAimImprover": "m_pBot do CCSPlayerPawn (0x17D8): o G6 vê `[BotAimImprover] Loaded (Linux)` e o smoke, zero exceção",
    "BotBuy": "nenhuma assinatura própria; o G6 vê `BotBuyPatch` carregado e bots comprando",
    "BotState": "hooks por assinatura sem âncora (DefuseBomb): o G6 vê `Smarter-Bot` carregado, sem erro de hook",
}
GERAL = ("offsets de vtable do gamedata e compatibilidade das DLLs (API 1.0.367 a 1.0.375) "
         "com a CSSharp 1.0.378: só o `Finished loading` e o smoke do G6 provam")
RE_LINUX = re.compile(r'IsOSPlatform\(OSPlatform\.Linux\)\s*(?://[^\n]*\n\s*)*\?\s*@?"([0-9A-Fa-f? ]+)"')


class InsumoInvalido(Exception):
    pass


def secoes(dados: bytes) -> dict:
    """{nome: (endereço, offset no arquivo, tamanho)} das seções de um ELF64 LE."""
    if dados[:4] != b"\x7fELF" or dados[4] != 2 or dados[5] != 1:
        raise InsumoInvalido("não é um ELF64 little-endian")
    shoff = struct.unpack_from("<Q", dados, 0x28)[0]
    tam, num, idx = struct.unpack_from("<HHH", dados, 0x3A)
    cab = [struct.unpack_from("<IIQQQQ", dados, shoff + i * tam) for i in range(num)]
    base = cab[idx][4]
    saida = {}
    for nome, _tipo, _flags, end, off, tamanho in cab:
        fim = dados.index(b"\0", base + nome)
        saida[dados[base + nome:fim].decode("ascii", "replace")] = (end, off, tamanho)
    if ".text" not in saida:
        raise InsumoInvalido("ELF sem .text")
    return saida


def padrao(texto: str) -> re.Pattern:
    """Assinatura no formato da CSSharp (`?` casa qualquer byte), com casamentos sobrepostos."""
    partes = [b"." if t in ("?", "??") else re.escape(bytes([int(t, 16)])) for t in texto.split()]
    return re.compile(b"(?=" + b"".join(partes) + b")", re.S)


def casamentos(dados: bytes, secs: dict, texto: str) -> list:
    _end, off, tam = secs[".text"]
    return [m.start() for m in padrao(texto).finditer(dados, off, off + tam)]


def strings_referidas(dados: bytes, secs: dict, inicio: int, janela: int = 0x300) -> list:
    """Strings de .rodata* apontadas por `lea r64,[rip+disp32]` a partir de `inicio`."""
    end_t, off_t, _ = secs[".text"]
    achadas = []
    for i in range(inicio, min(inicio + janela, len(dados) - 7)):
        if dados[i] in (0x48, 0x4C) and dados[i + 1] == 0x8D and dados[i + 2] & 0xC7 == 0x05:
            alvo = end_t + (i + 7 - off_t) + struct.unpack_from("<i", dados, i + 3)[0]
            for nome, (end, off, tam) in secs.items():
                if nome.startswith(".rodata") and end <= alvo < end + tam:
                    o = off + alvo - end
                    achadas.append(dados[o:dados.index(b"\0", o)].decode("latin-1"))
    return achadas


def conferir_entrada(dados: bytes, secs: dict, nome: str, texto: str, v: dict) -> tuple:
    """(estado, linha): estado OK, AVISO (degradação que o próprio plugin trata) ou DIVERGE."""
    achados = casamentos(dados, secs, texto)
    if not achados:
        if v.get("zero_desliga"):
            return "AVISO", f"{nome}: 0 casamentos; {v['zero_desliga']}"
        return "DIVERGE", f"{nome}: NÃO CASA (0 casamentos)"
    if len(achados) > 1:
        return "DIVERGE", f"{nome}: {len(achados)} casamentos, a CSSharp pegaria o primeiro"
    a = achados[0]
    notas = [f"{nome}: 1 casamento, arquivo {a:#x}"]
    if "ancora" in v:
        refs = strings_referidas(dados, secs, a)
        if not any(r.startswith(v["ancora"]) for r in refs):
            return "DIVERGE", f"{nome}: casa em {a:#x}, mas sem a âncora '{v['ancora']}' ({refs[:3]})"
        notas.append(f"âncora '{v['ancora']}'")
    for desloc, valor in v.get("disp32", []):
        lido = struct.unpack_from("<I", dados, a + desloc)[0]
        if lido != valor:
            return "DIVERGE", f"{nome}: disp32 em +{desloc} é {lido:#x}, esperado {valor:#x}"
        notas.append(f"disp32 +{desloc} = {valor:#x}")
    corpo = dados[a:a + 0x200]
    for valor in v.get("contem_disp32", []):
        if struct.pack("<I", valor) not in corpo:
            return "DIVERGE", f"{nome}: a função não lê {valor:#x}"
        notas.append(f"lê {valor:#x}")
    if "byte_em" in v:
        desloc, valor = v["byte_em"]
        if dados[a + desloc] != valor:
            return "DIVERGE", f"{nome}: byte original {dados[a + desloc]:#04x}, esperado {valor:#04x}"
        notas.append(f"byte original {valor:#04x}")
    return "OK", "; ".join(notas)


def conferir_gamedata(dados: bytes, secs: dict, gamedata: dict) -> dict:
    """{chave: 'OK' | 'offset' | 'N casamentos'} das entradas do server no Linux."""
    saida = {}
    for chave, v in gamedata.items():
        sig = v.get("signatures", {})
        if "linux" in sig and sig.get("library") == "server":
            n = len(casamentos(dados, secs, sig["linux"]))
            saida[chave] = "OK" if n == 1 else f"{n} casamentos"
        elif "linux" in v.get("offsets", {}):
            saida[chave] = "offset"
    return saida


def conferir_botai(texto: str, sha: str) -> tuple:
    linhas = [ln.strip() for ln in texto.splitlines() if ln.strip()]
    if not any(sha in ln for ln in linhas):
        return "DIVERGE", "saída do conferir_botai é de outro libserver (sha256 não confere)"
    if not linhas or linhas[-1] != "RESULTADO: OK":
        return "DIVERGE", "saída do conferir_botai sem `RESULTADO: OK`"
    return "OK", "conferir_botai_2000930.py: RESULTADO: OK neste sha256 (40 entradas, m_gameState)"


def conferir_fonte_nade(texto: str) -> tuple:
    achadas = [" ".join(s.split()).upper() for s in RE_LINUX.findall(texto)]
    tabela = [" ".join(t.split()) for p, _n, t, _v in ASSINATURAS if p == "NadeSystem"]
    if achadas != tabela:
        return "DIVERGE", f"fonte: as assinaturas Linux do NadeSystem.cs não são as da tabela ({len(achadas)} lidas)"
    return "OK", f"fonte: as {len(achadas)} assinaturas Linux do NadeSystem.cs são as da tabela"


def ler(caminho: Path) -> bytes:
    try:
        return Path(caminho).read_bytes()
    except OSError as exc:
        raise InsumoInvalido(f"{caminho}: {exc.strerror}") from exc


def conferir(args) -> int:
    dados = ler(args.lib)
    sha = hashlib.sha256(dados).hexdigest()
    if len(dados) != args.tamanho or sha != args.sha.lower():
        raise InsumoInvalido(f"{args.lib}: {len(dados)} bytes, sha256 {sha} (esperado {args.tamanho}, {args.sha})")
    secs = secoes(dados)
    gamedata = json.loads(ler(args.gamedata).decode("utf-8-sig"))
    print(f"insumo: {args.lib}\n  {len(dados)} bytes, sha256 {sha}\n  .text no arquivo "
          f"{secs['.text'][1]:#x}, {secs['.text'][2]:#x} bytes")
    gd = conferir_gamedata(dados, secs, gamedata)
    assinaturas = [k for k, v in gd.items() if v != "offset"]
    ruins = [k for k in assinaturas if gd[k] != "OK"]
    print(f"gamedata {args.gamedata}: {len(assinaturas) - len(ruins)}/{len(assinaturas)} assinaturas Linux "
          f"do server casam 1 vez; {len(gd) - len(assinaturas)} offsets sem prova offline")
    resultado = {p: [] for p in PLUGINS}
    resultado["BotAI"].append(conferir_botai(ler(args.botai_saida).decode("utf-8", "replace"), sha))
    for plugin, nome, texto, v in ASSINATURAS:
        resultado[plugin].append(conferir_entrada(dados, secs, nome, texto, v))
    resultado["NadeSystem"].append(conferir_fonte_nade(ler(args.nadesystem_fonte).decode("utf-8-sig")))
    for plugin, chaves in DEPENDE.items():
        falhas = [f"{k} ({gd.get(k, 'ausente')})" for k in chaves if gd.get(k) not in ("OK", "offset")]
        resultado[plugin].append(("DIVERGE", "gamedata: " + ", ".join(falhas)) if falhas else
                                 ("OK", "gamedata: " + ", ".join(f"{k} {gd[k]}" for k in chaves)))
    divergiu = False
    for plugin in PLUGINS:
        print(f"\n[{plugin}]")
        for estado, linha in resultado[plugin]:
            print(f"  {estado}: {linha}")
        if plugin in SEM_PROVA:
            print(f"  sem prova offline: {SEM_PROVA[plugin]}")
        estados = {e for e, _ in resultado[plugin]}
        veredito = "DIVERGE" if "DIVERGE" in estados else "OK com aviso" if "AVISO" in estados else "OK"
        divergiu |= veredito == "DIVERGE"
        print(f"  PLUGIN {plugin}: {veredito}")
    print(f"\nsem prova offline (todos): {GERAL}")
    print("\nRESULTADO: " + ("DIVERGE" if divergiu else "OK"))
    return 1 if divergiu else 0


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--lib", type=Path, required=True)
    ap.add_argument("--sha", required=True)
    ap.add_argument("--tamanho", type=int, required=True)
    ap.add_argument("--gamedata", type=Path, required=True)
    ap.add_argument("--botai-saida", type=Path, required=True)
    ap.add_argument("--nadesystem-fonte", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        return conferir(args)
    except (InsumoInvalido, ValueError, IndexError, struct.error) as exc:
        print(f"insumo inválido: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())

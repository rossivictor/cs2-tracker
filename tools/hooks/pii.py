#!/usr/bin/env python3
"""
Dado pessoal e segredo em texto que vai para o repositório público (card
B0.5). O hook de guarda (tools/hooks/guarda.py) chama `achar` no Write/Edit;
o escopo (que parte vale em que pasta) é decidido lá.

Acha:
  - SteamID64 com cara de real (7656119 + 10 dígitos) acima da base
    76561197960265728, menos os de IDS_FICTICIOS: até a base não existe
    conta (SteamID64 = base + ID da conta), então esses são fictícios e
    servem para fixture anonimizada;
  - SteamID3 ([U:1:n]), menos [U:1:0] e os equivalentes dos fictícios;
  - IPv4 fora de 127.0.0.1 e 0.0.0.0, menos número de versão (build,
    versão, version ou patch logo antes: PatchVersion=1.40.9.3);
  - os valores de SRCDS_TOKEN, CS2_RCONPW e MATCHZY_ADMINS do .env do
    checkout principal, lidos na hora. Valor igual ao do .env.example é
    público e não conta. Sem .env, essa parte é pulada.

Nenhuma mensagem traz o valor achado: só o tipo e a linha. O segredo do
.env nunca é impresso, nem em erro.

Só biblioteca padrão.
"""
from __future__ import annotations

import os
import re

# Só abaixo da base (T1.3): o ID fictício antigo, acima dela, saiu com OK do
# Victor em 28/09, porque pode ser conta real.
IDS_FICTICIOS = frozenset({"76561190000000001"})
# SteamID64 = BASE + ID da conta; o SteamID3 é [U:1:<ID da conta>].
BASE_STEAMID64 = 76561197960265728
STEAMID3_FICTICIOS = frozenset(
    {"[U:1:0]"} | {f"[U:1:{int(s) - BASE_STEAMID64}]" for s in IDS_FICTICIOS
                   if int(s) > BASE_STEAMID64}
)
IPS_LIBERADOS = frozenset({"127.0.0.1", "0.0.0.0"})
CHAVES_DO_ENV = ("SRCDS_TOKEN", "CS2_RCONPW", "MATCHZY_ADMINS")
# Segredo mais curto que isso casaria palavra comum; o MATCHZY_ADMINS tem
# SteamID64, que a regra própria já pega.
TAMANHO_MINIMO_SEGREDO = 4
MAX_ACHADOS = 5

_STEAMID64 = re.compile(r"(?<!\d)7656119\d{10}(?!\d)")
_STEAMID3 = re.compile(r"\[U:1:\d+\]", re.IGNORECASE)
# Nem colado em letra/ponto antes (v1.2.3.4, 2.0.0.1411), nem seguido de
# dígito ou de ".dígito" (1.2.3.4.5). Ponto final de frase ainda casa.
_IPV4 = re.compile(r"(?<![\w.])(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?!\.?\d)(?!\w)")
# Palavra de versão até ~24 caracteres antes, na mesma linha: CS2 build 1.40.9.3.
_ANTES_DE_VERSAO = re.compile(r"(?:build|vers[aã]o|version|patch)[^\n]{0,24}$", re.IGNORECASE)


def _linha(texto: str, pos: int) -> int:
    return texto.count("\n", 0, pos) + 1


def _ler_env(caminho) -> dict:
    """KEY -> valor das chaves de CHAVES_DO_ENV. Arquivo ausente: {}."""
    try:
        with open(caminho, encoding="utf-8-sig", errors="replace") as arq:
            texto = arq.read()
    except OSError:
        return {}
    valores = {}
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        if linha.startswith("export "):
            linha = linha[len("export "):].lstrip()
        chave, igual, valor = linha.partition("=")
        chave = chave.strip()
        if not igual or chave not in CHAVES_DO_ENV:
            continue
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "'\"":
            valor = valor[1:-1]
        else:
            valor = valor.split(" #", 1)[0].strip()
        valores[chave] = valor
    return valores


def ler_segredos(caminho_env) -> list:
    """[(chave, valor)] a procurar no texto. O MATCHZY_ADMINS vale inteiro e
    também cada item da lista separada por vírgula."""
    reais = _ler_env(caminho_env)
    if not reais:
        return []
    publicos = _ler_env(os.path.join(os.path.dirname(os.fspath(caminho_env)), ".env.example"))
    segredos = []
    for chave, valor in reais.items():
        partes = [valor]
        if chave == "MATCHZY_ADMINS":
            partes += [p.strip() for p in valor.split(",")]
        for parte in partes:
            if (len(parte) >= TAMANHO_MINIMO_SEGREDO and parte != publicos.get(chave)
                    and parte not in IDS_FICTICIOS and (chave, parte) not in segredos):
                segredos.append((chave, parte))
    return segredos


def segredo_forte(valor: str) -> bool:
    """Valor que não aparece por acaso em código: 16+ caracteres (token, SteamID)
    ou 8+ misturando letra e dígito. Fora de docs/ e afins, só esses contam:
    uma senha fraca ("password") casaria meio repositório."""
    return len(valor) >= 16 or (len(valor) >= 8 and any(c.isdigit() for c in valor)
                                and any(c.isalpha() for c in valor))


def ficticio(steamid64: str) -> bool:
    """Da allowlist ou até a base: não existe conta com esse número."""
    return steamid64 in IDS_FICTICIOS or int(steamid64) <= BASE_STEAMID64


def _versao(texto: str, pos: int) -> bool:
    return _ANTES_DE_VERSAO.search(texto, max(0, pos - 40), pos) is not None


def achar(texto: str, segredos=(), ids=True, ips=True) -> list:
    """Descrições (sem o valor) do que não pode ir para o repositório.
    `ids` liga SteamID64/SteamID3 e `ips` liga IPv4; segredo vale sempre."""
    achados = []
    for m in _STEAMID64.finditer(texto) if ids else ():
        if not ficticio(m.group(0)):
            achados.append(f"SteamID64 real na linha {_linha(texto, m.start())}")
    for m in _STEAMID3.finditer(texto) if ids else ():
        if m.group(0).upper() not in STEAMID3_FICTICIOS:
            achados.append(f"SteamID3 [U:1:n] na linha {_linha(texto, m.start())}")
    for m in _IPV4.finditer(texto) if ips else ():
        octetos = [int(g) for g in m.groups()]
        if (all(o <= 255 for o in octetos) and m.group(0) not in IPS_LIBERADOS
                and not _versao(texto, m.start())):
            achados.append(f"IPv4 na linha {_linha(texto, m.start())}")
    for chave, valor in segredos:
        m = re.search(r"(?<![A-Za-z0-9])" + re.escape(valor) + r"(?![A-Za-z0-9])", texto)
        if m:
            achados.append(f"valor de {chave} do .env na linha {_linha(texto, m.start())}")
    if len(achados) > MAX_ACHADOS:
        achados = achados[:MAX_ACHADOS] + [f"e mais {len(achados) - MAX_ACHADOS}"]
    return achados

#!/usr/bin/env python3
"""
RCON só no loopback (card P1.11): no docker-compose.yml a 27015/tcp (RCON)
é publicada só em 127.0.0.1, enquanto a 27015/udp (jogo) e a 27020/udp
(CSTV) seguem em todas as interfaces; e o override da válvula vanilla
(docker-compose.vanilla.yml, card P1.2) não publica porta nenhuma, então o
merge do compose não traz de volta uma 27015/tcp sem host.

A .venv não tem PyYAML: os blocos `ports:` saem do texto, só na sintaxe
curta entre aspas, que é a que o repo usa; entrada em outra forma reprova o
teste em vez de passar calada. Os gabaritos são escritos à mão. Nada de
docker, processo ou rede: só leitura de arquivo (e tmp_path no teste do
leitor).
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BASE = RAIZ / "docker-compose.yml"
VANILLA = RAIZ / "docker-compose.vanilla.yml"

# "[ip:]publicada:alvo[/proto]", com ou sem aspas
_ENTRADA = re.compile(r'^-\s+"?(?:(?P<ip>[0-9.]+):)?(?P<pub>\d+):(?P<alvo>\d+)(?:/(?P<proto>tcp|udp))?"?\s*(?:#.*)?$')


def _portas(texto: str) -> list:
    """Lista (ip, publicada, alvo, proto) de todos os blocos `ports:` do texto.
    ip None = todas as interfaces; proto padrão do compose é tcp."""
    portas = []
    linhas = texto.splitlines()
    i = 0
    while i < len(linhas):
        m = re.match(r"^(\s*)ports:\s*(#.*)?$", linhas[i])
        if not m:
            assert not re.match(r"^\s*ports:", linhas[i]), \
                f"bloco ports em forma não suportada pelo teste: {linhas[i]!r}"
            i += 1
            continue
        recuo = len(m.group(1))
        i += 1
        while i < len(linhas):
            bruta = linhas[i]
            limpa = bruta.strip()
            if not limpa or limpa.startswith("#"):
                i += 1
                continue
            if len(bruta) - len(bruta.lstrip()) <= recuo:
                break
            e = _ENTRADA.match(limpa)
            assert e, f"entrada de porta fora da sintaxe curta: {bruta!r}"
            portas.append((e["ip"], int(e["pub"]), int(e["alvo"]), e["proto"] or "tcp"))
            i += 1
    return portas


def test_leitor_entende_ip_proto_padrao_e_comentario(tmp_path):
    arq = tmp_path / "c.yml"
    arq.write_text(
        "services:\n"
        "  s:\n"
        "    ports:\n"
        "      # comentário\n"
        '      - "127.0.0.1:1:2/tcp"\n'
        "      - 3:4\n"
        '      - "5:6/udp"\n'
        "    tty: true\n", encoding="utf-8")
    assert _portas(arq.read_text(encoding="utf-8")) == [
        ("127.0.0.1", 1, 2, "tcp"), (None, 3, 4, "tcp"), (None, 5, 6, "udp")]


def test_base_publica_rcon_so_no_loopback_e_jogo_e_cstv_abertos():
    assert _portas(BASE.read_text(encoding="utf-8")) == [
        ("127.0.0.1", 27015, 27015, "tcp"),
        (None, 27015, 27015, "udp"),
        (None, 27020, 27020, "udp"),
    ]


def test_nenhuma_27015_tcp_sem_host_no_base_nem_no_vanilla():
    for arq in (BASE, VANILLA):
        tcp_27015 = [p for p in _portas(arq.read_text(encoding="utf-8"))
                     if p[1] == 27015 and p[3] == "tcp"]
        assert all(p[0] == "127.0.0.1" for p in tcp_27015), (arq.name, tcp_27015)


def test_override_vanilla_nao_publica_porta():
    texto = VANILLA.read_text(encoding="utf-8")
    assert _portas(texto) == []
    assert not re.search(r"^\s*ports\s*:", texto, re.M)

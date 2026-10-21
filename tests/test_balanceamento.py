#!/usr/bin/env python3
"""
Contagem de presentes no balanceamento (card P1.7).

Dois defeitos em _force_start_and_balance_bots, vistos nas partidas 89, 91
e 93 (19-20/10):

1. `presentes` somava o tamanho das tuplas (nome, time) do snapshot: 2 por
   cliente. Com 7 clientes dava 14, maior que os 10 esperados, e a
   recomposição de times nunca disparava.
2. "Times após reconciliação" relia o MESMO bloco OnPreResetRound de antes
   do kick do excedente e anunciava o 6:4 velho (no log e no chat do jogo),
   embora o servidor já tivesse kickado o bot e reposto pela quota.

Agora os dois contam clientes pelo `status` do RCON, com espera limitada.
O `status` não traz o lado de ninguém: a linha final diz quantos clientes
há, não um CT:TR que ninguém mediu.

"Teste 4x5": 5x5 com o humano no CT monta 4 bots CT + 5 TR; com o humano no
TR, o espelho 5 CT + 4 TR. Os gabaritos (linhas de log, comandos RCON,
contagens) estão escritos à mão. Os fakes trocam start_match.subprocess,
start_match.RconClient e start_match.time: nenhum processo, rede, Docker ou
RCON de verdade, e o relógio falso só anda no sleep.
"""
import json
import subprocess
import types

import pytest

import start_match

NICK = "cobaia"


def _linha_time(nome, cid, time_):
    return f'"{nome}<{cid}><BOT><{time_}>" OnPreResetRound => CTMDBG\n'


def _bloco(ct, tr, humano_ct):
    """Bloco OnPreResetRound com os bots `ct` e `tr` e o humano no lado dele."""
    linhas = [_linha_time(nome, i, "CT") for i, nome in enumerate(ct, start=1)]
    linhas += [_linha_time(nome, 20 + i, "TERRORIST") for i, nome in enumerate(tr, start=1)]
    linhas.append(_linha_time(NICK, 0, "CT" if humano_ct else "TERRORIST"))
    return "".join(linhas)


def _status(n):
    return "---------players--------\n" + "".join(
        f"  {i} 00:01 0 0 active 0 'jogador{i}'\n" for i in range(n)) + "#end\n"


class Relogio:
    def __init__(self):
        self.t = 1000.0

    def time(self):
        return self.t

    def sleep(self, s):
        self.t += s


class Servidor:
    """Simula a contagem de clientes do servidor a partir dos comandos RCON.

    - `bot_kick` puro zera os bots; cada bot_add_* põe um; `bot_kick "nome"`
      tira um.
    - `pos_start`: quantos clientes o servidor tem logo depois do css_start
      (None = os mesmos de antes).
    - `repoe`: a quota repõe o bot kickado pelo nome, mas só depois da
      primeira leitura do `status` (a reposição é assíncrona).
    - O `docker logs --tail` devolve `bloco_antes` até o css_start e
      `bloco_depois` a partir dele, e nunca muda por causa de um kick: é o
      bloco velho que o servidor ainda não renovou.
    """

    def __init__(self, bloco_antes, bloco_depois, pos_start=None, repoe=True):
        self.rcon = []
        self.clientes = 1  # o humano
        self.bloco_antes = bloco_antes
        self.bloco_depois = bloco_depois
        self.pos_start = pos_start
        self.repoe = repoe
        self.a_repor = 0
        self.ao_vivo = False

    def run(self, argv, **kwargs):
        assert argv[0] == "docker", argv
        if argv[1:3] == ["logs", "--tail"]:
            bloco = self.bloco_depois if self.ao_vivo else self.bloco_antes
            return subprocess.CompletedProcess(argv, 0, bloco, "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    def comando(self, cmd):
        self.rcon.append(cmd)
        if cmd == "bot_kick":
            self.clientes = 1
        elif cmd.startswith("bot_add_"):
            self.clientes += 1
        elif cmd.startswith('bot_kick "'):
            self.clientes -= 1
            if self.repoe:
                self.a_repor += 1
        elif cmd == "css_start":
            self.ao_vivo = True
            if self.pos_start is not None:
                self.clientes = self.pos_start
        elif cmd == "status":
            resposta = _status(self.clientes)
            self.clientes += self.a_repor
            self.a_repor = 0
            return resposta
        return ""

    def cliente(self):
        servidor = self

        class RconFalso:
            def __init__(self, host, port, passwd=None, timeout=None):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def run(self, cmd):
                return servidor.comando(cmd)

        return RconFalso


def _instalar(monkeypatch, servidor):
    relogio = Relogio()
    monkeypatch.setattr(start_match, "subprocess", types.SimpleNamespace(
        run=servidor.run, PIPE=subprocess.PIPE))
    monkeypatch.setattr(start_match, "RconClient", servidor.cliente())
    monkeypatch.setattr(start_match, "time", types.SimpleNamespace(
        time=relogio.time, sleep=relogio.sleep))
    return relogio


def _config(tmp_path, lado):
    caminho = tmp_path / "match_config.json"
    caminho.write_text(json.dumps({"num_maps": 1, "map_sides": [f"team1_{lado}"]}),
                       encoding="utf-8")
    return caminho


def _rodar(tmp_path, lado):
    logs = []
    start_match.force_start_and_balance_bots(
        rcon_host="127.0.0.1", rcon_port=27015, rcon_password="fake",
        container_name="cs2-spike", team_size=5, player=NICK,
        local_match_config=_config(tmp_path, lado), log=logs.append)
    return logs


# Lado do humano -> (bots CT, bots TR) do 5x5 e o bloco equilibrado do warmup.
MONTAGEM = {
    "ct": (["Ct1", "Ct2", "Ct3", "Ct4"], ["Tr1", "Tr2", "Tr3", "Tr4", "Tr5"]),
    "t": (["Ct1", "Ct2", "Ct3", "Ct4", "Ct5"], ["Tr1", "Tr2", "Tr3", "Tr4"]),
}


def _bloco_equilibrado(lado):
    ct, tr = MONTAGEM[lado]
    return _bloco(ct, tr, humano_ct=lado == "ct")


# -- presentes depois do css_start: clientes, não tuplas --------------------

@pytest.mark.parametrize("lado, adds_ct, adds_t", [
    ("ct", 8, 10),  # 4 CT + 5 TR, duas vezes
    ("t", 10, 8),   # 5 CT + 4 TR, duas vezes
])
def test_faltando_cliente_depois_do_css_start_recompoe(tmp_path, monkeypatch,
                                                      lado, adds_ct, adds_t):
    """Só 7 clientes (humano + 6 bots) depois do css_start, e o bloco do
    docker logs mostra os mesmos 7. A soma antiga das tuplas dava 14 e não
    recompunha; contando clientes, 7 < 10 e os times são montados de novo."""
    bloco_7 = _bloco(["Ct1", "Ct2", "Ct3"], ["Tr1", "Tr2", "Tr3"], humano_ct=lado == "ct")
    servidor = Servidor(_bloco_equilibrado(lado), bloco_7, pos_start=7)
    _instalar(monkeypatch, servidor)

    logs = _rodar(tmp_path, lado)

    assert "  [AVISO] 7 cliente(s) após o css_start, esperado 10. Recompondo os times..." in logs
    assert servidor.rcon.count("bot_add_ct") == adds_ct
    assert servidor.rcon.count("bot_add_t") == adds_t
    assert servidor.rcon.count("bot_kick") == 2  # o da montagem e o da recomposição
    assert servidor.clientes == 10


@pytest.mark.parametrize("lado", ["ct", "t"])
def test_dez_clientes_nao_recompoe(tmp_path, monkeypatch, lado):
    servidor = Servidor(_bloco_equilibrado(lado), _bloco_equilibrado(lado))
    _instalar(monkeypatch, servidor)

    logs = _rodar(tmp_path, lado)

    assert not any("Recompondo" in linha for linha in logs)
    assert servidor.rcon.count("bot_kick") == 1
    assert not any(c.startswith('bot_kick "') for c in servidor.rcon)
    assert ("[MATCHZY] Clientes após reconciliação (status do RCON): 10 "
            "(esperado 10: 5 CT + 5 TR; o status não informa o lado).") in logs
    assert 'say "[CS2 Tracker] Times prontos: 10 jogadores em campo. Valendo!"' in servidor.rcon


# -- contagem depois do kick do excedente (partidas 89, 91 e 93) ------------

# O 1º bot cai no CT com o humano em qualquer lado: o bloco do ao vivo traz um
# bot a mais no CT e um a menos no TR. Contando o humano, os dois dão 6:4.
EXCEDENTE = {
    "ct": (_bloco(["Ct1", "Ct2", "Ct3", "Ct4", "Ct5"], ["Tr1", "Tr2", "Tr3", "Tr4"],
                  humano_ct=True),
           "[MATCHZY] CT com 5 bot(s), esperado 4 — kickando excedente(s): ['Ct1']"),
    "t": (_bloco(["Ct1", "Ct2", "Ct3", "Ct4", "Ct5", "Ct6"], ["Tr1", "Tr2", "Tr3"],
                 humano_ct=False),
          "[MATCHZY] CT com 6 bot(s), esperado 5 — kickando excedente(s): ['Ct1']"),
}


@pytest.mark.parametrize("lado", ["ct", "t"])
def test_contagem_final_le_o_servidor_depois_do_kick(tmp_path, monkeypatch, lado):
    """O kick tira o Ct1 (9 clientes) e a quota repõe um bot (10). A linha
    final mede 10 pelo status; antes ela relia o bloco velho e dizia
    "CT 6 : TR 4", no log e no chat."""
    bloco_depois, linha_kick = EXCEDENTE[lado]
    servidor = Servidor(_bloco_equilibrado(lado), bloco_depois)
    _instalar(monkeypatch, servidor)

    logs = _rodar(tmp_path, lado)

    assert linha_kick in logs
    kick = servidor.rcon.index('bot_kick "Ct1"')
    assert "status" in servidor.rcon[kick:]  # a contagem final vem depois do kick
    assert ("[MATCHZY] Clientes após reconciliação (status do RCON): 10 "
            "(esperado 10: 5 CT + 5 TR; o status não informa o lado).") in logs
    assert 'say "[CS2 Tracker] Times prontos: 10 jogadores em campo. Valendo!"' in servidor.rcon
    assert not any("CT 6 : TR 4" in linha for linha in logs)
    assert not any("CT 6 x 4 TR" in c for c in servidor.rcon)


def test_sem_reposicao_da_quota_anuncia_o_que_mediu(tmp_path, monkeypatch):
    """Se a quota não repõe, o servidor fica com 9 e é isso que sai, no log
    e no chat, depois de esperar no máximo PRESENTES_TIMEOUT_S."""
    bloco_depois, _ = EXCEDENTE["t"]
    servidor = Servidor(_bloco_equilibrado("t"), bloco_depois, repoe=False)
    relogio = _instalar(monkeypatch, servidor)

    logs = _rodar(tmp_path, "t")

    assert ("[MATCHZY] Clientes após reconciliação (status do RCON): 9 "
            "(esperado 10: 5 CT + 5 TR; o status não informa o lado).") in logs
    assert 'say "[CS2 Tracker] Atencao: 9 jogadores em campo, esperado 10."' in servidor.rcon
    assert not any("Times prontos" in c for c in servidor.rcon)
    # Espera limitada: 1 s da montagem + 3 s do css_start + 1 s depois do
    # kick + até 10 s de status, com folga para os 0,2 s entre os adds.
    assert relogio.t - 1000.0 < 20


def test_status_com_erro_nao_derruba_e_nao_inventa(tmp_path, monkeypatch):
    """O status falha depois do css_start: sem contagem, segue pela
    reconciliação de sempre e não anuncia time pronto nenhum."""
    servidor = Servidor(_bloco_equilibrado("ct"), _bloco_equilibrado("ct"))
    _instalar(monkeypatch, servidor)
    original = servidor.comando

    def comando(cmd):
        if cmd == "status" and servidor.ao_vivo:
            raise ConnectionError("rcon caiu")
        return original(cmd)

    servidor.comando = comando
    logs = _rodar(tmp_path, "ct")

    assert "  [AVISO] Não consegui contar os clientes pelo status do RCON (rcon caiu)." in logs
    assert "  [AVISO] Clientes após reconciliação: não medidos (status sem clientes ou com erro)." in logs
    assert not any("Recompondo" in linha for linha in logs)
    assert not any("Times prontos" in c for c in servidor.rcon)
    assert "mp_ignore_round_win_conditions 0" in servidor.rcon  # o finally rodou

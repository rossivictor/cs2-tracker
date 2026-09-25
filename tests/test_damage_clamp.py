#!/usr/bin/env python3
"""
Testes de parser.clamp_damage_health — o dano gravado tem que ser a vida
REMOVIDA, não o dano bruto que a fonte reporta.

Descoberto cruzando os contadores do engine (CSMatchStats_t) contra a nossa
soma de player_hurt numa partida real em 23/09/2026: 1614 contra 1370 em 10
rounds. A prova estava numa kill que registrou 136 de dano num jogador que
tem no máximo 100 de vida. Como HLTV e Leetify usam o número capado, o ADR
do tracker nunca foi comparável com as referências.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parser import MAX_HEALTH, clamp_damage_health


def _dano(round_num, tick, victim, dmg, attacker="can1sh"):
    """Tupla de damages no formato das duas ingestões (12 campos)."""
    return (round_num, tick, attacker, None, victim, None,
            "ak47", "1", dmg, 0, 1, 0)


def _cortado(linhas):
    return [r[8] for r in clamp_damage_health(linhas)]


def _bruto(linhas):
    return [r[-1] for r in clamp_damage_health(linhas)]


def test_tiro_que_mata_nao_conta_mais_que_a_vida_restante():
    """O caso real: 136 de dano num alvo com 100 de vida."""
    assert _cortado([_dano(1, 500, "bot", 136)]) == [100]


def test_valor_bruto_fica_guardado():
    assert _bruto([_dano(1, 500, "bot", 136)]) == [136]


def test_dano_normal_passa_intacto():
    linhas = [_dano(1, 500, "bot", 27), _dano(1, 600, "bot", 35)]
    assert _cortado(linhas) == [27, 35]


def test_soma_de_uma_vida_nunca_passa_de_100():
    linhas = [_dano(1, 100, "bot", 40), _dano(1, 200, "bot", 40),
              _dano(1, 300, "bot", 40)]
    assert _cortado(linhas) == [40, 40, 20]
    assert sum(_cortado(linhas)) == MAX_HEALTH


def test_dano_depois_da_vitima_zerar_conta_zero():
    linhas = [_dano(1, 100, "bot", 100), _dano(1, 200, "bot", 50)]
    assert _cortado(linhas) == [100, 0]


def test_o_teto_e_por_vitima():
    linhas = [_dano(1, 100, "bot_a", 80), _dano(1, 150, "bot_b", 80)]
    assert _cortado(linhas) == [80, 80]


def test_o_teto_reinicia_a_cada_round():
    linhas = [_dano(1, 100, "bot", 100), _dano(2, 100, "bot", 100)]
    assert _cortado(linhas) == [100, 100]


def test_o_acumulado_atravessa_atacantes():
    """Se um bot já tirou 80, o seu tiro de 100 vale 20. Sem isso o ADR
    continuaria inflado nos alvos que o time enfraqueceu antes."""
    linhas = [_dano(1, 100, "alvo", 80, attacker="Bot Kaiser"),
              _dano(1, 200, "alvo", 100, attacker="can1sh")]
    assert _cortado(linhas) == [80, 20]


def test_processa_por_tique_e_nao_pela_ordem_de_chegada():
    """As linhas chegam na ordem do arquivo, que não é garantidamente a
    ordem cronológica — o corte tem que seguir o tique."""
    fora_de_ordem = [_dano(1, 900, "alvo", 100), _dano(1, 100, "alvo", 30)]
    assert _cortado(fora_de_ordem) == [70, 30]


def test_preserva_a_ordem_original_das_linhas():
    """Só os valores mudam; quem chamou depende da posição pra dar INSERT."""
    linhas = [_dano(1, 900, "alvo", 10), _dano(1, 100, "alvo", 20)]
    saida = clamp_damage_health(linhas)
    assert [r[1] for r in saida] == [900, 100]


def test_dano_nulo_nao_explode():
    assert _cortado([_dano(1, 100, "bot", None)]) == [0]


def test_funciona_com_a_tupla_de_13_campos():
    """clamp roda DEPOIS de mark_post_mortem, que acrescenta post_mortem."""
    linha = _dano(1, 500, "bot", 136) + (1,)
    (saida,) = clamp_damage_health([linha])
    assert saida[8] == 100      # dano cortado
    assert saida[12] == 1       # post_mortem preservado na posição
    assert saida[-1] == 136     # bruto no fim


def test_idempotente():
    """Rodar de novo sobre o já cortado não corta mais nada."""
    linhas = [_dano(1, 100, "bot", 136)]
    uma = clamp_damage_health(linhas)
    duas = clamp_damage_health([r[:-1] for r in uma])
    assert [r[8] for r in duas] == [100]


def test_lista_vazia():
    assert clamp_damage_health([]) == []


# --------------------------------------------------------------------------- #
# Vítima desconhecida (fonte demo)
# --------------------------------------------------------------------------- #

def _sem_vitima(round_num, tick, dmg):
    return (round_num, tick, None, None, None, None, "glock", "1", dmg, 0, 1, 0)


def test_linha_sem_vitima_nao_e_cortada():
    """Na fonte demo o awpy não resolve a vítima em ~93% das linhas. Cortar
    por (round, None) juntaria todo mundo num balde de 100 e derrubaria a
    partida em 85% — medido no banco real antes de aplicar."""
    linhas = [_sem_vitima(1, 100, 80), _sem_vitima(1, 200, 90),
              _sem_vitima(1, 300, 70)]
    assert _cortado(linhas) == [80, 90, 70]


def test_vitima_desconhecida_nao_contamina_a_conhecida():
    linhas = [_sem_vitima(1, 100, 90), _dano(1, 200, "bot", 60),
              _dano(1, 300, "bot", 60)]
    assert _cortado(linhas) == [90, 60, 40]


def test_steamid_tem_precedencia_sobre_o_nome():
    """Mesmo jogador com nick diferente em duas linhas continua sendo um só."""
    a = (1, 100, "can1sh", None, "NickVelho", "7656119800", "ak47", "1", 70, 0, 1, 0)
    b = (1, 200, "can1sh", None, "NickNovo", "7656119800", "ak47", "1", 70, 0, 1, 0)
    assert _cortado([a, b]) == [70, 30]

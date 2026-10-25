#!/usr/bin/env python3
"""
Órfão real preservado, log em arquivo e aviso de candidato (card P1.1).

A cauda é a real: tests/fixtures/captura/current.jsonl (e a cópia em
tests/fixtures/logs/eventos/) é o que sobra no current.jsonl depois de uma
partida arquivada, só snapshot, round_stats e round_officially_ended. Os
eventos de round vêm do events_44_map0.jsonl (com BOM) e do events_59_map0.
Os órfãos falsos do P1.1d (orfao_falso_83/87.jsonl) são caudas reais com a
morte de pós-jogo pelo world, anonimizadas como as do T1.3.

Tudo em tmp_path, com start_match.ROOT trocado por ele: nada de
docker/events-live/, data/ ou logs/ de verdade, nem processo, Docker ou RCON
(as funções que falariam com o servidor viram fakes que só anotam).
"""
import itertools
import json
import re
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tools"))

import evidencia_partida as ep  # noqa: E402
import start_match  # noqa: E402

CAPTURA = RAIZ / "tests" / "fixtures" / "captura"
CAUDA_REAL = CAPTURA / "current.jsonl"
CAUDA_REAL_2 = RAIZ / "tests" / "fixtures" / "logs" / "eventos" / "current.jsonl"
PARTIDA_44 = CAPTURA / "events_44_map0.jsonl"  # começa com BOM
PARTIDA_59 = CAPTURA / "events_59_map0.jsonl"
NOME_ORFAO = re.compile(r"^orphan_\d{8}T\d{6}Z(?:-\d+)?\.jsonl$")


def _primeira_linha(caminho: Path, tipo: str, world: bool = False) -> bytes:
    """A linha crua do primeiro evento `tipo`, sem BOM: um evento de verdade
    da partida 44, não um escrito para o teste. Pula a morte pelo world, a
    não ser com world=True: a 1ª player_death da 44 é uma (round 2, atacante
    = vítima) e, sozinha na cauda, é a morte de pós-jogo do P1.1d."""
    for linha in caminho.read_bytes().removeprefix(b"\xef\xbb\xbf").splitlines(keepends=True):
        if f'"type":"{tipo}"'.encode() in linha and (world or b'"weapon":"world"' not in linha):
            return linha
    raise AssertionError(f"{tipo} não está em {caminho.name}")


def _orfaos(pasta: Path):
    return sorted(p.name for p in pasta.glob("orphan_*"))


# ------------------------------------------------------------------ órfão

@pytest.mark.parametrize("cauda", [CAUDA_REAL, CAUDA_REAL_2], ids=["captura", "logs"])
def test_cauda_real_so_de_snapshot_nao_vira_orfao(tmp_path, cauda):
    # A fixture tem 44/43 snapshots, 1 round_stats e 1 round_officially_ended.
    tipos = {json.loads(l)["type"] for l in cauda.read_text(encoding="utf-8-sig").splitlines()}
    assert tipos == {"snapshot", "round_stats", "round_officially_ended"}
    current = tmp_path / "current.jsonl"
    current.write_bytes(cauda.read_bytes())
    linhas = []

    assert start_match.preservar_orfao(tmp_path, log=linhas.append) is None

    # Descartada como hoje: o arquivo fica para o plugin truncar, intacto.
    assert current.read_bytes() == cauda.read_bytes()
    assert _orfaos(tmp_path) == []
    assert linhas == []


@pytest.mark.parametrize("tipo", ["round_start", "player_death", "player_hurt"])
def test_um_evento_de_round_depois_da_cauda_vira_orfao(tmp_path, tipo):
    conteudo = CAUDA_REAL.read_bytes() + _primeira_linha(PARTIDA_44, tipo)
    (tmp_path / "current.jsonl").write_bytes(conteudo)
    linhas = []

    destino = start_match.preservar_orfao(tmp_path, log=linhas.append)

    assert destino is not None and NOME_ORFAO.match(destino.name), destino
    assert not (tmp_path / "current.jsonl").exists()
    assert destino.read_bytes() == conteudo  # rename: byte a byte, nada perdido
    assert _orfaos(tmp_path) == [destino.name]
    assert linhas == [f"[CAPTURA] current.jsonl tinha rounds sem arquivar: "
                      f"preservado em {destino.name}."]


@pytest.mark.parametrize("tipo", ["round_end", "bomb_planted", "bomb_defused"])
def test_outros_eventos_sem_round_start_morte_ou_dano_nao_viram_orfao(tmp_path, tipo):
    # O critério pede round_start, player_death ou player_hurt: os demais
    # eventos do plugin, sozinhos na cauda, não bastam.
    conteudo = CAUDA_REAL.read_bytes() + _primeira_linha(PARTIDA_44, tipo)
    (tmp_path / "current.jsonl").write_bytes(conteudo)
    assert start_match.preservar_orfao(tmp_path, log=lambda _: None) is None
    assert _orfaos(tmp_path) == []


@pytest.mark.parametrize("partida", [PARTIDA_44, PARTIDA_59], ids=["44_com_bom", "59"])
def test_partida_inteira_nao_arquivada_vira_orfao(tmp_path, partida):
    (tmp_path / "current.jsonl").write_bytes(partida.read_bytes())
    destino = start_match.preservar_orfao(tmp_path, log=lambda _: None)
    assert destino is not None and destino.read_bytes() == partida.read_bytes()


def test_sem_current_ou_vazio_nao_faz_nada(tmp_path):
    assert start_match.preservar_orfao(tmp_path / "nao-existe", log=lambda _: None) is None
    (tmp_path / "current.jsonl").write_bytes(b"")
    assert start_match.preservar_orfao(tmp_path, log=lambda _: None) is None
    assert (tmp_path / "current.jsonl").exists() and _orfaos(tmp_path) == []


def test_orfao_com_o_mesmo_nome_nunca_e_sobrescrito(tmp_path, monkeypatch):
    monkeypatch.setattr(start_match, "_carimbo_utc", lambda: "20261004T210000Z")
    anterior = tmp_path / "orphan_20261004T210000Z.jsonl"
    anterior.write_bytes(b"orfao anterior\n")
    conteudo = _primeira_linha(PARTIDA_44, "round_start")
    (tmp_path / "current.jsonl").write_bytes(conteudo)

    destino = start_match.preservar_orfao(tmp_path, log=lambda _: None)

    assert destino.name == "orphan_20261004T210000Z-2.jsonl"
    assert destino.read_bytes() == conteudo
    assert anterior.read_bytes() == b"orfao anterior\n"


# ------------------------------------------- morte de pós-jogo (P1.1d)
# Os dois órfãos falsos reais, anonimizados como no T1.3: a cauda do round 17
# da partida 83 (orphan_20261015T164958Z) e a do round 25 da 87
# (orphan_20261019T185248Z). Cada um tem uma player_death pelo world em que o
# humano é atacante e vítima, e nenhum round_start.

@pytest.mark.parametrize("nome, linhas, snapshots, round_num", [
    ("orfao_falso_83.jsonl", 16, 13, 17),
    ("orfao_falso_87.jsonl", 15, 12, 25),
], ids=["83", "87"])
def test_orfao_falso_real_e_cauda_e_fica_intacto(tmp_path, nome, linhas, snapshots, round_num):
    fixture = CAPTURA / nome
    eventos = [json.loads(l) for l in fixture.read_text(encoding="utf-8").splitlines()]
    # Gabarito contado à mão na cópia do backup, antes da troca de ids e nomes.
    assert len(eventos) == linhas
    assert [e["type"] for e in eventos].count("snapshot") == snapshots
    assert sorted(e["type"] for e in eventos if e["type"] != "snapshot") == [
        "player_death", "round_officially_ended", "round_stats"]
    assert {e["round_num"] for e in eventos} == {round_num}
    [morte] = [e for e in eventos if e["type"] == "player_death"]
    assert morte["weapon"] == "world"
    assert morte["attacker_steamid"] == morte["victim_steamid"] == "76561190000000001"
    current = tmp_path / "current.jsonl"
    current.write_bytes(fixture.read_bytes())
    linhas_log = []

    assert start_match.preservar_orfao(tmp_path, log=linhas_log.append) is None

    assert current.read_bytes() == fixture.read_bytes()  # fica para o plugin truncar
    assert _orfaos(tmp_path) == [] and linhas_log == []


def _morte_de_pos_jogo() -> bytes:
    return _primeira_linha(CAPTURA / "orfao_falso_83.jsonl", "player_death", world=True)


def test_morte_pelo_world_da_partida_44_so_e_cauda_sem_o_round_start(tmp_path):
    # O mesmo formato num round de verdade (partida 44, round 2): sozinho na
    # cauda é cauda; com o round_start do round, é órfão.
    morte = _primeira_linha(PARTIDA_44, "player_death", world=True)
    assert json.loads(morte)["round_num"] == 2 and b'"weapon":"world"' in morte
    (tmp_path / "current.jsonl").write_bytes(CAUDA_REAL.read_bytes() + morte)
    assert start_match.preservar_orfao(tmp_path, log=lambda _: None) is None
    conteudo = CAUDA_REAL.read_bytes() + _primeira_linha(PARTIDA_44, "round_start") + morte
    (tmp_path / "current.jsonl").write_bytes(conteudo)
    assert start_match.preservar_orfao(tmp_path, log=lambda _: None) is not None


def test_cauda_real_do_t13_com_a_morte_de_pos_jogo_nao_vira_orfao(tmp_path):
    conteudo = CAUDA_REAL.read_bytes() + _morte_de_pos_jogo()
    (tmp_path / "current.jsonl").write_bytes(conteudo)
    assert start_match.preservar_orfao(tmp_path, log=lambda _: None) is None
    assert (tmp_path / "current.jsonl").read_bytes() == conteudo
    assert _orfaos(tmp_path) == []


def _variante(**troca) -> bytes:
    evento = json.loads(_morte_de_pos_jogo())
    evento.update(troca)
    return (json.dumps(evento, separators=(",", ":")) + "\n").encode()


@pytest.mark.parametrize("extra", [
    pytest.param(lambda: _primeira_linha(PARTIDA_44, "round_start") + _morte_de_pos_jogo(),
                 id="com_round_start"),
    pytest.param(lambda: _morte_de_pos_jogo() + _primeira_linha(PARTIDA_44, "player_hurt"),
                 id="com_dano"),
    pytest.param(lambda: _variante(attacker_steamid="76561190000000002"), id="atacante_outro"),
    pytest.param(lambda: _variante(weapon="hegrenade"), id="arma_nao_world"),
    pytest.param(lambda: _variante(attacker_steamid="", victim_steamid=""), id="sem_steamid"),
    pytest.param(lambda: _primeira_linha(PARTIDA_44, "player_death"), id="morte_da_partida_44"),
])
def test_fora_da_morte_de_pos_jogo_continua_virando_orfao(tmp_path, extra):
    conteudo = CAUDA_REAL.read_bytes() + extra()
    (tmp_path / "current.jsonl").write_bytes(conteudo)
    destino = start_match.preservar_orfao(tmp_path, log=lambda _: None)
    assert destino is not None and NOME_ORFAO.match(destino.name)
    assert destino.read_bytes() == conteudo


# A regra num lugar só (critério 2): o start_match não importa a ferramenta
# do G7 nem ela o caminho de jogo, então as duas implementações provam aqui
# que dão a mesma resposta. Domínio: a cauda (snapshot, round_stats,
# round_officially_ended) mais qualquer combinação dos eventos de partida do
# P1.1. Fora dele as duas divergem de propósito (round_end, bomba e afins
# sozinhos; contrato do JSONL, §7).
_PECAS = {
    "round_start": lambda: _primeira_linha(PARTIDA_44, "round_start"),
    "dano": lambda: _primeira_linha(PARTIDA_44, "player_hurt"),
    "morte_partida": lambda: _primeira_linha(PARTIDA_44, "player_death"),
    "pos_jogo": _morte_de_pos_jogo,
    "world_de_outro": lambda: _variante(attacker_steamid="76561190000000002"),
    "suicidio_granada": lambda: _variante(weapon="hegrenade"),
}
_COMBINACOES = [c for n in range(len(_PECAS) + 1) for c in itertools.combinations(_PECAS, n)]


def _concordam(tmp_path, conteudo: bytes) -> bool:
    pasta = tmp_path / "ep"
    pasta.mkdir()
    (pasta / "current.jsonl").write_bytes(conteudo)
    do_g7 = ep.analisar_current(pasta)["estado"] == "com_rounds"
    do_orfao = start_match.preservar_orfao(pasta, log=lambda _: None) is not None
    assert do_g7 == do_orfao
    return do_orfao


@pytest.mark.parametrize("pecas", _COMBINACOES, ids=lambda c: "+".join(c) or "so_cauda")
def test_preservar_orfao_concorda_com_analisar_current(tmp_path, pecas):
    conteudo = CAUDA_REAL.read_bytes() + b"".join(_PECAS[p]() for p in pecas)
    # Gabarito à mão: só a morte de pós-jogo (sozinha) some na cauda.
    assert _concordam(tmp_path, conteudo) == (set(pecas) - {"pos_jogo"} != set())


@pytest.mark.parametrize("fixture", [CAUDA_REAL, CAUDA_REAL_2, CAPTURA / "orfao_falso_83.jsonl",
                                     CAPTURA / "orfao_falso_87.jsonl", PARTIDA_44, PARTIDA_59],
                         ids=["cauda_t13", "cauda_logs", "83", "87", "partida_44", "partida_59"])
def test_preservar_orfao_concorda_com_analisar_current_nos_arquivos_reais(tmp_path, fixture):
    esperado = fixture in (PARTIDA_44, PARTIDA_59)
    assert _concordam(tmp_path, fixture.read_bytes()) is esperado


# ---------------------------------------------------- run_match com fakes

class Parar(Exception):
    """Interrompe o run_match logo depois do loadmatch."""


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    """ROOT em tmp_path, e o que falaria com o servidor só anota o estado da
    pasta de eventos no momento da chamada."""
    eventos = tmp_path / "docker" / "events-live"
    eventos.mkdir(parents=True)
    estado = types.SimpleNamespace(eventos=eventos, chamadas=[], logs=[])

    def foto(nome):
        estado.chamadas.append((nome, (eventos / "current.jsonl").exists(), _orfaos(eventos)))

    def rcon_run(host, port, password, command, timeout=5):
        if command.startswith("matchzy_loadmatch"):
            foto("loadmatch")
            raise Parar
        return ""

    monkeypatch.setattr(start_match, "ROOT", tmp_path)
    monkeypatch.setattr(start_match, "EVENTS_LIVE_DIR", "./docker/events-live")
    monkeypatch.setattr(start_match, "read_max_players", lambda _: None)
    monkeypatch.setattr(start_match, "docker_fora_do_ar", lambda: None)  # P1.1c: daemon no ar
    monkeypatch.setattr(start_match, "container_running", lambda _: False)
    monkeypatch.setattr(start_match, "compose_up", lambda *_a, **_k: foto("compose_up"))
    monkeypatch.setattr(start_match, "wait_for_rcon", lambda *_a, **_k: None)
    monkeypatch.setattr(start_match, "rcon_run", rcon_run)
    return estado


def _rodar(mundo, **extra):
    with pytest.raises(Parar):
        start_match.run_match(
            container_name="cs2-teste", match_config="match_config.spike.json",
            compose_file="docker-compose.yml", rcon_host="127.0.0.1", rcon_port=27015,
            rcon_password="fake", team_size=5, boot_timeout=1, skip_up=False,
            player=None, log=mundo.logs.append, **extra)


def _log_em_arquivo(tmp_path: Path) -> list:
    arquivos = sorted((tmp_path / "logs" / "partidas").glob("partida_*.log"))
    assert len(arquivos) == 1, arquivos
    assert re.match(r"^partida_\d{8}T\d{6}Z\.log$", arquivos[0].name)
    # Cada linha vem com HH:MM:SS na frente.
    return [l[9:] for l in arquivos[0].read_text(encoding="utf-8").splitlines()]


def test_run_match_preserva_o_orfao_antes_do_compose_up_e_do_loadmatch(mundo):
    conteudo = CAUDA_REAL.read_bytes() + _primeira_linha(PARTIDA_44, "player_death")
    (mundo.eventos / "current.jsonl").write_bytes(conteudo)

    _rodar(mundo)

    [orfao] = _orfaos(mundo.eventos)
    assert mundo.chamadas == [("compose_up", False, [orfao]), ("loadmatch", False, [orfao])]
    assert (mundo.eventos / orfao).read_bytes() == conteudo


def test_run_match_com_a_cauda_real_nao_cria_orfao(mundo):
    (mundo.eventos / "current.jsonl").write_bytes(CAUDA_REAL.read_bytes())
    _rodar(mundo)
    assert mundo.chamadas == [("compose_up", True, []), ("loadmatch", True, [])]
    assert (mundo.eventos / "current.jsonl").read_bytes() == CAUDA_REAL.read_bytes()


def test_run_match_com_a_morte_de_pos_jogo_real_nao_cria_orfao(mundo):
    # P1.1d: a subida seguinte à partida 87 com o current.jsonl que ela deixou.
    fixture = CAPTURA / "orfao_falso_87.jsonl"
    (mundo.eventos / "current.jsonl").write_bytes(fixture.read_bytes())
    _rodar(mundo)
    assert mundo.chamadas == [("compose_up", True, []), ("loadmatch", True, [])]
    assert (mundo.eventos / "current.jsonl").read_bytes() == fixture.read_bytes()
    assert not any("preservado em" in l for l in mundo.logs)


def test_run_match_grava_o_log_em_logs_partidas(mundo, tmp_path):
    _rodar(mundo)
    no_arquivo = _log_em_arquivo(tmp_path)
    assert no_arquivo == mundo.logs  # tudo o que foi para a tela, na ordem
    assert "[MATCHZY] Carregando runtime/match_config.spike.json..." in no_arquivo


def test_run_match_leva_a_saida_do_watcher_ao_arquivo(mundo, tmp_path, monkeypatch):
    def start_watcher(container, player, config, on_output=None, log=print):
        on_output("[PIPELINE] Eventos do mapa 0 arquivados em events_75_map0.jsonl")
        return types.SimpleNamespace()

    monkeypatch.setattr(start_match, "start_watcher", start_watcher)
    na_tela = []
    with pytest.raises(Parar):
        start_match.run_match(
            container_name="cs2-teste", match_config="match_config.spike.json",
            compose_file="docker-compose.yml", rcon_host="127.0.0.1", rcon_port=27015,
            rcon_password="fake", team_size=5, boot_timeout=1, skip_up=True,
            player="Jogador", watcher_output=na_tela.append, log=mundo.logs.append)
    assert na_tela == ["[PIPELINE] Eventos do mapa 0 arquivados em events_75_map0.jsonl"]
    assert na_tela[0] in _log_em_arquivo(tmp_path)


def test_falha_ao_gravar_o_log_nao_para_a_partida(mundo, tmp_path):
    (tmp_path / "logs").write_text("um arquivo no lugar da pasta", encoding="utf-8")

    _rodar(mundo)  # chegou ao loadmatch mesmo assim

    assert [nome for nome, *_ in mundo.chamadas] == ["compose_up", "loadmatch"]
    avisos = [l for l in mundo.logs if l.startswith("[AVISO] Não consegui gravar o log")]
    assert len(avisos) == 1, mundo.logs  # um aviso só, não um por linha
    assert "[MATCHZY] Carregando runtime/match_config.spike.json..." in mundo.logs


def test_sink_com_arquivo_engole_qualquer_erro_de_escrita(tmp_path, monkeypatch):
    def quebra(*_a, **_k):
        raise PermissionError("disco cheio")

    monkeypatch.setattr(Path, "open", quebra)
    tela = []
    log = start_match.sink_com_arquivo(tela.append, tmp_path, "partida.log")
    log("linha 1")
    log("linha 2")
    assert tela[0] == "linha 1"
    assert tela[1].startswith("[AVISO] Não consegui gravar o log") and "disco cheio" in tela[1]
    assert tela[2] == "linha 2" and len(tela) == 3


# -------------------------------------------------------------- candidato

def test_com_candidato_json_imprime_a_linha_info(mundo, tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "candidato.json").write_text(json.dumps({
        "tag": "candidato-8", "commit": "0123456789abcdef0123456789abcdef01234567",
        "nota": "P1.1 · PR #62", "plugin_captura": "ab" * 32,
        "marcado_em": "2026-10-12T15:30:00"}), encoding="utf-8")

    _rodar(mundo)

    info = [l for l in mundo.logs if l.startswith("[INFO]")]
    assert info == ["[INFO] Candidato em teste: candidato-8 (P1.1 · PR #62, commit 012345678). "
                    "Esta partida valida esse degrau; para desfazer: tools/jogavel.py voltar."]
    assert info[0] in _log_em_arquivo(tmp_path)


def test_sem_candidato_json_nao_imprime_info(mundo):
    _rodar(mundo)
    assert [l for l in mundo.logs if l.startswith("[INFO]")] == []


def test_candidato_json_ilegivel_nao_para_a_partida(mundo, tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "candidato.json").write_text("{quebrado", encoding="utf-8")
    _rodar(mundo)
    assert [l for l in mundo.logs if l.startswith("[INFO]")] == [
        "[INFO] Candidato em teste: ? (data/candidato.json ilegível). "
        "Esta partida valida esse degrau; para desfazer: tools/jogavel.py voltar."]

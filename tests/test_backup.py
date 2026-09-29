#!/usr/bin/env python3
"""
Testes de tools/backup.py (card B0.6). A origem é um checkout falso em
tmp_path, com banco SQLite pequeno, captura, perfil, logs, board e plugins
fictícios; o preflight é injetado. Nada do checkout principal é lido.
"""
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import backup  # noqa: E402
from preflight import JANELA, JOGANDO, LIVRE, Resultado  # noqa: E402

AGORA = datetime(2026, 9, 28, 21, 7)
MTIME = 1_700_000_000  # mtime antigo: prova que nada na origem foi tocado
SHA_ABC = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"  # sha256(b"abc")


def _escrever(arquivo: Path, conteudo: bytes) -> None:
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_bytes(conteudo)


def _banco(arquivo: Path, partidas: int = 3, com_matches: bool = True) -> None:
    con = sqlite3.connect(arquivo)
    if com_matches:
        con.execute("CREATE TABLE matches (id INTEGER PRIMARY KEY, mapa TEXT)")
        con.executemany("INSERT INTO matches (mapa) VALUES (?)",
                        [("de_mirage",)] * partidas)
    else:
        con.execute("CREATE TABLE outra (x)")
    con.commit()
    con.close()


@pytest.fixture
def origem(tmp_path):
    raiz = tmp_path / "checkout"
    (raiz / ".git").mkdir(parents=True)
    _banco(raiz / "cs2_tracker.db")
    _escrever(raiz / "docker/events-live/current.jsonl", b'{"type":"snapshot"}\n')
    _escrever(raiz / "docker/events-live/events_1_map1.jsonl", b'{"type":"round_end"}\n')
    _escrever(raiz / "data/profile.json", b'{"nick": "jogador-teste"}')
    _escrever(raiz / "logs/janelas/2026-09-27.md", b"registro\n")
    _escrever(raiz / "docs/board-cs2/Board.md", b"# board\n")
    _escrever(raiz / "docker/plugins/PluginA/PluginA.dll", b"abc")
    _escrever(raiz / "docker/plugins/PluginA/lang/pt.json", b"")
    (raiz / "docker/plugins/Vazio").mkdir()
    for arquivo in raiz.rglob("*"):
        if arquivo.is_file():
            os.utime(arquivo, (MTIME, MTIME))
    return raiz


def _preflight(codigo):
    chamadas = []

    def consultar(raiz):
        chamadas.append(raiz)
        return Resultado(codigo, f"teste {codigo}")
    consultar.chamadas = chamadas
    return consultar


def _foto(raiz: Path) -> dict:
    """Conteúdo e mtime de tudo na origem (inclusive o que surgir)."""
    return {p.relative_to(raiz).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in raiz.rglob("*") if p.is_file()}


def _rodar(origem, destino, codigo=LIVRE, *extra):
    return backup.main(["--origem", str(origem), "--destino", str(destino), *extra],
                       consultar=_preflight(codigo), agora=AGORA)


# ------------------------------------------------------------- banco

def test_banco_copiado_com_integridade_e_contagem_de_matches(origem, tmp_path):
    destino = tmp_path / "bk"
    assert _rodar(origem, destino) == 0
    m = json.loads((destino / "MANIFESTO.json").read_text(encoding="utf-8"))
    assert m["banco"]["status"] == "copiado"
    assert m["banco"]["integrity_check"] == ["ok"]
    assert m["banco"]["matches"] == 3
    con = sqlite3.connect(destino / "cs2_tracker.backup.db")
    assert con.execute("SELECT COUNT(*), MIN(mapa) FROM matches").fetchone() == (3, "de_mirage")
    con.close()


def test_origem_do_banco_e_aberta_em_mode_ro(origem, tmp_path, monkeypatch):
    abertos = []
    connect = sqlite3.connect

    def espiao(alvo, *args, **kwargs):
        abertos.append((str(alvo), kwargs.get("uri", False)))
        return connect(alvo, *args, **kwargs)
    monkeypatch.setattr(backup.sqlite3, "connect", espiao)
    assert _rodar(origem, tmp_path / "bk") == 0
    da_origem = [a for a in abertos if "/checkout/cs2_tracker.db" in a[0].replace("\\", "/")]
    assert da_origem == [((origem / "cs2_tracker.db").resolve().as_uri() + "?mode=ro", True)]


def test_banco_sem_tabela_matches_fica_anotado_sem_quebrar(origem, tmp_path):
    (origem / "cs2_tracker.db").unlink()
    _banco(origem / "cs2_tracker.db", com_matches=False)
    destino = tmp_path / "bk"
    assert _rodar(origem, destino) == 0
    banco = json.loads((destino / "MANIFESTO.json").read_text(encoding="utf-8"))["banco"]
    assert banco["matches"] is None
    assert banco["observacao"] == "tabela matches ausente"
    assert "matches sem tabela" in (destino / "MANIFESTO.txt").read_text(encoding="utf-8")


def test_banco_ausente_e_problema_mas_o_resto_e_copiado(origem, tmp_path):
    (origem / "cs2_tracker.db").unlink()
    destino = tmp_path / "bk"
    assert _rodar(origem, destino) == 1
    m = json.loads((destino / "MANIFESTO.json").read_text(encoding="utf-8"))
    assert m["banco"]["status"] == "ausente"
    assert m["problemas"] == ["cs2_tracker.db: ausente"]
    assert (destino / "data/profile.json").is_file()


# ------------------------------------------------------ pastas e plugins

def test_copia_events_live_perfil_logs_e_board(origem, tmp_path):
    destino = tmp_path / "bk"
    assert _rodar(origem, destino) == 0
    for rel in ("docker/events-live/current.jsonl", "docker/events-live/events_1_map1.jsonl",
                "data/profile.json", "logs/janelas/2026-09-27.md", "docs/board-cs2/Board.md"):
        assert (destino / rel).read_bytes() == (origem / rel).read_bytes(), rel
    m = json.loads((destino / "MANIFESTO.json").read_text(encoding="utf-8"))
    assert [(p["origem"], p["status"], p["arquivos"]) for p in m["pastas"]] == [
        ("docker/events-live", "copiado", 2), ("logs", "copiado", 1),
        ("docs/board-cs2", "copiado", 1)]


def test_pasta_ausente_e_pulada_e_dita_no_manifesto(origem, tmp_path):
    (origem / "docs/board-cs2/Board.md").unlink()
    (origem / "docs/board-cs2").rmdir()
    destino = tmp_path / "bk"
    assert _rodar(origem, destino) == 0
    m = json.loads((destino / "MANIFESTO.json").read_text(encoding="utf-8"))
    assert {"origem": "docs/board-cs2", "status": "ausente"} in m["pastas"]
    assert "docs/board-cs2: ausente" in (destino / "MANIFESTO.txt").read_text(encoding="utf-8")


def test_plugins_viram_manifesto_sha256_sem_copiar_binario(origem, tmp_path):
    destino = tmp_path / "bk"
    assert _rodar(origem, destino) == 0
    assert not (destino / "docker/plugins").exists()
    assert not list(destino.rglob("*.dll"))
    plugins = json.loads((destino / "MANIFESTO.json").read_text(encoding="utf-8"))["plugins"]
    assert plugins == {
        "PluginA": [
            {"arquivo": "PluginA.dll", "bytes": 3, "sha256": SHA_ABC},
            {"arquivo": "lang/pt.json", "bytes": 0, "sha256":
             "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
        ],
        "Vazio": [],
    }
    linhas = (destino / "plugins/PluginA.sha256").read_text(encoding="utf-8").splitlines()
    assert linhas[0] == f"{SHA_ABC}  PluginA.dll"


# ------------------------------------------------------------- preflight

def test_recusa_com_preflight_3_sem_criar_destino(origem, tmp_path, capsys):
    destino = tmp_path / "bk"
    consultar = _preflight(JOGANDO)
    codigo = backup.main(["--origem", str(origem), "--destino", str(destino)],
                         consultar=consultar, agora=AGORA)
    assert codigo == 3
    assert consultar.chamadas == [origem]
    assert not destino.exists()
    assert "backup recusado" in capsys.readouterr().err


@pytest.mark.parametrize("codigo", [1, 2, 5])
def test_codigo_desconhecido_do_preflight_conta_como_3(origem, tmp_path, codigo):
    assert _rodar(origem, tmp_path / "bk", codigo) == 3
    assert not (tmp_path / "bk").exists()


@pytest.mark.parametrize("codigo", [LIVRE, JANELA])
def test_passa_com_preflight_0_e_com_janela_aberta(origem, tmp_path, codigo):
    assert _rodar(origem, tmp_path / "bk", codigo) == 0
    m = json.loads((tmp_path / "bk/MANIFESTO.json").read_text(encoding="utf-8"))
    assert m["preflight"] == {"codigo": codigo, "motivo": f"teste {codigo}"}
    assert m["leitura_com_jogo"] is False


def test_leitura_com_jogo_passa_com_preflight_3_e_fica_registrada(origem, tmp_path):
    destino = tmp_path / "bk"
    assert _rodar(origem, destino, JOGANDO, "--leitura-com-jogo") == 0
    m = json.loads((destino / "MANIFESTO.json").read_text(encoding="utf-8"))
    assert m["leitura_com_jogo"] is True
    assert m["preflight"]["codigo"] == 3
    assert m["banco"]["matches"] == 3


def test_preflight_de_verdade_ve_current_jsonl_recente_como_3(origem):
    os.utime(origem / "docker/events-live/current.jsonl")  # mexido agora
    resultado = backup.consultar_preflight(origem, listar=lambda: [])
    assert resultado.codigo == JOGANDO
    assert "current.jsonl" in resultado.motivo


def test_preflight_de_verdade_devolve_0_com_origem_parada(origem):
    assert backup.consultar_preflight(origem, listar=lambda: []).codigo == LIVRE


# ------------------------------------------------------------- origem

def test_origem_fica_intacta_conteudo_mtime_e_nenhum_arquivo_novo(origem, tmp_path):
    antes = _foto(origem)
    assert _rodar(origem, tmp_path / "bk", JOGANDO, "--leitura-com-jogo") == 0
    assert _foto(origem) == antes
    # o mtime antigo foi preservado na cópia (copy2), e a origem não ganhou journal
    assert (tmp_path / "bk/data/profile.json").stat().st_mtime == MTIME
    assert not list(origem.glob("cs2_tracker.db-*"))


# ------------------------------------------------------ uso e destino

def test_destino_existente_e_recusado_sem_sobrescrever(origem, tmp_path, capsys):
    destino = tmp_path / "bk"
    destino.mkdir()
    (destino / "antigo.txt").write_text("não mexer", encoding="utf-8")
    consultar = _preflight(LIVRE)
    assert backup.main(["--origem", str(origem), "--destino", str(destino)],
                       consultar=consultar, agora=AGORA) == 2
    assert [p.name for p in destino.iterdir()] == ["antigo.txt"]
    assert consultar.chamadas == []
    assert "já existe" in capsys.readouterr().err


def test_destino_dentro_da_origem_e_recusado(origem, tmp_path):
    assert _rodar(origem, origem / "backups" / "hoje") == 2
    assert not (origem / "backups").exists()


def test_origem_inexistente_e_erro_de_uso(tmp_path):
    assert _rodar(tmp_path / "nao-existe", tmp_path / "bk") == 2


def test_argumento_desconhecido_sai_com_2(capsys):
    with pytest.raises(SystemExit) as saida:
        backup.main(["--sobrescrever"], consultar=_preflight(LIVRE))
    assert saida.value.code == 2


def test_destino_padrao_por_data_e_hora():
    assert backup.destino_padrao(AGORA) == Path(
        "C:/Users/Victor/cs2-tracker-backups/2026-09-28/backup-2107")

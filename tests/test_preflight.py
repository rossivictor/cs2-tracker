#!/usr/bin/env python3
"""
Testes de tools/preflight.py (card B0.4): 0 livre, 3 Victor jogando, 4 janela
aberta, com o 3 tendo precedência e qualquer falha de detecção virando 3.

Tudo é simulado: a lista de processos é injetada, o executor de subprocess é
falso e o checkout é um diretório em tmp_path. Nenhum processo real é
listado e nada do checkout principal é consultado.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import preflight  # noqa: E402
from preflight import (  # noqa: E402
    JANELA,
    JOGANDO,
    LIVRE,
    DeteccaoFalhou,
    Processo,
    avaliar,
    listar_processos,
    resolver_raiz_principal,
    script_do_jogo,
    sinais_nos_processos,
    via_powershell,
    via_tasklist,
    via_wmic,
)

AGORA = 1_800_000_000.0
PYTHON_VENV = r"C:\Users\Victor\Projetos\cs2-tracker\.venv\Scripts\python.exe"


# ------------------------------------------------------------ apoio

@pytest.fixture
def raiz(tmp_path):
    """Checkout principal falso: tem .git como diretório."""
    (tmp_path / ".git").mkdir()
    return tmp_path


def _lista(*processos):
    return lambda: list(processos)


def _python(linha, pid=100, nome="python.exe"):
    return Processo(pid=pid, nome=nome, linha=linha)


def _abrir_janela(raiz, idade_s=60):
    marca = raiz / "logs" / "janelas" / "ABERTA"
    marca.parent.mkdir(parents=True)
    marca.write_text("", encoding="utf-8")
    os.utime(marca, (AGORA - idade_s, AGORA - idade_s))
    return marca


def _current_jsonl(raiz, idade_s):
    arquivo = raiz / "docker" / "events-live" / "current.jsonl"
    arquivo.parent.mkdir(parents=True)
    arquivo.write_text("", encoding="utf-8")
    os.utime(arquivo, (AGORA - idade_s, AGORA - idade_s))
    return arquivo


def _lista_que_falha(exc):
    def listar():
        raise exc
    return listar


# ---------------------------------------------------------- 0 livre

def test_livre_sem_processos_sem_current_jsonl_e_sem_janela(raiz):
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista(
        Processo(1, "explorer.exe", r"C:\WINDOWS\Explorer.EXE"),
        _python(f"{PYTHON_VENV} -m pytest -q"),
    ))
    assert r.codigo == LIVRE
    assert r.motivo.startswith("livre")


def test_current_jsonl_antigo_nao_conta(raiz):
    _current_jsonl(raiz, idade_s=15 * 60)
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista())
    assert r.codigo == LIVRE


# ------------------------------------------------ 3 Victor jogando

def test_cs2_exe_rodando_da_3(raiz):
    r = avaliar(raiz=raiz, agora=AGORA,
                listar=_lista(Processo(11592, "cs2.exe", None)))
    assert r.codigo == JOGANDO
    assert "cs2.exe (PID 11592)" in r.motivo


@pytest.mark.parametrize("linha, script", [
    (f"{PYTHON_VENV} wizard_tui.py", "wizard_tui"),
    (f'"{PYTHON_VENV}" "C:\\Users\\Victor\\Projetos\\cs2-tracker\\wizard_tui.py"', "wizard_tui"),
    (f"{PYTHON_VENV} -m wizard_tui", "wizard_tui"),
    (f"{PYTHON_VENV} -u watcher.py --mode matchzy --player victor", "watcher"),
    (f"{PYTHON_VENV} start_match.py --map de_mirage --side ct", "start_match"),
    ("python C:/Users/Victor/Projetos/cs2-tracker/START_MATCH.PY", "start_match"),
])
def test_python_rodando_script_do_jogo_da_3(raiz, linha, script):
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista(_python(linha, pid=7388)))
    assert r.codigo == JOGANDO
    assert f"python {script} (PID 7388)" in r.motivo


@pytest.mark.parametrize("linha", [
    f"{PYTHON_VENV} -m pytest tests/test_watcher.py",
    f"{PYTHON_VENV} -m pytest -q tests/test_wizard_session.py",
    f"{PYTHON_VENV} tools/live_watch.py --out logs/x.log",
    f"{PYTHON_VENV} -m uvicorn web.app:app --port 8010",
    f"{PYTHON_VENV} tools/preflight.py",
])
def test_python_que_nao_e_o_jogo_nao_conta(raiz, linha):
    assert avaliar(raiz=raiz, agora=AGORA, listar=_lista(_python(linha))).codigo == LIVRE


def test_script_do_jogo_so_em_processo_python(raiz):
    # grep/bash citando o nome do script não é o jogo rodando.
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista(
        Processo(5, "bash.exe", "bash -c 'grep -n x watcher.py'")))
    assert r.codigo == LIVRE


@pytest.mark.parametrize("nome", ["python.exe", "pythonw.exe", "python3.13.exe", "py.exe"])
def test_variacoes_de_nome_do_python(raiz, nome):
    r = avaliar(raiz=raiz, agora=AGORA,
                listar=_lista(_python("x wizard_tui.py", nome=nome)))
    assert r.codigo == JOGANDO


def test_current_jsonl_recente_da_3(raiz):
    _current_jsonl(raiz, idade_s=5 * 60)
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista())
    assert r.codigo == JOGANDO
    assert "current.jsonl modificado há 5 min" in r.motivo


def test_current_jsonl_com_mtime_no_futuro_conta_como_recente(raiz):
    _current_jsonl(raiz, idade_s=-120)
    assert avaliar(raiz=raiz, agora=AGORA, listar=_lista()).codigo == JOGANDO


def test_limite_de_dez_minutos(raiz):
    arquivo = _current_jsonl(raiz, idade_s=10 * 60 - 1)
    assert avaliar(raiz=raiz, agora=AGORA, listar=_lista()).codigo == JOGANDO
    os.utime(arquivo, (AGORA - 10 * 60, AGORA - 10 * 60))
    assert avaliar(raiz=raiz, agora=AGORA, listar=_lista()).codigo == LIVRE


def test_varios_sinais_aparecem_no_motivo(raiz):
    _current_jsonl(raiz, idade_s=30)
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista(
        Processo(1, "cs2.exe", None), _python("python wizard_tui.py", pid=2)))
    assert r.codigo == JOGANDO
    assert "cs2.exe" in r.motivo and "wizard_tui" in r.motivo and "current.jsonl" in r.motivo
    assert "\n" not in r.motivo


# ----------------------------------------------- 4 janela aberta

def test_janela_aberta_da_4(raiz):
    _abrir_janela(raiz, idade_s=5 * 60)
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista())
    assert r.codigo == JANELA
    assert "logs/janelas/ABERTA" in r.motivo
    assert "criada há 5 min" in r.motivo


# ------------------------------------ janela vencida (Q4=A, 45 min)

def test_limite_de_45_minutos(raiz):
    marca = _abrir_janela(raiz, idade_s=45 * 60 - 1)
    assert avaliar(raiz=raiz, agora=AGORA, listar=_lista()).codigo == JANELA
    os.utime(marca, (AGORA - 45 * 60, AGORA - 45 * 60))
    assert avaliar(raiz=raiz, agora=AGORA, listar=_lista()).codigo == LIVRE


def test_marca_esquecida_nao_vira_janela_aberta(raiz):
    # Janela nunca abre por ausência de processo (protocolo 8): uma marca
    # esquecida de ontem não libera o servidor.
    _abrir_janela(raiz, idade_s=24 * 3600)
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista())
    assert r.codigo == LIVRE
    assert r.motivo.startswith("livre")
    assert "janela vencida" in r.motivo
    assert "criada há 1440 min" in r.motivo


def test_marca_com_data_no_futuro(raiz):
    marca = _abrir_janela(raiz, idade_s=-30)
    assert avaliar(raiz=raiz, agora=AGORA, listar=_lista()).codigo == JANELA
    os.utime(marca, (AGORA + 5 * 60, AGORA + 5 * 60))
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista())
    assert r.codigo == LIVRE
    assert "janela vencida" in r.motivo and "no futuro" in r.motivo


def test_janela_vencida_aparece_mesmo_com_victor_jogando(raiz):
    _abrir_janela(raiz, idade_s=3 * 3600)
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista(Processo(9, "cs2.exe", None)))
    assert r.codigo == JOGANDO
    assert "cs2.exe" in r.motivo and "janela vencida" in r.motivo


# ------------------------------------------------- precedência

def test_jogando_tem_precedencia_sobre_janela_por_processo(raiz):
    _abrir_janela(raiz)
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista(Processo(9, "cs2.exe", None)))
    assert r.codigo == JOGANDO
    assert "janela aberta não vale" in r.motivo


def test_current_jsonl_recente_nao_derruba_janela_valida(raiz):
    # Dentro da janela o servidor trunca/escreve o current.jsonl (boot,
    # troca de mapa, partida só de bots): não é sinal do Victor.
    _abrir_janela(raiz)
    _current_jsonl(raiz, idade_s=60)
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista())
    assert r.codigo == JANELA
    assert "current.jsonl modificado há 1 min, ignorado dentro da janela" in r.motivo


def test_processo_do_victor_vence_janela_mesmo_com_current_jsonl_ignorado(raiz):
    _abrir_janela(raiz)
    _current_jsonl(raiz, idade_s=30)
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista(_python("python wizard_tui.py", pid=3)))
    assert r.codigo == JOGANDO
    assert "wizard_tui" in r.motivo and "janela aberta não vale" in r.motivo


def test_current_jsonl_recente_com_janela_vencida_da_3(raiz):
    _abrir_janela(raiz, idade_s=45 * 60)
    _current_jsonl(raiz, idade_s=60)
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista())
    assert r.codigo == JOGANDO
    assert "current.jsonl" in r.motivo and "janela vencida" in r.motivo


def test_falha_de_deteccao_tem_precedencia_sobre_janela(raiz):
    _abrir_janela(raiz)
    r = avaliar(raiz=raiz, agora=AGORA,
                listar=_lista_que_falha(DeteccaoFalhou("sem listagem")))
    assert r.codigo == JOGANDO


# ------------------------------------------------ falha segura

def test_listagem_que_falha_da_3_com_motivo(raiz):
    r = avaliar(raiz=raiz, agora=AGORA,
                listar=_lista_que_falha(DeteccaoFalhou("tasklist saiu com 1")))
    assert r.codigo == JOGANDO
    assert r.motivo.startswith("falha segura")
    assert "tasklist saiu com 1" in r.motivo


def test_erro_inesperado_tambem_da_3(raiz):
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista_que_falha(RuntimeError("boom")))
    assert r.codigo == JOGANDO
    assert "RuntimeError" in r.motivo


def test_python_sem_linha_de_comando_da_3(raiz):
    # Só o tasklist funcionou: há um python e não dá pra saber o que ele roda.
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista(_python(None, pid=4242)))
    assert r.codigo == JOGANDO
    assert "4242" in r.motivo


def test_o_proprio_preflight_sem_linha_nao_conta(raiz):
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista(
        _python(None, pid=os.getpid()), _python(None, pid=os.getppid())))
    assert r.codigo == LIVRE


def test_python_sem_linha_nao_mascara_cs2(raiz):
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista(
        _python(None, pid=4242), Processo(1, "cs2.exe", None)))
    assert r.codigo == JOGANDO
    assert "cs2.exe" in r.motivo


def test_stat_do_current_jsonl_com_erro_da_3(raiz, monkeypatch):
    original = Path.stat

    def stat_falho(self, *args, **kwargs):
        if self.name == "current.jsonl":
            raise PermissionError("negado")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat_falho)
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista())
    assert r.codigo == JOGANDO
    assert "current.jsonl" in r.motivo


def test_stat_da_marca_da_janela_com_erro_da_3(raiz, monkeypatch):
    _abrir_janela(raiz)
    original = Path.stat

    def stat_falho(self, *args, **kwargs):
        if self.name == "ABERTA":
            raise PermissionError("negado")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat_falho)
    r = avaliar(raiz=raiz, agora=AGORA, listar=_lista())
    assert r.codigo == JOGANDO
    assert r.motivo.startswith("falha segura")
    assert "logs/janelas/ABERTA" in r.motivo


def test_checkout_sem_git_da_3(tmp_path):
    r = avaliar(raiz=tmp_path, agora=AGORA, listar=_lista())
    assert r.codigo == JOGANDO
    assert "falha segura" in r.motivo


# --------------------------------------------- worktree → principal

def _worktree(tmp_path):
    principal = tmp_path / "cs2-tracker"
    gitdir = principal / ".git" / "worktrees" / "wt1"
    gitdir.mkdir(parents=True)
    (gitdir / "commondir").write_text("../..\n", encoding="utf-8")
    wt = principal / ".claude" / "worktrees" / "wt1"
    wt.mkdir(parents=True)
    (wt / ".git").write_text(f"gitdir: {gitdir.as_posix()}\n", encoding="utf-8")
    return principal, wt


def test_worktree_resolve_para_o_checkout_principal(tmp_path):
    principal, wt = _worktree(tmp_path)
    assert resolver_raiz_principal(wt) == principal.resolve()
    assert resolver_raiz_principal(principal) == principal


def test_de_dentro_da_worktree_olha_o_current_jsonl_do_principal(tmp_path):
    principal, wt = _worktree(tmp_path)
    _current_jsonl(principal, idade_s=60)
    assert avaliar(raiz=wt, agora=AGORA, listar=_lista()).codigo == JOGANDO


def test_de_dentro_da_worktree_olha_a_janela_do_principal(tmp_path):
    principal, wt = _worktree(tmp_path)
    _abrir_janela(principal)
    assert avaliar(raiz=wt, agora=AGORA, listar=_lista()).codigo == JANELA


def test_arquivo_git_quebrado_da_3(tmp_path):
    (tmp_path / ".git").write_text("lixo", encoding="utf-8")
    assert avaliar(raiz=tmp_path, agora=AGORA, listar=_lista()).codigo == JOGANDO


# --------------------------------------------- listagem simulada

class ExecutorFalso:
    """Faz o papel de subprocess.run: responde por nome do executável."""

    def __init__(self, respostas):
        self.respostas = respostas
        self.chamados = []

    def __call__(self, argv, **kwargs):
        nome = Path(argv[0]).name.lower()
        self.chamados.append(nome)
        resposta = self.respostas.get(nome)
        if resposta is None:
            raise FileNotFoundError(nome)
        if isinstance(resposta, BaseException):
            raise resposta
        codigo, saida = resposta
        return subprocess.CompletedProcess(argv, codigo, stdout=saida, stderr=b"")


def test_powershell_lista_com_linha_de_comando():
    saida = json.dumps([
        {"ProcessId": 4, "Name": "System", "CommandLine": None},
        {"ProcessId": 7388, "Name": "python.exe", "CommandLine": "python wizard_tui.py"},
    ]).encode("utf-8")
    processos = via_powershell(ExecutorFalso({"powershell.exe": (0, saida)}))
    assert Processo(7388, "python.exe", "python wizard_tui.py") in processos
    assert Processo(4, "System", None) in processos


def test_powershell_com_um_processo_so_devolve_objeto():
    saida = json.dumps({"ProcessId": 9, "Name": "cs2.exe", "CommandLine": "cs2.exe"}).encode()
    assert via_powershell(ExecutorFalso({"powershell.exe": (0, saida)})) == [
        Processo(9, "cs2.exe", "cs2.exe")]


@pytest.mark.parametrize("resposta", [
    (0, b"isto nao e json"),
    (0, b""),
    (1, b"[]"),
    subprocess.TimeoutExpired("powershell.exe", 30),
    PermissionError("negado"),
])
def test_powershell_com_problema_vira_deteccao_falhou(resposta):
    with pytest.raises(DeteccaoFalhou):
        via_powershell(ExecutorFalso({"powershell.exe": resposta}))


def test_wmic_utf16_com_virgula_na_linha_de_comando():
    texto = ("\r\nNode,CommandLine,Name,ProcessId\r\n"
             "PC,python -u watcher.py --mode matchzy --player a,b,python.exe,21772\r\n"
             "PC,,System,4\r\n")
    saida = b"\xff\xfe" + texto.encode("utf-16-le")
    processos = via_wmic(ExecutorFalso({"wmic.exe": (0, saida)}))
    assert Processo(21772, "python.exe",
                    "python -u watcher.py --mode matchzy --player a,b") in processos
    assert Processo(4, "System", None) in processos


def test_tasklist_so_da_nome_e_pid():
    saida = ('"System","4","Services","0","144 K"\r\n'
             '"cs2.exe","11592","Console","1","3.145.728 K"\r\n').encode("cp850")
    processos = via_tasklist(ExecutorFalso({"tasklist.exe": (0, saida)}))
    assert Processo(11592, "cs2.exe", None) in processos
    assert all(p.linha is None for p in processos)


def test_listagem_cai_pro_proximo_metodo(monkeypatch):
    monkeypatch.setattr(preflight, "_exe_do_sistema", lambda nome: nome)
    saida = '"cs2.exe","11592","Console","1","1 K"\r\n'.encode("cp850")
    executor = ExecutorFalso({"tasklist.exe": (0, saida)})
    processos = listar_processos(executor)
    assert executor.chamados == ["powershell.exe", "wmic.exe", "tasklist.exe"]
    assert sinais_nos_processos(processos) == ["cs2.exe (PID 11592)"]


def test_powershell_com_bom_utf8_ainda_parseia():
    saida = "﻿".encode("utf-8") + json.dumps(
        [{"ProcessId": 9, "Name": "cs2.exe", "CommandLine": None}]).encode("utf-8")
    assert via_powershell(ExecutorFalso({"powershell.exe": (0, saida)})) == [
        Processo(9, "cs2.exe", None)]


def test_saida_estranha_do_powershell_cai_pro_proximo_metodo(monkeypatch):
    monkeypatch.setattr(preflight, "_exe_do_sistema", lambda nome: nome)
    executor = ExecutorFalso({
        "powershell.exe": (0, b"[1, 2]"),  # JSON válido, formato inesperado
        "tasklist.exe": (0, b'"cs2.exe","11592","Console","1","1 K"\r\n'),
    })
    assert listar_processos(executor) == [Processo(11592, "cs2.exe", None)]


def test_sem_nenhum_metodo_de_listagem_vira_deteccao_falhou(monkeypatch):
    monkeypatch.setattr(preflight, "_exe_do_sistema", lambda nome: nome)
    with pytest.raises(DeteccaoFalhou, match="não deu pra listar os processos"):
        listar_processos(ExecutorFalso({}))


def test_script_do_jogo():
    assert script_do_jogo(r'"C:\x\python.exe" "C:\x\wizard_tui.py"') == "wizard_tui"
    assert script_do_jogo("python -m start_match --map de_nuke") == "start_match"
    assert script_do_jogo("python tests/test_watcher.py") is None
    assert script_do_jogo("python watcher.pyc") is None


# ------------------------------------------------------------ CLI

@pytest.mark.parametrize("preparar, codigo", [
    (lambda r: None, LIVRE),
    (_abrir_janela, JANELA),
    (lambda r: _current_jsonl(r, idade_s=0), JOGANDO),
])
def test_main_imprime_uma_linha_e_devolve_o_codigo(raiz, capsys, monkeypatch, preparar, codigo):
    monkeypatch.setattr(preflight, "time", SimpleNamespace(time=lambda: AGORA))
    preparar(raiz)
    assert preflight.main(["--raiz", str(raiz)], listar=_lista()) == codigo
    saida = capsys.readouterr().out
    assert saida.count("\n") == 1
    assert saida.startswith(f"preflight {codigo}: ")


def test_main_com_erro_de_varias_linhas_ainda_imprime_uma_linha(raiz, capsys):
    listar = _lista_que_falha(RuntimeError("linha 1\nlinha 2"))
    assert preflight.main(["--raiz", str(raiz)], listar=listar) == JOGANDO
    saida = capsys.readouterr().out
    assert saida.count("\n") == 1
    assert "linha 1 linha 2" in saida

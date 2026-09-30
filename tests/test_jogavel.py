#!/usr/bin/env python3
"""
Testes de tools/jogavel.py, card B0.7: núcleo, status, voltar e atualizar
(fatia 1) e janela abrir, fechar e vigiar (fatia 2); card B0.7b: pasta do
plugin pelo manifesto no voltar, marcar, comandos do servidor e coletar.

O checkout é um repo git de verdade em tmp_path (git init, com a origin num
repo bare ao lado). Docker, RCON, lista de processos e preflight são falsos:
o executor recebe um `rodar` que só deixa passar git, e só dentro de
tmp_path. As cópias da pasta do plugin também ficam em tmp_path. Nada do
checkout principal nem dos backups é tocado. Na janela, relógio e sono
também são falsos: o `vigiar` não espera de verdade.
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import jogavel  # noqa: E402
from jogavel import CRLF, FALHA, OK, PARTIDA, RECUSA, VENCIDA, Executor, main  # noqa: E402

AGORA = 1_800_000_000.0
PS = r"C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe"
PY = r"C:\Users\Victor\Projetos\cs2-tracker\.venv\Scripts\python.exe"
RUNTIME = "docker/match_config.spike.json"
CFG = "server-configs/cfg/gamemode_competitive_server.cfg"


def _git(raiz, *args):
    return subprocess.run(["git", *args], cwd=raiz, capture_output=True, encoding="utf-8",
                          check=True).stdout.strip()


def _commit(raiz, msg, arquivos=None, remover=(), tag=None):
    for rel, conteudo in (arquivos or {}).items():
        caminho = raiz / rel
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(conteudo if isinstance(conteudo, bytes) else conteudo.encode())
        _git(raiz, "add", rel)
    for rel in remover:
        _git(raiz, "rm", "-q", "--cached", rel)
    _git(raiz, "commit", "-q", "-m", msg)
    if tag:
        _git(raiz, "tag", tag)
    return _git(raiz, "rev-parse", "HEAD")


class Mundo:
    """O lado de fora do checkout: docker, processos e preflight falsos."""

    def __init__(self, raiz):
        self.raiz = raiz
        self.processos = []
        # Quem responde a lista de processos: "powershell" (com linha de
        # comando), "tasklist" (PowerShell sai 1, wmic ausente, tasklist sem
        # linha de comando: o caso desta máquina) ou "nenhum".
        self.listagem = "powershell"
        self.preflight = 0
        self.binds = [CFG, "docker/pre.sh", RUNTIME]
        self.compose_ok = True
        self.build, self.build_depois = "2000918", "2000918"
        self.docker = []
        self.container = "Up 2 hours"
        self.ps_falha = False
        # Relógio falso da janela e um `docker ps` que "espera aprovação":
        # avança o relógio uma vez (lição de 27/09).
        self.relogio, self.docker_lento = None, 0

    def rodar(self, argv, cwd=None, capture_output=True, timeout=None, **_kw):
        assert Path(cwd).resolve().is_relative_to(self.raiz.parent.resolve()), cwd
        nome = Path(argv[0]).name.lower()
        if nome == "git":
            return subprocess.run(argv, cwd=cwd, capture_output=True, timeout=timeout)
        if nome == "docker":
            self.docker.append(" ".join(argv[1:]))
            return self._docker(argv[1:])
        if nome == "powershell.exe":
            if self.listagem != "powershell":
                return _feito(argv, 1, "")
            linhas = [{"ProcessId": pid, "Name": n, "CommandLine": c} for pid, n, c in self.processos]
            return _feito(argv, 0, json.dumps(linhas))
        if nome == "wmic.exe":
            raise FileNotFoundError(argv[0])
        if nome == "tasklist.exe":
            if self.listagem != "tasklist":
                return _feito(argv, 1, "")
            return _feito(argv, 0, "".join(f'"{n}","{pid}","Console","1","1.000 K"\n'
                                           for pid, n, _c in self.processos))
        if any(a.endswith("preflight.py") for a in argv):
            return _feito(argv, self.preflight, f"preflight {self.preflight}: falso")
        raise AssertionError(f"processo inesperado: {argv}")

    def _docker(self, args):
        if args[:2] == ["compose", "config"]:
            vols = [{"type": "bind", "source": str(self.raiz / b), "target": "/x"} for b in self.binds]
            vols.append({"type": "volume", "source": "cs2-data", "target": "/home/steam"})
            return _feito(args, 0 if self.compose_ok else 1,
                          json.dumps({"services": {"cs2-server": {"volumes": vols}}}))
        if args[:1] == ["logs"]:
            return _feito(args, 0, f"GC Connection established for server version {self.build}, instance idx 1\n")
        if args[:2] == ["compose", "up"]:
            self.build = self.build_depois
            return _feito(args, 0, "")
        if args[:1] == ["ps"]:
            if self.docker_lento:
                self.relogio.t += self.docker_lento
                self.docker_lento = 0
            return _feito(args, 1 if self.ps_falha else 0, "" if self.ps_falha else self.container + "\n")
        if args == ["stop", "cs2-spike"]:
            self.container = "Exited (0) 1 second ago"
            return _feito(args, 0, "cs2-spike\n")
        raise AssertionError(f"docker inesperado: {args}")


def _feito(argv, codigo, saida):
    return subprocess.CompletedProcess(argv, codigo, saida.encode("utf-8"), b"")


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    """Checkout com a tag jogavel-2026-09-26 e a main um commit à frente
    (só Python), com o runtime file modificado como o start_match deixa.
    Para o recreate, ele faz o papel do checkout principal."""
    raiz = tmp_path / "checkout"
    raiz.mkdir()
    monkeypatch.setattr(jogavel, "checkout_principal", lambda: raiz)
    monkeypatch.setattr(jogavel, "COPIAS_PLUGIN", tmp_path / "copias")
    _git(raiz, "init", "-q", "-b", "main")
    for chave, valor in (("core.autocrlf", "false"), ("user.name", "Teste"),
                         ("user.email", "teste@example.invalid"), ("commit.gpgsign", "false")):
        _git(raiz, "config", chave, valor)
    _commit(raiz, "base", {"docker-compose.yml": "services: {}\n", "docker/pre.sh": "echo pre\n",
                           RUNTIME: '{"matchid": 1}\n', CFG: "bot_quota 0\n",
                           "start_match.py": "v = 1\n"}, tag="jogavel-2026-09-26")
    _commit(raiz, "python", {"start_match.py": "v = 2\n"})
    (raiz / RUNTIME).write_text('{"matchid": 99}\n')
    origem = tmp_path / "origem.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origem)], check=True)
    _git(raiz, "remote", "add", "origin", str(origem))
    _git(raiz, "push", "-q", "origin", "main", "--tags")
    _git(raiz, "fetch", "-q", "origin")
    mundo = Mundo(raiz)
    mundo.copias = tmp_path / "copias"
    return mundo


def _rodar(mundo, *argv, entrada=None, agora=AGORA):
    def fabrica(raiz, seco=False):
        return Executor(raiz, seco=seco, rodar=mundo.rodar, dormir=lambda _s: None)

    def sem_pergunta(texto):
        raise AssertionError(f"não devia perguntar: {texto}")
    return main(["--raiz", str(mundo.raiz), *argv], fabrica=fabrica,
                entrada=entrada or sem_pergunta, agora=agora)


def _head(mundo):
    return _git(mundo.raiz, "rev-parse", "HEAD")


def _tag(mundo, tag="jogavel-2026-09-26"):
    return _git(mundo.raiz, "rev-parse", f"{tag}^{{commit}}")


def _current(mundo, eventos, idade_s):
    arquivo = mundo.raiz / "docker" / "events-live" / "current.jsonl"
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text("".join(json.dumps({"type": t}) + "\n" for t in eventos))
    os.utime(arquivo, (AGORA - idade_s, AGORA - idade_s))


# --------------------------------------------------- partida em curso

def test_partida_em_curso_recusa_sem_tocar_em_nada(mundo, capsys):
    _current(mundo, ["round_start", "player_hurt", "snapshot", "snapshot"], idade_s=5)
    antes = _head(mundo)
    assert _rodar(mundo, "voltar") == PARTIDA
    assert _head(mundo) == antes and mundo.docker == []
    assert "partida em curso: current.jsonl com player_hurt há ~6 s" in capsys.readouterr().out


def test_watcher_ingerindo_recusa(mundo, capsys):
    mundo.processos = [(4321, "python.exe", f"{PY} -u watcher.py --mode matchzy")]
    assert _rodar(mundo, "voltar") == PARTIDA
    assert "watcher ingerindo (python watcher (PID 4321))" in capsys.readouterr().out


def test_so_cs2_exe_e_tui_avisam_o_que_fechar_e_voltam(mundo, capsys):
    mundo.processos = [(10, "cs2.exe", None), (11, "python.exe", f"{PY} wizard_tui.py")]
    assert _rodar(mundo, "voltar") == OK
    saida = capsys.readouterr().out
    assert "aviso: feche o CS2: cs2.exe (PID 10)" in saida
    assert "aviso: feche a TUI: python wizard_tui (PID 11)" in saida
    assert _head(mundo) == _tag(mundo)


def test_so_tasklist_com_cs2_e_python_sem_linha_recusa(mundo, capsys):
    # Reprovação 1 do QA: PowerShell sai 1, wmic não existe, e o tasklist
    # mostra o cs2.exe e um python sem linha de comando, que pode ser o
    # watcher. O cs2.exe não pode esconder o python cego.
    mundo.listagem = "tasklist"
    mundo.processos = [(10, "cs2.exe", None), (4321, "python.exe", None)]
    ex = Executor(mundo.raiz, rodar=mundo.rodar)
    assert jogavel.sinais_de_partida(ex, AGORA) == (
        ["sem certeza sobre o watcher: python sem linha de comando legível (PID 4321)"],
        ["feche o CS2: cs2.exe (PID 10)"])
    antes = _head(mundo)
    assert _rodar(mundo, "voltar") == PARTIDA
    saida = capsys.readouterr().out
    assert "voltar recusado" in saida and "aviso: feche o CS2: cs2.exe (PID 10)" in saida
    assert _head(mundo) == antes and mundo.docker == []


def test_so_tasklist_so_com_cs2_avisa_e_volta(mundo, capsys):
    mundo.listagem = "tasklist"
    mundo.processos = [(10, "cs2.exe", None)]
    assert _rodar(mundo, "voltar") == OK
    assert "aviso: feche o CS2: cs2.exe (PID 10)" in capsys.readouterr().out
    assert _head(mundo) == _tag(mundo)


def test_sem_lista_de_processos_recusa(mundo, capsys):
    mundo.listagem = "nenhum"
    mundo.processos = [(10, "cs2.exe", None)]
    antes = _head(mundo)
    assert _rodar(mundo, "voltar") == PARTIDA
    assert "sem certeza sobre o watcher: não deu pra listar os processos" in capsys.readouterr().out
    assert _head(mundo) == antes


def test_cauda_so_de_snapshots_depois_do_fim_nao_e_partida(mundo):
    # round_end e 300 snapshots (150 s a 2 por segundo): o arquivo é recente,
    # mas o último evento de round já passou de 2 min.
    _current(mundo, ["round_end"] + ["snapshot"] * 300, idade_s=1)
    assert _rodar(mundo, "voltar") == OK


def test_idade_do_round_soma_mtime_e_snapshots(mundo):
    _current(mundo, ["round_end"] + ["snapshot"] * 100, idade_s=10)
    assert jogavel.evento_de_round_recente(mundo.raiz, AGORA) == "current.jsonl com round_end há ~60 s"
    _current(mundo, ["round_end"] + ["snapshot"] * 100, idade_s=70)
    assert jogavel.evento_de_round_recente(mundo.raiz, AGORA) is None


@pytest.mark.parametrize("tipo", ["freeze_end", "round_officially_ended", "player_blind", "round_stats"])
def test_eventos_de_round_alem_de_dano_e_bomba(mundo, tipo):
    _current(mundo, [tipo] + ["snapshot"] * 100, idade_s=10)
    assert jogavel.evento_de_round_recente(mundo.raiz, AGORA) == f"current.jsonl com {tipo} há ~60 s"


def test_round_sem_dano_conta_do_fim_do_freeze(mundo, capsys):
    # 15 s de freeze (30 snapshots) e 115 s de round sem dano (230): do
    # round_start são 130 s, do freeze_end são 115 s. Ainda é partida.
    _current(mundo, ["round_start"] + ["snapshot"] * 30 + ["freeze_end"] + ["snapshot"] * 230,
             idade_s=0)
    assert _rodar(mundo, "voltar") == PARTIDA
    assert "current.jsonl com freeze_end há ~115 s" in capsys.readouterr().out


@pytest.mark.parametrize("digitado,codigo", [("VOLTAR", OK), ("sim", RECUSA)])
def test_agora_pede_confirmacao_digitada(mundo, digitado, codigo):
    _current(mundo, ["round_start"], idade_s=5)
    perguntas = []
    assert _rodar(mundo, "voltar", "--agora",
                  entrada=lambda t: perguntas.append(t) or digitado) == codigo
    assert perguntas and "Digite VOLTAR" in perguntas[0]
    assert (_head(mundo) == _tag(mundo)) is (codigo == OK)


def test_agora_nao_le_docker_logs_antes_do_recreate(mundo, capsys):
    # docker logs com partida em curso é proibido (AGENTS.md): a build
    # "antes" fica sem leitura e a "depois" sai do container novo.
    _git(mundo.raiz, "checkout", "-q", "--", RUNTIME)
    _commit(mundo.raiz, "cfg", {CFG: "bot_quota 5\n"})
    _current(mundo, ["round_start"], idade_s=5)
    mundo.build_depois = "2000919"
    assert _rodar(mundo, "voltar", "--agora", entrada=lambda _t: "VOLTAR") == OK
    saida = capsys.readouterr().out
    assert mundo.docker == ["compose config --format json", "compose up -d --force-recreate",
                            "logs cs2-spike"]
    assert "build do CS2 antes: não lida (partida em curso)" in saida
    assert "build do CS2 depois: 2000919" in saida and "a build do CS2 mudou" not in saida
    assert not list((mundo.raiz / "logs" / "jogavel").glob("*/docker-logs.txt"))


# ------------------------------------------------------ runtime file

def test_runtime_modificado_nos_dois_commits_e_restaurado(mundo):
    alvo = _commit(mundo.raiz, "match_config novo", {RUNTIME: '{"matchid": 2}\n'}, tag="jogavel-x")
    _git(mundo.raiz, "switch", "-q", "--detach", "HEAD~1")
    (mundo.raiz / RUNTIME).write_text('{"matchid": 99}\n')
    assert _rodar(mundo, "voltar", "--tag", "jogavel-x") == OK
    assert _head(mundo) == alvo
    assert (mundo.raiz / RUNTIME).read_text() == '{"matchid": 99}\n'


def test_runtime_rastreado_para_nao_rastreado_fica_so_a_copia(mundo):
    # Sentido 1: HEAD rastreia (modificado), o alvo já não rastreia (P1.6).
    alvo = _commit(mundo.raiz, "runtime fora do índice", remover=[RUNTIME], tag="jogavel-sem")
    (mundo.raiz / RUNTIME).unlink()
    _git(mundo.raiz, "switch", "-q", "--detach", "jogavel-2026-09-26")
    (mundo.raiz / RUNTIME).write_text('{"matchid": 99}\n')
    assert _rodar(mundo, "voltar", "--tag", "jogavel-sem") == OK
    assert _head(mundo) == alvo and not (mundo.raiz / RUNTIME).exists()
    copias = list((mundo.raiz / "logs" / "jogavel").glob("*/match_config.spike.json"))
    assert [c.read_text() for c in copias] == ['{"matchid": 99}\n']


def test_runtime_nao_rastreado_para_rastreado_e_restaurado(mundo):
    # Sentido 2: HEAD não rastreia (arquivo solto), o alvo rastreia: sem o
    # tratamento, o git switch recusa sobrescrever o arquivo não rastreado.
    _commit(mundo.raiz, "runtime fora do índice", remover=[RUNTIME])
    (mundo.raiz / RUNTIME).write_text('{"matchid": 77}\n')
    assert _rodar(mundo, "voltar", "--tag", "jogavel-2026-09-26") == OK
    assert _head(mundo) == _tag(mundo)
    assert (mundo.raiz / RUNTIME).read_text() == '{"matchid": 77}\n'


# ----------------------------------------------- pre.sh e infra

def test_pre_sh_com_crlf_aborta_antes_do_recreate(mundo, capsys):
    _git(mundo.raiz, "checkout", "-q", "--", RUNTIME)
    _git(mundo.raiz, "switch", "-q", "--detach", "jogavel-2026-09-26")
    _commit(mundo.raiz, "crlf", {"docker/pre.sh": b"echo pre\r\nexit 0\r\n",
                                 "docker-compose.yml": "services: {a: {}}\n"}, tag="jogavel-crlf")
    _git(mundo.raiz, "switch", "-q", "main")
    assert _rodar(mundo, "voltar", "--tag", "jogavel-crlf") == CRLF
    saida = capsys.readouterr().out
    assert "docker/pre.sh tem 2 '\\r'" in saida and "--recriar" in saida
    assert not any(c.startswith("compose up") for c in mundo.docker)


def test_fontes_de_bind_so_as_de_dentro_do_checkout(mundo):
    mundo.binds = [CFG, "docker/plugins/BotAimImprover", "../fora/pasta"]
    ex = Executor(mundo.raiz, rodar=mundo.rodar)
    assert jogavel.fontes_de_bind(ex) == ["docker/plugins/BotAimImprover", CFG]
    mudados = ["start_match.py", CFG, "docker/plugins/X/a.dll", "docker-compose.yml", "docs/a.md"]
    assert jogavel.infra_no_delta(ex, mudados) == [CFG, "docker/plugins/X/a.dll", "docker-compose.yml"]


def test_fonte_de_bind_mudada_recria_e_registra_a_build(mundo, capsys):
    _git(mundo.raiz, "checkout", "-q", "--", RUNTIME)
    _commit(mundo.raiz, "cfg", {CFG: "bot_quota 5\n"})
    mundo.build_depois = "2000919"
    assert _rodar(mundo, "voltar") == OK
    saida = capsys.readouterr().out
    assert "infra difere: " + CFG in saida
    assert "compose up -d --force-recreate" in mundo.docker
    assert "build do CS2 antes: 2000918" in saida and "build do CS2 depois: 2000919" in saida
    assert "a build do CS2 mudou (2000918 -> 2000919)" in saida
    assert list((mundo.raiz / "logs" / "jogavel").glob("*/docker-logs.txt"))


def test_so_python_mudado_nao_recria(mundo, capsys):
    assert _rodar(mundo, "voltar") == OK
    assert "infra igual à do alvo: sem recreate" in capsys.readouterr().out
    assert not any(c.startswith("compose up") for c in mundo.docker)


def test_sem_compose_config_todo_mudado_conta_como_infra(mundo):
    mundo.compose_ok = False
    assert _rodar(mundo, "voltar") == OK
    assert "compose up -d --force-recreate" in mundo.docker


def test_recriar_forca_o_recreate_com_infra_igual(mundo):
    _git(mundo.raiz, "checkout", "-q", "--", RUNTIME)
    _git(mundo.raiz, "switch", "-q", "--detach", "jogavel-2026-09-26")
    assert _rodar(mundo, "voltar", "--recriar") == OK
    assert "compose up -d --force-recreate" in mundo.docker


def test_recreate_so_do_checkout_principal(mundo, tmp_path, capsys):
    wt = tmp_path / "wt"
    _git(mundo.raiz, "worktree", "add", "-q", "--detach", str(wt), "main")
    mundo.raiz = wt  # .git aqui é arquivo: o compose criaria projeto e volume novos
    assert _rodar(mundo, "voltar", "--recriar") == RECUSA
    assert "não é o checkout principal" in capsys.readouterr().out
    assert not any(c.startswith("compose up") for c in mundo.docker)


def test_recreate_recusa_clone_avulso(mundo, tmp_path, capsys):
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", "-c", "core.autocrlf=false", str(mundo.raiz), str(clone)],
                   check=True)
    assert (clone / ".git").is_dir()  # pasta .git, como a do principal
    mundo.raiz = clone
    assert _rodar(mundo, "voltar", "--recriar") == RECUSA
    assert "não é o checkout principal" in capsys.readouterr().out
    assert not any(c.startswith("compose up") for c in mundo.docker)


# ---------------------------------- pasta do plugin pelo manifesto (B0.7b)

PLUGIN = "docker/plugins/Cs2TrackerEvents"
BOM = {"Cs2TrackerEvents.dll": b"dll boa", "Cs2TrackerEvents.deps.json": b'{"deps": 1}',
       "Cs2TrackerEvents.pdb": b"pdb bom"}
# A pasta do checkout depois de um build ruim: DLL nova, .pdb sumido e um arquivo a mais.
RUIM = {"Cs2TrackerEvents.dll": b"dll ruim", "Cs2TrackerEvents.deps.json": b'{"deps": 1}',
        "extra.xml": b"<x/>"}


def _sha(dados):
    return hashlib.sha256(dados).hexdigest()


def _copia(mundo, arquivos=BOM, formato="b0.3"):
    """Cópia da pasta em copias/<sha256 da DLL>/, com o manifesto de um dos
    dois formatos que existem nos backups."""
    sha_dll = _sha(arquivos["Cs2TrackerEvents.dll"])
    pasta = mundo.copias / sha_dll
    pasta.mkdir(parents=True)
    for nome, dados in arquivos.items():
        (pasta / nome).write_bytes(dados)
    if formato == "b0.3":
        linhas = ["# Manifesto da pasta docker/plugins/Cs2TrackerEvents/ (card B0.3)",
                  "# formato: sha256  bytes  mtime-da-origem  nome"]
        linhas += [f"{_sha(d)}  {len(d)}  2026-09-23T19:10:55-03:00  {n}" for n, d in arquivos.items()]
        (pasta / "MANIFEST.txt").write_text("\n".join(linhas) + "\n")
    else:
        (pasta / "MANIFESTO.sha256").write_text("".join(f"{_sha(d)} *{n}\n" for n, d in arquivos.items()))
    return sha_dll


def _pasta_plugin(mundo, arquivos):
    pasta = mundo.raiz / PLUGIN
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, dados in arquivos.items():
        (pasta / nome).write_bytes(dados)
    return pasta


def _conteudo(pasta):
    return {a.name: a.read_bytes() for a in pasta.iterdir()}


def _tag_com_plugin(mundo, sha_dll, tag="jogavel-plugin", commit="jogavel-2026-09-26"):
    _git(mundo.raiz, "tag", "-a", tag, commit, "-m", f"G7 ok\n\nplugin Cs2TrackerEvents: {sha_dll}")
    return tag


def test_voltar_restaura_a_pasta_inteira_do_plugin_com_o_container_parado(mundo, capsys):
    sha_dll = _copia(mundo)
    pasta = _pasta_plugin(mundo, RUIM)
    assert _rodar(mundo, "voltar", "--tag", _tag_com_plugin(mundo, sha_dll)) == OK
    saida = capsys.readouterr().out
    assert _conteudo(pasta) == {"Cs2TrackerEvents.dll": b"dll boa", "Cs2TrackerEvents.deps.json": b'{"deps": 1}',
                                "Cs2TrackerEvents.pdb": b"pdb bom"}
    antes, = (mundo.raiz / "logs" / "jogavel").glob("*-voltar/plugin-antes")
    assert _conteudo(antes) == RUIM  # nada se apaga: a pasta de antes fica como evidência
    # para antes de trocar, e recria depois (a pasta do plugin é infra)
    assert mundo.docker.index("stop cs2-spike") < mundo.docker.index("compose up -d --force-recreate")
    assert f"pasta do plugin restaurada do manifesto {sha_dll[:12]} e conferida (3 arquivos)" in saida
    assert "infra difere: docker/plugins/Cs2TrackerEvents/" in saida


def test_voltar_com_a_pasta_igual_ao_manifesto_nao_para_nem_recria(mundo, capsys):
    sha_dll = _copia(mundo)
    _pasta_plugin(mundo, BOM)
    assert _rodar(mundo, "voltar", "--tag", _tag_com_plugin(mundo, sha_dll)) == OK
    assert f"pasta do plugin confere com o manifesto {sha_dll[:12]}" in capsys.readouterr().out
    assert "stop cs2-spike" not in mundo.docker
    assert not any(c.startswith("compose up") for c in mundo.docker)


def test_voltar_com_container_ja_parado_restaura_sem_stop(mundo):
    sha_dll = _copia(mundo)
    pasta = _pasta_plugin(mundo, RUIM)
    mundo.container = "Exited (137) 3 minutes ago"
    assert _rodar(mundo, "voltar", "--tag", _tag_com_plugin(mundo, sha_dll)) == OK
    assert _conteudo(pasta) == BOM and "stop cs2-spike" not in mundo.docker


def test_voltar_com_copia_que_nao_confere_nao_troca_nada(mundo, capsys):
    sha_dll = _copia(mundo)
    (mundo.copias / sha_dll / "Cs2TrackerEvents.pdb").write_bytes(b"pdb corrompido")
    pasta = _pasta_plugin(mundo, RUIM)
    assert _rodar(mundo, "voltar", "--tag", _tag_com_plugin(mundo, sha_dll)) == FALHA
    assert "não confere com o próprio manifesto (sha256 diferente: Cs2TrackerEvents.pdb)" in capsys.readouterr().out
    assert _conteudo(pasta) == RUIM and "stop cs2-spike" not in mundo.docker


def test_voltar_sem_saber_se_o_container_parou_nao_troca_a_dll(mundo, capsys):
    sha_dll = _copia(mundo)
    pasta = _pasta_plugin(mundo, RUIM)
    mundo.ps_falha = True
    assert _rodar(mundo, "voltar", "--tag", _tag_com_plugin(mundo, sha_dll)) == FALHA
    assert "o container não está comprovadamente parado" in capsys.readouterr().out
    assert _conteudo(pasta) == RUIM and "stop cs2-spike" not in mundo.docker


def test_voltar_entende_o_manifesto_do_sha256sum_e_o_plugin_forcado(mundo):
    # Tag antiga, sem a linha do `marcar`: o sha256 da DLL vem do --plugin.
    sha_dll = _copia(mundo, formato="sha256sum")
    pasta = _pasta_plugin(mundo, RUIM)
    assert _rodar(mundo, "voltar", "--plugin", sha_dll) == OK
    assert _conteudo(pasta) == BOM


def test_voltar_de_tag_sem_registro_do_plugin_so_avisa(mundo, capsys):
    pasta = _pasta_plugin(mundo, RUIM)
    assert _rodar(mundo, "voltar") == OK
    assert "jogavel-2026-09-26 não registra o manifesto" in capsys.readouterr().out
    assert _conteudo(pasta) == RUIM and "stop cs2-spike" not in mundo.docker


def test_voltar_seco_nao_troca_o_plugin(mundo, capsys):
    sha_dll = _copia(mundo)
    pasta = _pasta_plugin(mundo, RUIM)
    assert _rodar(mundo, "voltar", "--seco", "--tag", _tag_com_plugin(mundo, sha_dll)) == OK
    saida = capsys.readouterr().out
    assert _conteudo(pasta) == RUIM and "stop cs2-spike" not in mundo.docker
    assert "[seco] docker stop cs2-spike" in saida and "[seco] restauraria" in saida


def test_pre_sh_crlf_aborta_antes_de_parar_pelo_plugin(mundo):
    sha_dll = _copia(mundo)
    pasta = _pasta_plugin(mundo, RUIM)
    _git(mundo.raiz, "checkout", "-q", "--", RUNTIME)
    _git(mundo.raiz, "switch", "-q", "--detach", "jogavel-2026-09-26")
    _commit(mundo.raiz, "crlf", {"docker/pre.sh": b"echo pre\r\n"})
    _tag_com_plugin(mundo, sha_dll, commit="HEAD")
    _git(mundo.raiz, "switch", "-q", "main")
    assert _rodar(mundo, "voltar", "--tag", "jogavel-plugin") == CRLF
    assert _conteudo(pasta) == RUIM and "stop cs2-spike" not in mundo.docker


def test_ler_manifesto_dos_dois_formatos(tmp_path):
    b03 = tmp_path / "MANIFEST.txt"
    b03.write_text("# comentário\n" + "a" * 64 + "  49152  2026-09-23T19:10:55-03:00  X.dll\n\n")
    sha256sum = tmp_path / "MANIFESTO.sha256"
    sha256sum.write_text("B" * 64 + " *Y.deps.json\n" + "c" * 64 + "  Z.pdb\n")
    assert jogavel.ler_manifesto(b03) == {"X.dll": "a" * 64}
    assert jogavel.ler_manifesto(sha256sum) == {"Y.deps.json": "b" * 64, "Z.pdb": "c" * 64}


@pytest.mark.parametrize("linha", ["abc  X.dll", "a" * 64, "a" * 64 + "  ../X.dll", ""])
def test_ler_manifesto_recusa_linha_fora_do_formato(tmp_path, linha):
    arquivo = tmp_path / "MANIFEST.txt"
    arquivo.write_text(linha + "\n")
    with pytest.raises(ValueError):
        jogavel.ler_manifesto(arquivo)


# ------------------------------------------------------ marcar (B0.7b)

NOTA = "B1.10 · PR #40"
QUANDO = datetime.fromtimestamp(AGORA).strftime("%Y-%m-%dT%H:%M:%S")


def _tags(mundo, padrao):
    return _git(mundo.raiz, "tag", "-l", padrao).split()


def test_marcar_candidato_cria_tag_registro_copia_e_candidato_json(mundo):
    _pasta_plugin(mundo, BOM)
    _git(mundo.raiz, "tag", "candidato-7", "jogavel-2026-09-26")  # o N segue o maior
    sha, sha_dll = _head(mundo), _sha(b"dll boa")
    assert _rodar(mundo, "marcar", "candidato", "main", "-m", NOTA) == OK
    # tag anotada no commit, com o sha256 da DLL na mensagem, e na origin
    assert _git(mundo.raiz, "rev-parse", "candidato-8^{commit}") == sha
    assert _git(mundo.raiz, "cat-file", "-t", "candidato-8") == "tag"
    mensagem = _git(mundo.raiz, "tag", "-l", "--format=%(contents)", "candidato-8")
    assert mensagem.startswith(f"{NOTA}\n\nplugin Cs2TrackerEvents: {sha_dll}\n")
    assert "refs/tags/candidato-8" in _git(mundo.raiz, "ls-remote", "--tags", "origin")
    # cópia da pasta inteira, com o manifesto do B0.3
    copia = mundo.copias / sha_dll
    assert {n: d for n, d in _conteudo(copia).items() if n != "MANIFEST.txt"} == BOM
    linhas = (copia / "MANIFEST.txt").read_text(encoding="utf-8").splitlines()
    # sha256, bytes, mtime e nome, como o MANIFEST.txt do B0.3
    assert [(l.split()[0], l.split()[1], l.split()[3]) for l in linhas if not l.startswith("#")] == [
        (_sha(b'{"deps": 1}'), "11", "Cs2TrackerEvents.deps.json"),
        (_sha(b"dll boa"), "7", "Cs2TrackerEvents.dll"),
        (_sha(b"pdb bom"), "7", "Cs2TrackerEvents.pdb")]
    registro = (mundo.raiz / "logs" / "jogavel" / "tags.md").read_text(encoding="utf-8")
    assert registro == f"- {QUANDO} candidato-8 -> {sha[:9]} · plugin {sha_dll[:12]} · {NOTA}\n"
    assert json.loads((mundo.raiz / "data" / "candidato.json").read_text(encoding="utf-8")) == {
        "tag": "candidato-8", "commit": sha, "nota": NOTA, "plugin_captura": sha_dll, "marcado_em": QUANDO}


def test_voltar_para_a_tag_do_marcar_restaura_o_plugin_dela(mundo):
    pasta = _pasta_plugin(mundo, BOM)
    assert _rodar(mundo, "marcar", "candidato", "jogavel-2026-09-26", "-m", NOTA) == OK
    for nome, dados in RUIM.items():
        (pasta / nome).write_bytes(dados)
    (pasta / "Cs2TrackerEvents.pdb").unlink()
    assert _rodar(mundo, "voltar", "--tag", "candidato-1") == OK
    assert _conteudo(pasta) == BOM


def test_marcar_jogavel_com_nome_ocupado_e_fecha_o_candidato(mundo, capsys):
    _pasta_plugin(mundo, BOM)
    assert _rodar(mundo, "marcar", "candidato", "jogavel-2026-09-26", "-m", "B1.3r") == OK
    _git(mundo.raiz, "tag", "jogavel-2027-01-15", "jogavel-2026-09-26")  # o dia de AGORA, noutro commit
    assert _rodar(mundo, "marcar", "jogavel", "main", "-m", "G7 ok, partida 32") == OK
    assert _git(mundo.raiz, "rev-parse", "jogavel-2027-01-15-2^{commit}") == _head(mundo)
    assert not (mundo.raiz / "data" / "candidato.json").exists()
    assert "data/candidato.json apagado: candidato-1 validado por jogavel-2027-01-15-2" in capsys.readouterr().out
    # de novo no mesmo commit: já feita, sem tag nova
    assert _rodar(mundo, "marcar", "jogavel", "main", "-m", "G7 ok, partida 32") == OK
    assert _tags(mundo, "jogavel-2027-*") == ["jogavel-2027-01-15", "jogavel-2027-01-15-2"]


def test_marcar_jogavel_mantem_o_candidato_que_nao_esta_nela(mundo):
    _pasta_plugin(mundo, BOM)
    assert _rodar(mundo, "marcar", "candidato", "main", "-m", NOTA) == OK
    assert _rodar(mundo, "marcar", "jogavel", "jogavel-2026-09-26", "-m", "reteste") == OK
    assert json.loads((mundo.raiz / "data" / "candidato.json").read_text(encoding="utf-8"))["tag"] == "candidato-1"


def test_marcar_candidato_no_mesmo_commit_ja_esta_feito(mundo):
    _pasta_plugin(mundo, BOM)
    assert _rodar(mundo, "marcar", "candidato", "main", "-m", NOTA) == OK
    assert _rodar(mundo, "marcar", "candidato", "main", "-m", NOTA) == OK
    assert _tags(mundo, "candidato-*") == ["candidato-1"]


def test_marcar_sem_a_pasta_do_plugin_nao_marca_nada(mundo, capsys):
    assert _rodar(mundo, "marcar", "candidato", "main", "-m", NOTA) == FALHA
    assert "a pasta só existe no checkout principal" in capsys.readouterr().out
    assert _tags(mundo, "candidato-*") == [] and not (mundo.raiz / "data").exists()
    assert not (mundo.raiz / "logs").exists() and not mundo.copias.exists()


def test_marcar_nao_sobrescreve_copia_diferente(mundo, capsys):
    _copia(mundo, {**BOM, "Cs2TrackerEvents.pdb": b"outro pdb"})  # mesma DLL, outra pasta
    _pasta_plugin(mundo, BOM)
    assert _rodar(mundo, "marcar", "candidato", "main", "-m", NOTA) == FALHA
    assert "já existe e não é esta pasta" in capsys.readouterr().out
    assert (mundo.copias / _sha(b"dll boa") / "Cs2TrackerEvents.pdb").read_bytes() == b"outro pdb"
    assert _tags(mundo, "candidato-*") == []


def test_marcar_reaproveita_copia_que_confere(mundo):
    _copia(mundo)
    _pasta_plugin(mundo, BOM)
    assert _rodar(mundo, "marcar", "candidato", "main", "-m", NOTA) == OK
    assert _tags(mundo, "candidato-*") == ["candidato-1"]


def test_marcar_seco_nao_cria_nada(mundo, capsys):
    _pasta_plugin(mundo, BOM)
    assert _rodar(mundo, "marcar", "candidato", "main", "-m", NOTA, "--seco") == OK
    saida = capsys.readouterr().out
    assert _tags(mundo, "candidato-*") == [] and not mundo.copias.exists()
    assert not (mundo.raiz / "logs").exists() and not (mundo.raiz / "data").exists()
    assert "[seco] git tag -a candidato-1" in saida and "[seco] escreveria data/candidato.json" in saida


# ---------------------------------------------------------- --seco

def test_voltar_seco_nao_muda_nada(mundo, capsys):
    _commit(mundo.raiz, "cfg", {CFG: "bot_quota 5\n"})
    (mundo.raiz / RUNTIME).write_text('{"matchid": 99}\n')
    antes = _head(mundo)
    assert _rodar(mundo, "voltar", "--seco") == OK
    saida = capsys.readouterr().out
    assert _head(mundo) == antes and (mundo.raiz / RUNTIME).read_text() == '{"matchid": 99}\n'
    assert not (mundo.raiz / "logs").exists()
    assert mundo.docker == ["compose config --format json"]
    for linha in ("[seco] git switch --detach jogavel-2026-09-26", "[seco] docker logs -t cs2-spike",
                  "[seco] docker compose up -d --force-recreate"):
        assert linha in saida


def test_executor_seco_nao_roda_o_que_muda_e_mede_o_timeout():
    chamados, tempo = [], iter([10.0, 15.5])

    def rodar(argv, **kw):
        chamados.append(argv)
        raise subprocess.TimeoutExpired(argv, kw["timeout"])
    ex = Executor(Path("."), seco=True, rodar=rodar, relogio=lambda: next(tempo))
    assert ex.docker("compose", "up", muda=True).seco and chamados == []
    ch = ex.docker("ps", timeout=5)
    assert (ch.codigo, ch.erro, ch.segundos) == (None, "sem resposta em 5 s", 5.5)
    assert len(ex.historico) == 2


# ------------------------------------------------------- atualizar

def _publicar(mundo, arquivos):
    _git(mundo.raiz, "switch", "-q", "-c", "outro")
    sha = _commit(mundo.raiz, "novo", arquivos)
    _git(mundo.raiz, "push", "-q", "origin", "outro:main")
    _git(mundo.raiz, "switch", "-q", "main")
    _git(mundo.raiz, "branch", "-q", "-D", "outro")
    return sha


def test_atualizar_recusa_sem_preflight_livre(mundo, capsys):
    mundo.preflight = 3
    _publicar(mundo, {"start_match.py": "v = 3\n"})
    antes = _head(mundo)
    assert _rodar(mundo, "atualizar") == PARTIDA
    assert _head(mundo) == antes


def test_atualizar_recusa_infra_sem_janela(mundo, capsys):
    _publicar(mundo, {"docker-compose.yml": "services: {b: {}}\n"})
    antes = _head(mundo)
    assert _rodar(mundo, "atualizar") == RECUSA
    assert _head(mundo) == antes
    assert "toca infra e não há janela aberta: docker-compose.yml" in capsys.readouterr().out


def test_atualizar_com_janela_traz_infra_e_manda_recriar(mundo, capsys):
    mundo.preflight = 4
    novo = _publicar(mundo, {CFG: "bot_quota 7\n"})
    assert _rodar(mundo, "atualizar") == OK
    assert _head(mundo) == novo
    assert "recrie com `docker compose up -d --force-recreate`" in capsys.readouterr().out


def test_atualizar_so_python_avisa_para_reabrir(mundo, capsys):
    novo = _publicar(mundo, {"start_match.py": "v = 3\n"})
    assert _rodar(mundo, "atualizar") == OK
    assert _head(mundo) == novo
    assert (mundo.raiz / RUNTIME).read_text() == '{"matchid": 99}\n'
    assert "Reabra a TUI e o uvicorn." in capsys.readouterr().out


def test_atualizar_merge_falho_volta_ao_head_destacado(mundo, capsys):
    # A main local divergiu da origin/main: o switch main passa, o merge
    # --ff-only falha, e o checkout não pode ficar na main local.
    _publicar(mundo, {"start_match.py": "v = 3\n"})
    _commit(mundo.raiz, "local", {"notas.txt": "só aqui\n"})
    _git(mundo.raiz, "switch", "-q", "--detach", "jogavel-2026-09-26")
    assert _rodar(mundo, "atualizar") == FALHA
    saida = capsys.readouterr().out
    assert "falhou: git merge --ff-only origin/main" in saida
    assert "voltei ao HEAD de antes (destacado em " in saida
    assert _head(mundo) == _tag(mundo)
    assert _git(mundo.raiz, "branch", "--show-current") == ""
    assert (mundo.raiz / RUNTIME).read_text() == '{"matchid": 99}\n'


def test_atualizar_seco_so_mostra(mundo, capsys):
    _publicar(mundo, {"start_match.py": "v = 3\n"})
    antes = _head(mundo)
    assert _rodar(mundo, "atualizar", "--seco") == OK
    assert _head(mundo) == antes
    assert "[seco] git merge --ff-only origin/main" in capsys.readouterr().out


# ------------------------------------------------- status e janela

def test_status_so_le(mundo, capsys):
    marca = mundo.raiz / "logs" / "janelas" / "ABERTA"
    marca.parent.mkdir(parents=True)
    marca.touch()
    os.utime(marca, (AGORA - 600, AGORA - 600))
    antes = _head(mundo)
    assert _rodar(mundo, "status") == OK
    saida = capsys.readouterr().out
    assert "última jogável: jogavel-2026-09-26; HEAD está 1 commit(s) à frente dela" in saida
    assert "janela: aberta há 10 min" in saida and "pre.sh: LF" in saida
    assert "runtime file: M docker/match_config.spike.json" in saida
    assert "container cs2-spike: Up 2 hours" in saida
    # origin/main igual ao HEAD: sem delta, nem o compose config roda
    assert _head(mundo) == antes
    assert mundo.docker == ["ps -a --filter name=^cs2-spike$ --format {{.Status}}"]


# ---------------------------------------------------------- janela

class Relogio:
    """Relógio de parede falso; `dormir` avança o tempo e pode mexer no
    mundo no n-ésimo sono (processo que aparece, marca apagada)."""

    def __init__(self, t=AGORA):
        self.t, self.sonos, self.no_sono = t, [], {}

    def __call__(self):
        return self.t

    def dormir(self, s):
        self.sonos.append(s)
        self.t += s
        self.no_sono.get(len(self.sonos), lambda: None)()


def _janela(mundo, *argv, rel=None):
    rel = rel or Relogio()
    mundo.relogio = rel

    def fabrica(raiz, seco=False):
        return Executor(raiz, seco=seco, rodar=mundo.rodar, relogio=rel, dormir=rel.dormir)
    return main(["--raiz", str(mundo.raiz), "janela", *argv], fabrica=fabrica, relogio=rel,
                entrada=lambda t: pytest.fail(f"não devia perguntar: {t}"))


MARCA = "logs/janelas/ABERTA"
REGISTRO = "logs/janelas/teste.md"


def _marca(mundo, idade_s, **dados):
    base = {"head": _head(mundo), "teto_min": 45, "container": "Up 2 hours", "registro": REGISTRO}
    marca = mundo.raiz / MARCA
    marca.parent.mkdir(parents=True, exist_ok=True)
    marca.write_text(json.dumps({**base, **dados}))
    os.utime(marca, (AGORA - idade_s, AGORA - idade_s))
    return marca


def _registro(mundo, rel=REGISTRO):
    arquivo = mundo.raiz / rel
    return arquivo.read_text(encoding="utf-8") if arquivo.exists() else ""


def test_abrir_cria_marca_com_mtime_da_abertura_e_registro(mundo):
    assert _janela(mundo, "abrir", "--por", "pode mexer no servidor", "--teto", "30") == OK
    marca = mundo.raiz / MARCA
    assert marca.stat().st_mtime == AGORA
    dados = json.loads(marca.read_text(encoding="utf-8"))
    assert (dados["por"], dados["teto_min"], dados["head"], dados["container"]) == (
        "pode mexer no servidor", 30, _head(mundo), "Up 2 hours")
    registro = _registro(mundo, f"logs/janelas/{datetime.fromtimestamp(AGORA):%Y-%m-%d}.md")
    assert '- Aberta por: "pode mexer no servidor" · teto 30 min' in registro
    assert f"- Checkout: main {_head(mundo)[:9]} · container cs2-spike: Up 2 hours" in registro
    assert f"(vence {datetime.fromtimestamp(AGORA + 1800):%H:%M:%S})" in registro


def test_abrir_recusa_com_preflight_3(mundo, capsys):
    mundo.preflight = 3
    assert _janela(mundo, "abrir", "--por", "terminei") == PARTIDA
    assert not (mundo.raiz / "logs").exists()
    assert "precisa de preflight 0" in capsys.readouterr().out


@pytest.mark.parametrize("idade_s,estado", [(600, "aberta há 10 min"), (50 * 60, "vencida")])
def test_abrir_recusa_com_marca_existente_e_nao_renova(mundo, capsys, idade_s, estado):
    marca = _marca(mundo, idade_s)
    assert _janela(mundo, "abrir", "--por", "pode mexer no servidor") == RECUSA
    assert marca.stat().st_mtime == AGORA - idade_s
    assert f"abrir recusado: janela {estado}" in capsys.readouterr().out


def test_abrir_sem_frase_do_victor_recusa(mundo):
    assert _janela(mundo, "abrir") == RECUSA
    assert not (mundo.raiz / MARCA).exists()


def test_abrir_seco_nao_cria_nada(mundo, capsys):
    assert _janela(mundo, "abrir", "--seco", "--por", "terminei") == OK
    assert not (mundo.raiz / "logs").exists()
    saida = capsys.readouterr().out
    assert "[seco] criaria logs/janelas/ABERTA" in saida and '+= - Aberta por: "terminei"' in saida


def test_janela_recusa_fora_do_checkout_principal(mundo, tmp_path, capsys):
    wt = tmp_path / "wt"
    _git(mundo.raiz, "worktree", "add", "-q", "--detach", str(wt), "main")
    mundo.raiz = wt
    assert _janela(mundo, "abrir", "--por", "terminei") == RECUSA
    assert not (wt / "logs").exists() and "não é o checkout principal" in capsys.readouterr().out


TODOS = ("--feito", "matchzy", "--feito", "cvars", "--feito", "sha256")


def test_fechar_recusa_com_checklist_pendente(mundo, capsys):
    marca = _marca(mundo, 600)
    assert _janela(mundo, "fechar", "--feito", "cvars") == RECUSA
    saida = capsys.readouterr().out
    assert marca.exists() and marca.stat().st_mtime == AGORA - 600
    assert "[FALTA] matchzy (à mão)" in saida and "[ok] cvars (à mão)" in saida
    assert "passe --feito matchzy --feito sha256" in saida and _registro(mundo) == ""


@pytest.mark.parametrize("na_abertura,agora,codigo", [
    ("Up 2 hours", "Exited (137) 1 minute ago", RECUSA),   # parado pela janela
    ("Exited (255) 5 hours ago", "Exited (255) 6 hours ago", OK),  # deixado como estava
    ("Up 2 hours", "Up 3 minutes", OK)])
def test_fechar_confere_o_container(mundo, na_abertura, agora, codigo):
    marca = _marca(mundo, 600, container=na_abertura)
    mundo.container = agora
    assert _janela(mundo, "fechar", *TODOS) == codigo
    assert marca.exists() is (codigo != OK)


def test_fechar_com_pre_sh_crlf_recusa(mundo, capsys):
    _marca(mundo, 600)
    (mundo.raiz / "docker/pre.sh").write_bytes(b"echo pre\r\n")
    assert _janela(mundo, "fechar", *TODOS) == RECUSA
    assert "[FALTA] docker/pre.sh sem '\\r'" in capsys.readouterr().out


def test_fechar_com_checklist_completo_apaga_marca_e_registra(mundo):
    _marca(mundo, 600)
    assert _janela(mundo, "fechar", *TODOS) == OK
    assert not (mundo.raiz / MARCA).exists()
    linha = _registro(mundo)
    assert "(jogavel.py janela fechar): container Up 2 hours · pre.sh LF" in linha
    assert "à mão, pelo servidor: matchzy, cvars, sha256" in linha and "ABERTA removida" in linha


def test_fechar_seco_nao_apaga(mundo, capsys):
    _marca(mundo, 600)
    assert _janela(mundo, "fechar", "--seco", *TODOS) == OK
    assert (mundo.raiz / MARCA).exists() and _registro(mundo) == ""
    assert "[seco] apagaria logs/janelas/ABERTA" in capsys.readouterr().out


@pytest.mark.parametrize("listagem,processos,sinal", [
    ("powershell", [(10, "cs2.exe", None)], "feche o CS2: cs2.exe (PID 10)"),
    ("powershell", [(11, "python.exe", f"{PY} start_match.py")],
     "feche o start_match (terminal da partida): python start_match (PID 11)"),
    ("tasklist", [(4321, "python.exe", None)],
     "sem certeza sobre o watcher: python sem linha de comando legível (PID 4321)")])
def test_vigiar_aborta_quando_aparece_processo_do_victor(mundo, capsys, listagem, processos, sinal):
    _marca(mundo, 600)
    rel = Relogio()
    mundo.listagem, mundo.processos = listagem, [(1, "explorer.exe", None)]

    def aparece():
        mundo.processos = mundo.processos + processos
    rel.no_sono[2] = aparece
    antes = _head(mundo)
    assert _janela(mundo, "vigiar", rel=rel) == PARTIDA
    assert rel.sonos == [30, 30]  # abortou no 3º ciclo, sem esperar mais
    assert f"ABORTO, processo do Victor ({sinal}" in _registro(mundo)
    assert "nada a voltar pelo git" in capsys.readouterr().out and _head(mundo) == antes


@pytest.mark.parametrize("seco", [False, True])
def test_vigiar_aborta_e_volta_ao_checkout_da_abertura(mundo, capsys, seco):
    _git(mundo.raiz, "checkout", "-q", "--", RUNTIME)
    antes = _head(mundo)
    _marca(mundo, 600, head=_tag(mundo))  # na janela o servidor trouxe um commit
    mundo.processos = [(10, "cs2.exe", None)]
    assert _janela(mundo, "vigiar", *(["--seco"] if seco else [])) == PARTIDA
    saida = capsys.readouterr().out
    assert _head(mundo) == (antes if seco else _tag(mundo))
    assert f"voltar --tag {_tag(mundo)[:9]} (checkout da abertura): saída 0" in saida
    assert ("[seco] git switch --detach" in saida) is seco and (_registro(mundo) == "") is seco


@pytest.mark.parametrize("idade_min,teto,sonos,aviso", [
    (44, 45, [30, 30], "faltam 1 min para o teto"),
    (29.5, 30, [30], "faltam 0 min para o teto")])
def test_vigiar_vence_pelo_mtime_da_marca(mundo, idade_min, teto, sonos, aviso):
    marca = _marca(mundo, idade_min * 60, teto_min=teto)
    rel = Relogio()
    assert _janela(mundo, "vigiar", rel=rel) == VENCIDA
    assert rel.sonos == sonos and marca.stat().st_mtime == AGORA - idade_min * 60
    registro = _registro(mundo)
    assert registro.count(aviso) == 1
    assert f"JANELA VENCIDA (marca de {teto} min, teto {teto} min)" in registro


def test_vigiar_ignora_current_jsonl_do_smoke_so_de_bots(mundo):
    # Na janela quem escreve rounds no current.jsonl é o servidor (smoke,
    # changelevel): só processo do Victor aborta.
    _marca(mundo, 44 * 60)
    _current(mundo, ["round_start", "player_hurt"], idade_s=5)
    assert _janela(mundo, "vigiar") == VENCIDA
    assert "ABORTO" not in _registro(mundo)


def test_vigiar_com_docker_preso_vence_sem_contar_ciclos(mundo):
    # O `docker ps` do 1º ciclo "espera aprovação" 20 min: a marca tinha 30
    # min e passa a ter 50. Vence no mesmo ciclo, sem dormir.
    _marca(mundo, 30 * 60)
    mundo.docker_lento = 20 * 60
    rel = Relogio()
    assert _janela(mundo, "vigiar", rel=rel) == VENCIDA
    assert rel.sonos == []
    registro = _registro(mundo)
    assert "ciclo de 1200 s (limite 30 s): `docker ps -a --filter name=^cs2-spike$ " in registro
    assert "levou 1200 s" in registro and "JANELA VENCIDA (marca de 50 min" in registro


def test_vigiar_com_docker_lento_avisa_antes_de_vencer(mundo):
    _marca(mundo, 22 * 60)
    mundo.docker_lento = 20 * 60  # 42 min: faltam 3
    rel = Relogio()
    assert _janela(mundo, "vigiar", rel=rel) == VENCIDA
    # sem dormir depois do ciclo lento; os 3 min restantes em ciclos de 30 s
    assert rel.sonos == [0.0] + [30] * 6
    registro = _registro(mundo).splitlines()
    assert [i for i, l in enumerate(registro) if "ciclo de 1200 s" in l or "faltam 3 min" in l
            or "JANELA VENCIDA" in l] == [0, 1, 2]


def test_vigiar_avisa_container_parado_mais_de_5_min(mundo):
    _marca(mundo, 0, teto_min=10)
    mundo.container = "Exited (137) 1 minute ago"
    assert _janela(mundo, "vigiar") == VENCIDA
    registro = _registro(mundo)
    assert registro.count("container cs2-spike parado há 5 min (máximo ~5 min por passo)") == 1


def test_vigiar_termina_quando_a_marca_some(mundo, capsys):
    marca = _marca(mundo, 60)
    rel = Relogio()
    rel.no_sono[1] = marca.unlink
    assert _janela(mundo, "vigiar", rel=rel) == OK
    assert "marca removida: janela fechada" in capsys.readouterr().out


def test_vigiar_intervalo_acima_de_30_s_e_uso_errado(mundo):
    _marca(mundo, 60)
    assert _janela(mundo, "vigiar", "--intervalo", "31") == jogavel.USO


def test_janela_acao_desconhecida_e_uso_errado(mundo):
    with pytest.raises(SystemExit):
        _rodar(mundo, "janela", "outra")

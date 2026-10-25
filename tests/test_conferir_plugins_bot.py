"""tools/conferir_plugins_bot.py (card B1.13): ELF sintético em tmp_path, nunca o libserver real.

Os bytes de função são escritos à mão a partir do que a 2000930 e a 2000935 têm no
CSmokeGrenadeProjectile::Create (runbook b1.13-plugins-de-bot-2000935.md)."""
import hashlib
import json
import struct
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "tools"))

import conferir_plugins_bot as cpb  # noqa: E402

# Prólogo do Create da smoke até o `lea rdi,[rip+x]`, sem o disp32: 2000935 e 2000930.
SMOKE_935 = bytes.fromhex("55 4C 89 C1 48 89 E5 41 57 41 56 49 89 FE 41 55 45 89 CD 41 54 4D 89 C4 53"
                          " 48 81 EC 78 01 00 00 48 89 95 78 FE FF FF 48 89 F2 48 89 FE 48 8D 3D")
SMOKE_930 = bytes.fromhex("55 4C 89 C1 48 89 E5 41 57 49 89 FF 41 56 45 89 CE 41 55 4D 89 C5 41 54 53"
                          " 48 81 EC 78 01 00 00 48 89 95 78 FE FF FF 48 89 F2 48 89 FE 48 8D 3D")
SMOKE_1_2_1 = "55 4C 89 C1 48 89 E5 41 57 49 89 FF 41 56 45 89 CE 41 55"
TEXT_VA = 0x401000
RODATA_VA = TEXT_VA + 0x10000


def elf(funcoes, strings=(b"smokegrenade_projectile",)):
    """ELF64 com .text (cada função, o disp32 do lea final para a 1ª string, e CC) e .rodata.str1.1."""
    rodata = b"".join(s + b"\0" for s in strings)
    text = b""
    for corpo in funcoes:
        text += corpo
        if corpo.endswith(b"\x8d\x3d"):
            text += struct.pack("<i", RODATA_VA - (TEXT_VA + len(text) + 4))
        text += b"\xcc" * 16
    nomes = b"\0.text\0.rodata.str1.1\0.shstrtab\0"
    o_text, o_ro = 0x40, 0x40 + len(text)
    o_nomes = o_ro + len(rodata)
    cab = bytearray(b"\x7fELF\x02\x01\x01" + b"\0" * 57)
    struct.pack_into("<Q", cab, 0x28, o_nomes + len(nomes))
    struct.pack_into("<HHH", cab, 0x3A, 64, 4, 3)
    sh = b"\0" * 64
    for nome, end, off, tam in ((1, TEXT_VA, o_text, len(text)), (7, RODATA_VA, o_ro, len(rodata)),
                                (22, 0, o_nomes, len(nomes))):
        sh += struct.pack("<IIQQQQIIQQ", nome, 1, 0, end, off, tam, 0, 0, 1, 0)
    return bytes(cab) + text + rodata + nomes + sh


def conferir(dados, nome):
    n, t, v = next((n, t, v) for _p, n, t, v in cpb.ASSINATURAS if n == nome)
    return cpb.conferir_entrada(dados, cpb.secoes(dados), n, t, v)


def test_a_assinatura_nova_da_smoke_e_a_do_patch():
    assert cpb.SMOKE_B113 == ("55 4C 89 C1 48 89 E5 41 57 ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? "
                              "48 81 EC 78 01 00 00 48 89 95 78 FE FF FF 48 89 F2 48 89 FE 48 8D 3D")


def test_smoke_da_2000935_casa_1_vez_com_a_ancora_e_a_do_1_2_1_nao_casa():
    dados = elf([SMOKE_935])
    estado, linha = conferir(dados, "CSmokeGrenadeProjectile::Create")
    assert estado == "OK"
    assert "arquivo 0x40;" in linha and "smokegrenade_projectile" in linha
    assert cpb.casamentos(dados, cpb.secoes(dados), SMOKE_1_2_1) == []


def test_a_nova_tambem_casa_na_forma_da_2000930():
    dados = elf([SMOKE_930])
    assert cpb.casamentos(dados, cpb.secoes(dados), SMOKE_1_2_1) == [0x40]
    assert conferir(dados, "CSmokeGrenadeProjectile::Create")[0] == "OK"


def test_ancora_errada_e_dois_casamentos_divergem():
    estado, linha = conferir(elf([SMOKE_935], strings=(b"decoy_projectile",)), "CSmokeGrenadeProjectile::Create")
    assert estado == "DIVERGE" and "decoy_projectile" in linha
    estado, linha = conferir(elf([SMOKE_935, SMOKE_930]), "CSmokeGrenadeProjectile::Create")
    assert estado == "DIVERGE" and "2 casamentos" in linha


def test_disp32_do_m_enemy_deslocado_diverge():
    def pick(m_enemy):
        return (bytes.fromhex("55 48 89 E5 41 55 41 54 53 48 89 FB 48 83 EC 58 8B 8F")
                + struct.pack("<I", m_enemy) + bytes.fromhex("83 F9 FF") + struct.pack("<II", 0x59DC, 0x596C))
    assert conferir(elf([pick(0x59D8)]), "CCSBot::PickNewAimSpot")[0] == "OK"
    estado, linha = conferir(elf([pick(0x59D0)]), "CCSBot::PickNewAimSpot")
    assert estado == "DIVERGE" and "0x59d0" in linha


def test_fov_do_botstate_ausente_e_aviso_e_presente_e_ok():
    assert conferir(elf([b"\x90" * 8]), "IsVisiblePlayer_IgnoreFOV")[0] == "AVISO"
    fov = bytes.fromhex("45 84 F6 74 05 49 8B 54 24 18 48 89 DF 48 8B 0A 48 89 55 98"
                        " 48 8B 89 A0 09 00 00 48 89 4D A0 FF 90 B8 02 00 00")
    estado, linha = conferir(elf([fov]), "IsVisiblePlayer_IgnoreFOV")
    assert estado == "OK" and "0x74" in linha


FONTE = '''
        _smokeCreate = new(
            RuntimeInformation.IsOSPlatform(OSPlatform.Linux)
                // B1.13: comentário entre a plataforma e a assinatura
                ? @"{}"
                : @"48 8B C4");
        _heCreate = new(RuntimeInformation.IsOSPlatform(OSPlatform.Linux)
                ? "55 4C 89 C1 48 89 E5 41 57 49 89 FF 41 56 49 89 D6 48 89 F2 48 89 FE 41 55" : "48");
        _molotovCreate = new(RuntimeInformation.IsOSPlatform(OSPlatform.Linux)
                ? "55 48 8D 05 ? ? ? ? 48 89 E5 41 57 41 56 41 55 41 54 49 89 FC 53 48 81 EC ? ? ? ? 4C 8D 35" : "48");
'''


def test_fonte_do_nadesystem_com_a_smoke_antiga_diverge():
    assert cpb.conferir_fonte_nade(FONTE.replace("{}", cpb.SMOKE_B113))[0] == "OK"
    assert cpb.conferir_fonte_nade(FONTE.replace("{}", SMOKE_1_2_1))[0] == "DIVERGE"


def test_compose_monta_o_nadesystem_do_fork_ignorado_e_o_vanilla_o_mascara():
    destino = "/home/steam/cs2-dedicated/game/csgo/addons/counterstrikesharp/plugins/NadeSystem"
    ativas = [ln.strip() for ln in (RAIZ / "docker-compose.yml").read_text(encoding="utf-8").splitlines()
              if ln.strip().startswith("- ./") and ln.rstrip().endswith(destino)]
    assert ativas == [f"- ./docker/plugins/NadeSystem:{destino}"]
    assert f"- ./docker/plugins/_empty:{destino}" in (RAIZ / "docker-compose.vanilla.yml").read_text(encoding="utf-8")
    assert "docker/plugins/NadeSystem/" in (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()


def cli(tmp_path, monkeypatch, dados, botai="RESULTADO: OK", sha=None):
    lib = tmp_path / "libserver.so"
    lib.write_bytes(dados)
    real = hashlib.sha256(dados).hexdigest()
    (tmp_path / "gd.json").write_text(json.dumps({
        "UTIL_Remove": {"signatures": {"library": "server", "linux": "55 4C 89 C1 48 89 E5 41 57"}},
        "X": {"offsets": {"linux": 3}}}))
    (tmp_path / "botai.txt").write_text(f"  1 bytes, sha256 {real}\n\n{botai}\n")
    (tmp_path / "Nade.cs").write_text("fonte")
    smoke = [a for a in cpb.ASSINATURAS if a[1] == "CSmokeGrenadeProjectile::Create"]
    monkeypatch.setattr(cpb, "ASSINATURAS", smoke)
    monkeypatch.setattr(cpb, "conferir_fonte_nade", lambda texto: ("OK", "fonte"))
    monkeypatch.setattr(cpb, "DEPENDE", {"NadeSystem": ["UTIL_Remove", "X"]})
    return cpb.main(["--lib", str(lib), "--sha", sha or real, "--tamanho", str(len(dados)),
                     "--gamedata", str(tmp_path / "gd.json"), "--botai-saida", str(tmp_path / "botai.txt"),
                     "--nadesystem-fonte", str(tmp_path / "Nade.cs")])


def test_cli_ok_sai_0(tmp_path, monkeypatch, capsys):
    assert cli(tmp_path, monkeypatch, elf([SMOKE_935])) == 0
    saida = capsys.readouterr().out
    assert "PLUGIN NadeSystem: OK" in saida and saida.rstrip().endswith("RESULTADO: OK")


def test_cli_botai_sem_ok_ou_gamedata_quebrado_sai_1(tmp_path, monkeypatch, capsys):
    assert cli(tmp_path, monkeypatch, elf([SMOKE_935]), botai="RESULTADO: DIVERGE") == 1
    assert cli(tmp_path, monkeypatch, elf([b"\x90" * 32])) == 1
    saida = capsys.readouterr().out
    assert "UTIL_Remove (0 casamentos)" in saida and "RESULTADO: DIVERGE" in saida


def test_cli_sha_errado_sai_2(tmp_path, monkeypatch):
    assert cli(tmp_path, monkeypatch, elf([SMOKE_935]), sha="0" * 64) == 2

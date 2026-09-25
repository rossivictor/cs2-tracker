#!/usr/bin/env python3
"""
Extrai o metadado de radar de cada mapa do CS2 e grava data/map_radar.json.

É o que permite plotar uma posição do mundo em cima da imagem 2D do mapa: a
conversão precisa de `pos_x`/`pos_y` (coordenada de mundo do canto superior
esquerdo da imagem) e `scale` (unidades de mundo por pixel), que o jogo
guarda em `resource/overviews/<mapa>.txt`, dentro do pak01_dir.vpk.

Ao contrário de roster.read_vpk_profile_templates, que acha os perfis com
regex direto nos bytes, aqui o VPK é percorrido de verdade: o conteúdo dos
overviews não mora no _dir.vpk, e sim nos pak01_NNN.vpk ao lado, no offset
que o índice aponta. Sem ler o índice não dá pra chegar no arquivo.

A saída é um snapshot versionado em data/, na mesma linha de
data/rosters.json: o app lê o JSON e não depende do CS2 estar instalado.
Rode de novo quando a Valve mexer no radar de algum mapa.

Uso:
    .venv\\Scripts\\python.exe tools/extract_map_radar.py [--cs2-dir <path>]
"""
import argparse
import json
import re
import struct
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

VPK_SIGNATURE = 0x55AA1234
OVERVIEW_PREFIX = "resource/overviews"
OUT_PATH = ROOT / "data" / "map_radar.json"

# Onde o CS2 costuma estar. Dá pra passar --cs2-dir quando não for nenhum.
DEFAULT_CS2_DIRS = [
    Path(r"C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive/game/csgo"),
    Path(r"D:/Steam/steamapps/common/Counter-Strike Global Offensive/game/csgo"),
    Path(r"C:/SteamLibrary/steamapps/common/Counter-Strike Global Offensive/game/csgo"),
    Path.home() / ".steam/steam/steamapps/common/Counter-Strike Global Offensive/game/csgo",
]


def _cstring(buf: bytes, i: int):
    end = buf.index(b"\x00", i)
    return buf[i:end].decode("utf-8", "replace"), end + 1


def read_vpk_index(dir_vpk: Path):
    """Índice do VPK: {caminho: (archive, offset, length, preload, data_base)}.

    Formato: para cada extensão, para cada pasta, para cada arquivo — três
    laços aninhados terminados por string vazia."""
    raw = dir_vpk.read_bytes()
    signature, version, tree_size = struct.unpack_from("<III", raw, 0)
    if signature != VPK_SIGNATURE:
        raise SystemExit(f"[ERRO] {dir_vpk} não é um VPK (assinatura {signature:#x})")
    header_size = 12 if version == 1 else 28

    i = header_size
    tree_end = header_size + tree_size
    entries = {}
    while i < tree_end:
        extension, i = _cstring(raw, i)
        if not extension:
            break
        while True:
            folder, i = _cstring(raw, i)
            if not folder:
                break
            while True:
                name, i = _cstring(raw, i)
                if not name:
                    break
                _crc, preload_len, archive, offset, length, _term = struct.unpack_from(
                    "<IHHIIH", raw, i
                )
                i += 18
                preload = raw[i:i + preload_len]
                i += preload_len
                entries[f"{folder}/{name}.{extension}"] = (
                    archive, offset, length, preload, tree_end
                )
    return raw, entries


def read_vpk_file(dir_vpk: Path, raw: bytes, entry) -> bytes:
    archive, offset, length, preload, data_base = entry
    if length == 0:
        return preload
    if archive == 0x7FFF:  # 0x7fff = o conteúdo está no próprio _dir.vpk
        return preload + raw[data_base + offset: data_base + offset + length]
    side = dir_vpk.parent / dir_vpk.name.replace("_dir", f"_{archive:03d}")
    with open(side, "rb") as fh:
        fh.seek(offset)
        return preload + fh.read(length)


def _number(text, key):
    match = re.search(rf'"{key}"\s+"(-?[\d.]+)"', text)
    return float(match.group(1)) if match else None


def parse_overview(text: str):
    """pos_x/pos_y/scale e, quando o mapa tem dois níveis (Nuke, Vertigo), a
    altitude que separa o radar de cima do de baixo.

    `rotate` e `zoom` existem no arquivo e NÃO são usados: a imagem que o
    jogo distribui já vem na orientação final. É o mesmo que o awpy faz em
    awpy.plot.utils.game_to_pixel_axis, que é a implementação de referência
    desta conversão."""
    pos_x, pos_y, scale = _number(text, "pos_x"), _number(text, "pos_y"), _number(text, "scale")
    if pos_x is None or pos_y is None or not scale:
        return None
    lower = re.search(r'"lower".*?"AltitudeMax"\s+"(-?[\d.]+)"', text, re.S)
    return {
        "pos_x": pos_x,
        "pos_y": pos_y,
        "scale": scale,
        # A imagem oficial de radar é 1024x1024, então a área coberta é
        # scale*1024 unidades de mundo. Guardado explícito pra quem consome
        # não precisar saber disso de cor.
        "image_size": 1024,
        "lower_level_max_units": float(lower.group(1)) if lower else None,
    }


def find_cs2_dir(explicit=None):
    candidates = [Path(explicit)] if explicit else DEFAULT_CS2_DIRS
    for path in candidates:
        if (path / "pak01_dir.vpk").exists():
            return path
    raise SystemExit(
        "[ERRO] Não achei o pak01_dir.vpk do CS2. Passe --cs2-dir apontando pra "
        "…/Counter-Strike Global Offensive/game/csgo"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cs2-dir", default=None)
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args()

    cs2_dir = find_cs2_dir(args.cs2_dir)
    dir_vpk = cs2_dir / "pak01_dir.vpk"
    print(f"[INFO] Lendo {dir_vpk}")

    raw, entries = read_vpk_index(dir_vpk)
    overviews = {
        key.rsplit("/", 1)[-1][:-4]: entry
        for key, entry in entries.items()
        if key.startswith(OVERVIEW_PREFIX)
    }
    print(f"[INFO] {len(overviews)} overview(s) no VPK.")

    maps = {}
    for map_name, entry in sorted(overviews.items()):
        text = read_vpk_file(dir_vpk, raw, entry).decode("utf-8", "replace")
        data = parse_overview(text)
        if data is None:
            print(f"[PULA] {map_name}: overview sem pos_x/pos_y/scale")
            continue
        maps[map_name] = data
        extra = ""
        if data["lower_level_max_units"] is not None:
            extra = f"  nível inferior abaixo de z={data['lower_level_max_units']:.0f}"
        print(f"  {map_name:<18} pos=({data['pos_x']:.0f}, {data['pos_y']:.0f}) "
              f"scale={data['scale']}{extra}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "snapshot_date": date.today().isoformat(),
                "source": "resource/overviews/*.txt (pak01_dir.vpk do CS2)",
                "maps": maps,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"\n[OK] {len(maps)} mapa(s) em {out}")


if __name__ == "__main__":
    main()

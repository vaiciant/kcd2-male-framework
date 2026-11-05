"""Generates the head and beard meshes that are hidden in first person.

NPC heads are seen from the inside in first person. fp_mask.py, next to this file, copies the mask
of Henry's head, and the mesh goes in the same path as the vanilla one. The beards of those heads
are seen too: they are copied with the first-person bit off, as Henry's come, only
in their highest detail. The heads and the initial beards come from the STORM rules of the mod, and the other beards
from barber.toml, so a new model does not require touching this file.
The meshes derive from game files: they are not versioned (.gitignore).

Usage, from the repository root: python -I mod/kcd_male_framework/tools/generate_heads.py mod/kcd_male_framework
"""
import importlib.util
import os
import pathlib
import re
import shutil
import sys
import tomllib
import zipfile

# KCD2_GAME, or the game in the default Steam library, or in the maintainer's.
GAME_PLACES = (r"C:\Program Files (x86)\Steam\steamapps\common\KingdomComeDeliverance2", r"E:\SteamLibrary\steamapps\common\KingdomComeDeliverance2")
GAME = pathlib.Path(os.environ.get("KCD2_GAME") or next((p for p in GAME_PLACES if os.path.isfile(os.path.join(p, "Data", "Tables.pak"))), GAME_PLACES[0]))
HEADS = "objects/characters/humans/male/head"
# In first person the character is always seen with the highest detail: the other beards do not need to be hidden, and
# they are half of the size.
LODS = ("",)
# No mesh: there is nothing to hide.
DUMMY_BEARD = "m_beard_00"

_spec = importlib.util.spec_from_file_location("fp_mask", pathlib.Path(__file__).resolve().with_name("fp_mask.py"))
fp_mask = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fp_mask)


def pak_index() -> dict:
    """Lowercase path of each head file, with its pak: the paks are opened only once."""
    index = {}
    for pak_path in sorted((GAME / "Data").glob("IPL_Heads-part*.pak")) + [GAME / "Data" / "Heads.pak"]:
        if pak_path.is_file():
            with zipfile.ZipFile(pak_path) as pak:
                for name in pak.namelist():
                    index.setdefault(name.replace("\\", "/").lower(), (pak_path, name))
    return index


def read(index: dict, path: str) -> bytes:
    pak_path, name = index[path]
    with zipfile.ZipFile(pak_path) as pak:
        return pak.read(name)


def main() -> None:
    mod_dir = pathlib.Path(sys.argv[1])
    rules = (mod_dir / f"data/Libs/Storm/appearance/{mod_dir.resolve().name}.xml").read_text(encoding="utf-8")
    # Each head with the barber's beards (barber.toml) and the initial one of its models: not all of the game's.
    barber_beards = {beard["mesh"] for beard in tomllib.loads((mod_dir / "barber.toml").read_text(encoding="utf-8"))["beard"]}
    beards_of = {}
    for rule in re.findall(r"<rule .*?</rule>", rules, re.S):
        head = re.search(r'<setHead name="(m_head_[a-z0-9]+)"', rule)
        if head:
            beards_of.setdefault(head.group(1), set(barber_beards)).update(re.findall(r'<setBeard name="(m_beard_\d+)"', rule))
    heads = sorted(beards_of)
    index = pak_index()
    henry = read(index, f"{HEADS}/{fp_mask.HENRY}/{fp_mask.HENRY}.skin")
    for head in heads:
        out_dir = mod_dir / f"data/Objects/characters/humans/male/head/{head}"
        out_dir.mkdir(parents=True, exist_ok=True)
        result, stats = fp_mask.make(henry, read(index, f"{HEADS}/{head}/{head}.skin"))
        (out_dir / f"{head}.skin").write_bytes(result)
        print(f"{head}: {stats}")
        if stats["no_uv"]:
            print("WARNING: some head vertices have no matching UV in Henry; check them")
        hidden = 0
        shutil.rmtree(out_dir / "beards", ignore_errors=True)
        for beard in sorted(beards_of[head] - {DUMMY_BEARD}):
            for lod in LODS:
                path = f"{HEADS}/{head}/beards/{beard}{lod}.skin"
                if path in index:
                    (out_dir / "beards").mkdir(exist_ok=True)
                    (out_dir / f"beards/{beard}{lod}.skin").write_bytes(fp_mask.hide(read(index, path)))
                    hidden += 1
        print(f"{head}: {hidden} beard meshes hidden in first person")
    print(f"{len(heads)} heads")


if __name__ == "__main__":
    main()

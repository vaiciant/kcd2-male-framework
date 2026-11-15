"""A stand-in for a head of your own, to try make_face_pack.py before you have one (MAKING_FACES.md).

It copies a head of the game into source/ the way your own head goes there: the head and its LODs, its face poses, its
beards with their LODs, and its material, whose textures keep pointing at the game's. source/ is only what you give the
tool: the mod is what the tool writes from it. Your own head is not the game's, so it has no need of this file.

Usage, from the root of the framework's repository:
    python -I -X utf8 mod/kcd_male_framework/examples/sample_men_own_head/stand_in.py
"""
import os
import pathlib
import re
import zipfile

GAME_PLACES = (r"C:\Program Files (x86)\Steam\steamapps\common\KingdomComeDeliverance2", r"E:\SteamLibrary\steamapps\common\KingdomComeDeliverance2")
GAME = pathlib.Path(os.environ.get("KCD2_GAME") or next((p for p in GAME_PLACES if os.path.isfile(os.path.join(p, "Data", "Tables.pak"))), GAME_PLACES[0]))
HEAD = "m_head_008"
FOLDER = f"objects/characters/humans/male/head/{HEAD}/"
OUT = pathlib.Path(__file__).resolve().parent / "source" / HEAD
FILES = re.compile(rf"{HEAD}(_lod\d)?\.skin|{HEAD}_poses\.xml|beards/m_beard_\d+(_lod\d)?\.skin")


def main():
    written = 0
    for pak in sorted((GAME / "Data").glob("*Head*.pak")):
        with zipfile.ZipFile(pak) as archive:
            for name in archive.namelist():
                path = name.replace("\\", "/").lower()
                rest = path[len(FOLDER):] if path.startswith(FOLDER) else ""
                if FILES.fullmatch(rest):
                    target = OUT / rest
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(name))
                    written += 1
                elif rest == f"{HEAD}_m01.mtl":
                    OUT.mkdir(parents=True, exist_ok=True)
                    text = archive.read(name).decode("utf-8")
                    (OUT / f"{HEAD}.mtl").write_text(text.replace('File="./', f'File="{FOLDER}'), encoding="utf-8")
                    written += 1
    if not written:
        raise SystemExit(f"{HEAD} is not in the game's paks in {GAME}: KCD2_GAME is the folder of the game")
    print(f"{OUT}: {written} files")


if __name__ == "__main__":
    main()

"""Extracts the game's tables that the generators read, into game_files/.

The generators read some of the game's own files as plain files: the tables of Tables.pak (Libs/Tables) and the STORM
rules of IPL_GameData.pak (Libs/Storm). They belong to Warhorse, so they are not in the repository: this tool takes them
from your copy of the game. Run it once before building, and again after a game update. It only writes inside
game_files/, which git ignores.

Usage, from the root of the repository:
    python -I tools/extract_game.py

Game path: KCD2_GAME, or the default Steam library, or the maintainer's.
"""
import os
import pathlib
import shutil
import sys
import zipfile

# KCD2_GAME, or the game in the default Steam library, or in the maintainer's.
GAME_PLACES = (r"C:\Program Files (x86)\Steam\steamapps\common\KingdomComeDeliverance2", r"E:\SteamLibrary\steamapps\common\KingdomComeDeliverance2")
GAME = pathlib.Path(os.environ.get("KCD2_GAME") or next((p for p in GAME_PLACES if os.path.isfile(os.path.join(p, "Data", "Tables.pak"))), GAME_PLACES[0]))
PROJECT = pathlib.Path(__file__).resolve().parent.parent
# The folder names are the ones the generators expect: one folder per pak, with the paths inside it.
OUT = PROJECT / "game_files"
PARTS = (
    ("Tables.pak", "Libs/Tables/", "Tables.pak"),
    ("IPL_GameData.pak", "Libs/Storm/", "IPL_GameData_storm"),
)


def main() -> int:
    if not (GAME / "Data" / "Tables.pak").is_file():
        raise SystemExit(f"The game is not in {GAME}. Set KCD2_GAME to the folder of Kingdom Come: Deliverance II.")
    for pak, prefix, folder in PARTS:
        dest = OUT / folder
        written = 0
        with zipfile.ZipFile(GAME / "Data" / pak) as z:
            for info in z.infolist():
                name = info.filename.replace("\\", "/")
                if info.is_dir() or not name.lower().startswith(prefix.lower()):
                    continue
                target = (dest / name).resolve()
                # A name with ".." must not write outside the folder.
                if not str(target).startswith(str(dest.resolve())):
                    raise SystemExit(f"{pak}: {name} points outside {dest}")
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as source, open(target, "wb") as out:
                    shutil.copyfileobj(source, out)
                written += 1
        print(f"{pak}: {written} files in {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

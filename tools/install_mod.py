"""Packs a mod with build_mod.py and copies it into the game's Mods folder.

It touches the game folder: run it only with the user's OK.

It does not change mod_order.txt; to enable the mod use tools/mod_profile.py clean <modid>.
It only replaces an existing folder in Mods/ if its mod.manifest has the same modid.

Usage:
    python -I tools/install_mod.py <source_folder>
Example:
    python -I tools/install_mod.py mod/medieval_life

Game path: KCD2_GAME, or the default Steam library, or the maintainer's.
"""
import os
import pathlib
import shutil
import subprocess
import sys

# KCD2_GAME, or the game in the default Steam library, or in the maintainer's.
GAME_PLACES = (r"C:\Program Files (x86)\Steam\steamapps\common\KingdomComeDeliverance2", r"E:\SteamLibrary\steamapps\common\KingdomComeDeliverance2")
GAME = pathlib.Path(os.environ.get("KCD2_GAME") or next((p for p in GAME_PLACES if os.path.isfile(os.path.join(p, "Data", "Tables.pak"))), GAME_PLACES[0]))
PROJECT = pathlib.Path(__file__).resolve().parent.parent

sys.path.insert(0, str(PROJECT / "tools"))
from build_mod import read_modid  # noqa: E402


def game_running() -> bool:
    # With the game open the .pak is in use: deleting it halfway would leave the mod broken.
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq KingdomCome.exe", "/NH"],
                         capture_output=True, text=True).stdout
    return "KingdomCome.exe" in out


def build(src: pathlib.Path, build_root: pathlib.Path) -> pathlib.Path:
    """Runs the mod's data generators and packs it. Returns the built folder, build_root/<modid>. package_mods.py uses
    it too."""
    # Origins, jobs and orders each come from one file: whatever was edited there goes in with no extra steps. Each mod
    # brings its generators in its own tools/ folder. The recipes come from the game, with the pictures of their pages,
    # which are not in the repository, and so do the drinks of KCD2 Tavern Nights.
    for source, tool in (("origins.toml", "generate_origins.py"), ("jobs.toml", "generate_jobs.py"), ("orders.toml", "generate_orders.py"),
                         ("tools/generate_recipes.py", "generate_recipes.py"), ("tools/generate_drinks.py", "generate_drinks.py"),
                         ("tools/collect_voice.py", "collect_voice.py")):
        if (src / source).is_file():
            subprocess.run([sys.executable, "-I", "-X", "utf8", str(src / "tools" / tool), str(src)], check=True)

    subprocess.run([sys.executable, "-I", str(PROJECT / "tools" / "build_mod.py"), str(src), str(build_root)],
                   check=True)
    return build_root / read_modid(src / "mod.manifest")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    if game_running():
        raise SystemExit("The game is open (KingdomCome.exe). Close it and run this again.")
    src = pathlib.Path(sys.argv[1]).resolve()
    modid = read_modid(src / "mod.manifest")
    build_root = PROJECT / "build"
    build(src, build_root)

    mods = GAME / "Mods"
    if not mods.is_dir():
        raise SystemExit(f"{mods} does not exist")
    dest = mods / modid
    if dest.exists():
        old = dest / "mod.manifest"
        if not old.is_file() or read_modid(old) != modid:
            raise SystemExit(f"{dest} exists and is not the mod {modid}; left untouched")
        shutil.rmtree(dest)
    shutil.copytree(build_root / modid, dest)
    print(f"Installed in {dest}")

    order = mods / "mod_order.txt"
    lines = order.read_text(encoding="utf-8-sig").splitlines() if order.is_file() else []
    if modid not in (l.strip() for l in lines):
        print(f"WARNING: {modid} is not enabled in mod_order.txt. "
              f"Enable it with: python -I tools/mod_profile.py clean {modid}")
    for copy in workshop_copies(modid):
        print(f"WARNING: the Steam Workshop has {modid} too, in {copy}. The game loads that copy and not the one in Mods/: "
              f"unsubscribe from it in Steam to test this build.")
    return 0


def workshop_copies(modid: str) -> list[pathlib.Path]:
    """The folders of the Steam Workshop with a mod of the same modid. With one, the game opens that copy and leaves
    out the one in Mods/ (kcd.log of 2026-11-07: the published 0.1.0 loaded instead of 0.1.12)."""
    workshop = GAME.parent.parent / "workshop" / "content" / "1771300"
    copies = []
    for manifest in sorted(workshop.glob("*/mod.manifest")) if workshop.is_dir() else []:
        try:
            if read_modid(manifest) == modid:
                copies.append(manifest.parent)
        except (OSError, ValueError, SystemExit):
            continue
    return copies


if __name__ == "__main__":
    sys.exit(main())

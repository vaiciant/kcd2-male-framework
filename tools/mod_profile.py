"""Manages the game's mod profile and the backups of the saves.

It touches the game folder: run it only with the user's OK.

The profile is changed by commenting out lines of Mods/mod_order.txt with "# ", as the
user does by hand. Lines are never deleted: the order and the usual list are kept.
Before each change a dated backup is saved (mod_order.backup_YYYYMMDD_HHMMSS.txt).

Usage:
    python -I tools/mod_profile.py status
    python -I tools/mod_profile.py backup
    python -I tools/mod_profile.py clean <modid> [<modid> ...]
    python -I tools/mod_profile.py restore <backup_file>
    python -I tools/mod_profile.py saves <label> [<playline>]

    status      shows the active mods and the existing backups
    backup      copies mod_order.txt with a date
    clean       leaves only the given modids active (adds them at the end if missing)
    restore     goes back to the given backup (see "status"); it backs up the current file first
    saves       copies the saves into saves_backup/sesion_<date>_<label>/;
                with <playline> (for example playline4) it copies only that save

Default paths (this machine); change them with the variables
KCD2_GAME and KCD2_SAVES.
"""
import datetime
import os
import pathlib
import re
import shutil
import sys

# KCD2_GAME, or the game in the default Steam library, or in the maintainer's.
GAME_PLACES = (r"C:\Program Files (x86)\Steam\steamapps\common\KingdomComeDeliverance2", r"E:\SteamLibrary\steamapps\common\KingdomComeDeliverance2")
GAME = pathlib.Path(os.environ.get("KCD2_GAME") or next((p for p in GAME_PLACES if os.path.isfile(os.path.join(p, "Data", "Tables.pak"))), GAME_PLACES[0]))
SAVES = pathlib.Path(os.environ.get("KCD2_SAVES", r"C:\Users\ziyo\Saved Games\kingdomcome2\saves"))
PROJECT = pathlib.Path(__file__).resolve().parent.parent
ORDER = GAME / "Mods" / "mod_order.txt"
MODID_RE = re.compile(r"[a-z0-9_]+")


def stamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def read_lines() -> list[str]:
    if not ORDER.is_file():
        raise SystemExit(f"{ORDER} does not exist")
    return ORDER.read_text(encoding="utf-8-sig").splitlines()


def active(lines: list[str]) -> list[str]:
    return [l.strip() for l in lines if l.strip() and not l.lstrip().startswith("#")]


def backups() -> list[pathlib.Path]:
    return sorted(ORDER.parent.glob("mod_order.backup_*.txt"))


def make_backup() -> pathlib.Path:
    dest = ORDER.parent / f"mod_order.backup_{stamp()}.txt"
    shutil.copy2(ORDER, dest)
    print(f"Backup: {dest.name}")
    return dest


def write_lines(lines: list[str]) -> None:
    ORDER.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_status() -> None:
    lines = read_lines()
    act = active(lines)
    print(f"{ORDER}")
    print(f"Active ({len(act)}): {', '.join(act) if act else '(none)'}")
    print(f"Commented out: {len(lines) - len(act) - sum(1 for l in lines if not l.strip())}")
    for b in backups():
        print(f"  backup: {b.name}")


def cmd_clean(modids: list[str]) -> None:
    for m in modids:
        if not MODID_RE.fullmatch(m):
            raise SystemExit(f"invalid modid: {m}")
    lines = read_lines()
    make_backup()
    out, seen = [], set()
    for line in lines:
        name = line.lstrip("#").strip()
        if not name:
            out.append(line)
        elif name in modids and name not in seen:
            out.append(name)
            seen.add(name)
        elif line.lstrip().startswith("#"):
            out.append(line)
        else:
            out.append(f"# {name}")
    out.extend(m for m in modids if m not in seen)
    write_lines(out)
    print(f"Active now: {', '.join(active(out))}")


def cmd_restore(name: str) -> None:
    src = ORDER.parent / pathlib.Path(name).name
    if not src.is_file():
        raise SystemExit(f"{src} does not exist")
    make_backup()
    shutil.copy2(src, ORDER)
    print(f"Restored from {src.name}. Active: {', '.join(active(read_lines())) or '(none)'}")


def cmd_saves(label: str, playline: str | None) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", label):
        raise SystemExit("The label only allows letters, digits, '_' and '-'")
    src = SAVES / playline if playline else SAVES
    if playline and not re.fullmatch(r"playline\d+", playline):
        raise SystemExit("The save must have the form playlineN")
    if not src.is_dir():
        raise SystemExit(f"{src} does not exist")
    # The folder keeps its old "sesion_" prefix, so new backups sort with the existing ones.
    dest = PROJECT / "saves_backup" / f"sesion_{stamp()}_{label}"
    if playline:
        dest = dest / playline
    shutil.copytree(src, dest)
    total = sum(p.stat().st_size for p in dest.rglob("*") if p.is_file())
    print(f"Saves copied to {dest} ({total / 1e6:.1f} MB)")


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    cmd, rest = args[0], args[1:]
    if cmd == "status" and not rest:
        cmd_status()
    elif cmd == "backup" and not rest:
        make_backup()
    elif cmd == "clean" and rest:
        cmd_clean(rest)
    elif cmd == "restore" and len(rest) == 1:
        cmd_restore(rest[0])
    elif cmd == "saves" and len(rest) in (1, 2):
        cmd_saves(rest[0], rest[1] if len(rest) == 2 else None)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

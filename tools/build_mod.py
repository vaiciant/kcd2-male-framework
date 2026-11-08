"""Packs a KCD2 mod from its source folder.

Expected layout of the source folder:
    <src>/mod.manifest
    <src>/data/...                        -> <out>/<modid>/Data/<modid>.pak
    <src>/localization/<Language>_xml/... -> <out>/<modid>/Localization/<Language>_xml.pak
    <src>/mod.cfg (optional)              -> copied as is

The .pak files are uncompressed ZIPs (ZIP_STORED). The official wiki (KM-A-3, KM-A-58)
asks for compression 0 and warns that ZIPs made with 7-Zip do not work.

Usage:
    python -I tools/build_mod.py <source_folder> <output_folder>
Example:
    python -I tools/build_mod.py mod/medieval_life build
    -> build/medieval_life/ ready to copy into <game>/Mods/
"""
import pathlib
import re
import shutil
import sys
import zipfile


def read_modid(manifest: pathlib.Path) -> str:
    text = manifest.read_text(encoding="utf-8-sig")
    match = re.search(r"<modid>\s*([^<\s]+)\s*</modid>", text)
    if not match:
        raise SystemExit(f"<modid> not found in {manifest}")
    modid = match.group(1)
    # Official rule (KM-A-3): only lowercase letters and underscores.
    if not re.fullmatch(r"[a-z_]+", modid):
        raise SystemExit(f"invalid modid '{modid}': only lowercase letters and underscores (KM-A-3)")
    return modid


def write_pak(src_dir: pathlib.Path, pak_path: pathlib.Path) -> int:
    files = sorted(p for p in src_dir.rglob("*") if p.is_file())
    pak_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(pak_path, "w", compression=zipfile.ZIP_STORED) as pak:
        for path in files:
            # Meshes and face poses are compressed, as in the game's paks.
            compressed = path.suffix == ".skin" or path.name.endswith("_poses.xml")
            compression = zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED
            pak.write(path, path.relative_to(src_dir).as_posix(), compress_type=compression)
    return len(files)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src = pathlib.Path(sys.argv[1]).resolve()
    out_root = pathlib.Path(sys.argv[2]).resolve()
    manifest = src / "mod.manifest"
    if not manifest.is_file():
        raise SystemExit(f"Missing {manifest}")

    modid = read_modid(manifest)
    out = out_root / modid
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    shutil.copy2(manifest, out / "mod.manifest")
    if (src / "mod.cfg").is_file():
        shutil.copy2(src / "mod.cfg", out / "mod.cfg")

    data_dir = src / "data"
    if data_dir.is_dir():
        count = write_pak(data_dir, out / "Data" / f"{modid}.pak")
        print(f"Data/{modid}.pak: {count} files")

    loc_dir = src / "localization"
    if loc_dir.is_dir():
        for lang_dir in sorted(p for p in loc_dir.iterdir() if p.is_dir()):
            count = write_pak(lang_dir, out / "Localization" / f"{lang_dir.name}.pak")
            print(f"Localization/{lang_dir.name}.pak: {count} files")

    print(f"Mod ready in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

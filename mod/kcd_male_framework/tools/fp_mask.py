"""Generates the "first person" version of a KCD2 NPC head. generate_heads.py uses it for the heads of
KCD2 Male Framework, and it also runs on its own. It only reads files of the installed game (never of other
mods) and writes a modified copy of the mesh.

Mechanism:
- The hiding groups are bits in the alpha of the vertex color; group 0
  is FirstPersonView and the game applies it to the player in first person (KM-A-64).
- NPC heads have that bit on (visible). Henry's has it
  off on the whole head except for an area of the neck (488 vertices), and on all
  the other subsets (overlay, eyelashes, eyes, tear duct).
- The heads share the UV map of subset 0, so Henry's mask
  is carried over vertex by vertex by UV coordinate. Everything else is hidden whole.
- Only bit 0 of the alpha changes; the rest of the file stays identical.

Usage:
    python -I mod/kcd_male_framework/tools/fp_mask.py make <game> <head> <out.skin>
        <game>  KCD2 folder (Data/IPL_Heads-part*.pak and Data/Heads.pak are read)
        <head>  name of the head folder, e.g. m_head_011
    python -I mod/kcd_male_framework/tools/fp_mask.py compare <a.skin> <b.skin>
"""
import pathlib
import struct
import sys
import zipfile

HENRY = "m_head_henry"
STREAM_POSITIONS, STREAM_TEXCOORDS, STREAM_COLORS = 0, 2, 3
CHUNK_DATASTREAM, CHUNK_SUBSETS = 0x1016, 0x1017


def find_skin(game: pathlib.Path, head: str) -> bytes:
    wanted = f"objects/characters/humans/male/head/{head}/{head}.skin"
    paks = sorted((game / "Data").glob("IPL_Heads-part*.pak")) + [game / "Data" / "Heads.pak"]
    for pak_path in paks:
        if not pak_path.is_file():
            continue
        with zipfile.ZipFile(pak_path) as pak:
            for name in pak.namelist():
                if name.replace("\\", "/").lower() == wanted:
                    return pak.read(name)
    raise SystemExit(f"{wanted} not found in {game / 'Data'}")


def read_mesh(data: bytes) -> tuple[dict, list]:
    """Returns {stream_type: (data_offset, n_elements, element_size)} and the subsets."""
    signature, version, count, table = struct.unpack_from("<4sIII", data, 0)
    if signature != b"CrCh" or version != 0x746:
        raise SystemExit(f"Unsupported format: {signature!r} {version:#x}")
    streams, subsets = {}, []
    for i in range(count):
        kind, _ver, _id, _size, offset = struct.unpack_from("<HHiII", data, table + 16 * i)
        if kind == CHUNK_DATASTREAM:
            _flags, stream, n, size = struct.unpack_from("<IIII", data, offset)
            if stream in streams:
                raise SystemExit("More than one mesh in the file: not supported")
            streams[stream] = (offset + 24, n, size)
        elif kind == CHUNK_SUBSETS:
            _flags, n = struct.unpack_from("<Ii", data, offset)
            # (first index, n indices, first vertex, n vertices, material)
            subsets = [struct.unpack_from("<iiiii", data, offset + 16 + 36 * k) for k in range(n)]
    for stream in (STREAM_TEXCOORDS, STREAM_COLORS):
        if stream not in streams:
            raise SystemExit(f"Stream {stream} is missing")
    if not subsets:
        raise SystemExit("The subsets are missing")
    return streams, subsets


def head_vertices(subsets: list) -> range:
    first, n = next((s[2], s[3]) for s in subsets if s[4] == 0)
    return range(first, first + n)


def uv_key(data: bytes, streams: dict, i: int) -> tuple:
    offset, _n, size = streams[STREAM_TEXCOORDS]
    u, v = struct.unpack_from("<ff", data, offset + size * i)
    return round(u, 4), round(v, 4)


def make(henry: bytes, target: bytes) -> tuple[bytes, dict]:
    h_streams, h_subsets = read_mesh(henry)
    t_streams, t_subsets = read_mesh(target)
    h_colors = h_streams[STREAM_COLORS][0]

    visible_uv: dict = {}
    for i in head_vertices(h_subsets):
        key = uv_key(henry, h_streams, i)
        visible = bool(henry[h_colors + 4 * i + 3] & 1)
        visible_uv[key] = visible_uv.get(key, False) or visible

    out = bytearray(target)
    t_colors, t_count, _size = t_streams[STREAM_COLORS]
    head = head_vertices(t_subsets)
    stats = {"vertices": t_count, "visible": 0, "no_uv": 0}
    for i in range(t_count):
        alpha = out[t_colors + 4 * i + 3]
        keep = False
        if i in head:
            key = uv_key(target, t_streams, i)
            if key not in visible_uv:
                stats["no_uv"] += 1
            keep = visible_uv.get(key, False)
        if keep:
            alpha |= 1
            stats["visible"] += 1
        else:
            alpha &= 0xFE
        out[t_colors + 4 * i + 3] = alpha
    return bytes(out), stats


def hide(target: bytes) -> bytes:
    """Turns bit 0 off in every vertex: the mesh is not seen in first person. Henry's beards come like this, with
    their LODs, while those of the NPC heads come with it on."""
    streams, _subsets = read_mesh(target)
    out = bytearray(target)
    offset, count, size = streams[STREAM_COLORS]
    for i in range(count):
        out[offset + size * i + 3] &= 0xFE
    return bytes(out)


def compare(a: bytes, b: bytes) -> int:
    if len(a) != len(b):
        print(f"Different size: {len(a)} / {len(b)}")
        return 1
    diffs = sum(1 for x, y in zip(a, b) if x != y)
    print("Identical" if diffs == 0 else f"{diffs} different bytes")
    return 0 if diffs == 0 else 1


def main() -> int:
    if len(sys.argv) == 5 and sys.argv[1] == "make":
        game = pathlib.Path(sys.argv[2])
        head = sys.argv[3]
        result, stats = make(find_skin(game, HENRY), find_skin(game, head))
        pathlib.Path(sys.argv[4]).write_bytes(result)
        print(f"{head}: {stats}")
        if stats["no_uv"]:
            print("WARNING: some head vertices have no matching UV in Henry; check them")
        return 0
    if len(sys.argv) == 4 and sys.argv[1] == "compare":
        return compare(pathlib.Path(sys.argv[2]).read_bytes(), pathlib.Path(sys.argv[3]).read_bytes())
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())

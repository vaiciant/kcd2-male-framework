"""A face pack: the faces of another mod for KCD2 Male Framework (MAKING_FACES.md).

The mod has a faces.toml at its root. This tool writes into that mod what the framework needs to put its faces on Henry,
next to the framework's own looks and without changing the framework's files:

- its tokens, one per face, in data/Libs/Tables/item/item__<pack>.xml;
- its Skald project, data/Quests/<pack>.xml, with one module: each face has a state that its token turns on and the
  framework's reset turns off, that answers the framework's question with its id, and that puts the face's head, body and
  Henry's underwear on Henry while it is on;
- its Lua, data/Scripts/MaleCore/Looks/<pack>.lua, which registers the faces with MaleCore.RegisterLooks, with the beards
  its head has;
- mod.manifest, if the mod has none yet.

A face takes a head of the framework (those of looks.toml, which hide in first-person view and have the barber's beards),
or a head of your own (head_mesh and material), a body of the framework's looks, and a hair and a beard of the game. A
head of your own goes into data/Objects/characters/humans/male/head/<pack>_<face>/ with its LODs, its poses and its
beards, hidden in first-person view as the framework hides the game's heads, and its node into
data/Libs/Tables/Character/CharacterComponent__<pack>.xml.

The ids are those of the save, shared by both frameworks: a pack takes a block of ten between 1000 and 1299, by its name
or the block that faces.toml asks for.

Usage, from the root of the framework's repository, with the game's tables extracted (tools/extract_game.py):
    python -I -X utf8 mod/kcd_male_framework/tools/make_face_pack.py path/to/your_mod
"""
import os
import pathlib
import re
import sys
import tomllib
import uuid
import xml.etree.ElementTree as ET
import zipfile
import zlib

FRAMEWORK = pathlib.Path("mod/kcd_male_framework")
LOOKS_DATA = FRAMEWORK / "data/Scripts/MaleCore/looks_data.lua"
ITEMS = FRAMEWORK / "data/Libs/Tables/item/item__kcd_male_framework.xml"
COMPONENTS = pathlib.Path("game_files/Tables.pak/Libs/Tables/Character/CharacterComponent.xml")
GAME_PLACES = (r"C:\Program Files (x86)\Steam\steamapps\common\KingdomComeDeliverance2", r"E:\SteamLibrary\steamapps\common\KingdomComeDeliverance2")
GAME = pathlib.Path(os.environ.get("KCD2_GAME") or next((p for p in GAME_PLACES if os.path.isfile(os.path.join(p, "Data", "Tables.pak"))), GAME_PLACES[0]))
# Henry's soul and his underwear, as the framework's own project has them (tools/generate_models.py).
HENRY_SOUL = "4c2dcffb-dea1-6263-72d7-b39f4db2d8b5"
HENRY_UNDERWEAR = "m_underwear01_m01"
# A beard without a mesh, which goes on any head.
MESHLESS_BEARD = "m_beard_00"
FIRST_ID, LAST_ID, BLOCK = 1000, 1299, 10
BLOCKS = (LAST_ID - FIRST_ID + 1) // BLOCK
NAME = re.compile(r"[a-z][a-z0-9_]*")


def framework_value(name):
    match = re.search(rf'^MaleCore\.{name} = "([0-9a-f-]+)"', LOOKS_DATA.read_text(encoding="utf-8"), re.M)
    if not match:
        raise SystemExit(f"{LOOKS_DATA} has no {name}: run the tool from the root of the framework's repository")
    return match.group(1)


def framework_looks():
    looks = tomllib.loads((FRAMEWORK / "looks.toml").read_text(encoding="utf-8"))["look"]
    return {look["head"] for look in looks}, {look["body"] for look in looks}


def man_hairs():
    """Every hair of the game for a man: the leaves under Hair in the Male branch."""
    if not COMPONENTS.exists():
        raise SystemExit(f"{COMPONENTS} is not there: extract the game's tables first (tools/extract_game.py)")
    male = next(n for n in ET.parse(COMPONENTS).getroot().iter() if n.get("Name") == "Male")
    return {n.get("Name") for n in male.iter("Hair") if n.get("Name") and not any(c is not n for c in n.iter("Hair"))}


def head_beards(head):
    """The beards that a head has a mesh for in the game, and the meshless one."""
    found = set()
    prefix = f"objects/characters/humans/male/head/{head}/beards/"
    for pak in sorted((GAME / "Data").glob("*Head*.pak")):
        with zipfile.ZipFile(pak) as archive:
            for name in archive.namelist():
                name = name.replace("\\", "/").lower()
                if name.startswith(prefix) and re.fullmatch(r"m_beard_\d+\.skin", name[len(prefix):]):
                    found.add(name[len(prefix):-len(".skin")])
    return sorted(found | {MESHLESS_BEARD})


def token_row(guid, name):
    template = re.search(r'\t\t<MiscItem [^\n]*Name="ml_mf_set_\d+" />', ITEMS.read_text(encoding="utf-8")).group(0)
    return re.sub(r'Id="[^"]+" Name="[^"]+"', f'Id="{guid}" Name="{name}"', template)


def read_faces(mod):
    path = mod / "faces.toml"
    if not path.exists():
        raise SystemExit(f"{path} is not there: MAKING_FACES.md shows how to write it")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    pack = data.get("pack", {})
    if not NAME.fullmatch(pack.get("id", "")):
        raise SystemExit("faces.toml: [pack] id is the id of your mod, in lowercase letters, digits and _")
    faces = data.get("face", [])
    if not 1 <= len(faces) <= BLOCK:
        raise SystemExit(f"faces.toml: a pack has from 1 to {BLOCK} faces")
    return pack, faces


def skald_module(pack_id, faces, reset, ask, answer):
    def trigger(node, descriptor, guid, y):
        return (f'\t\t\t\t<Function Name="{descriptor}" PositionY="{y}" PositionX="-900" MethodName="wh::entitymodule::CreateItemClassDescriptor" DeclaringType="wh::entitymodule">\n'
                f'\t\t\t\t\t<Constant Name="ItemClass" Value="{guid}" />\n\t\t\t\t\t<Constant Name="Amount" Value="1" />\n\t\t\t\t</Function>\n'
                f'\t\t\t\t<ItemDescriptorTrigger Name="{node}" PositionY="{y}" PositionX="-600">\n'
                '\t\t\t\t\t<Edge From="henry.Inventory" To="Inventory" />\n'
                f'\t\t\t\t\t<Edge From="{descriptor}.ItemDescriptor" To="ItemDescriptor" />\n'
                '\t\t\t\t\t<Edge From="always_on.State" To="IsActive" />\n\t\t\t\t</ItemDescriptorTrigger>\n')
    nodes = ('\t\t\t\t<ObjectProperties Name="henry" PositionY="0" PositionX="-1200" DeclaringType="wh::rpgmodule::I_Soul">\n'
             '\t\t\t\t\t<Asset Name="I_Soul" Alias="henry" />\n\t\t\t\t</ObjectProperties>\n'
             '\t\t\t\t<State Name="always_on" PositionY="-150" PositionX="-1200" TypeT="bool">\n'
             '\t\t\t\t\t<Constant Name="DefaultValue" Value="true" />\n\t\t\t\t</State>\n'
             + trigger("reset_token", "reset_descriptor", reset, -300) + trigger("ask_token", "ask_descriptor", ask, -450))
    for n, face in enumerate(faces):
        i, y = face["id"], 200 * n
        nodes += (trigger(f"set_token_{i}", f"set_descriptor_{i}", face["token"], y)
                  + f'\t\t\t\t<State Name="chosen_{i}" PositionY="{y}" PositionX="-300" TypeT="bool">\n'
                  '\t\t\t\t\t<Constant Name="DefaultValue" Value="false" />\n'
                  f'\t\t\t\t\t<Edge From="set_token_{i}.OnAcquire" To="SetTrue" />\n'
                  '\t\t\t\t\t<Edge From="reset_token.OnAcquire" To="SetFalse" />\n\t\t\t\t</State>\n'
                  f'\t\t\t\t<If Name="answer_if_{i}" PositionY="{y}" PositionX="300">\n'
                  f'\t\t\t\t\t<Edge From="chosen_{i}.State" To="Condition" />\n'
                  '\t\t\t\t\t<Edge From="ask_token.OnAcquire" To="Exec" />\n\t\t\t\t</If>\n'
                  f'\t\t\t\t<EventFunction Name="answer_{i}" PositionY="{y}" PositionX="600" MethodName="wh::entitymodule::CreatePlayerReward" DeclaringType="wh::entitymodule">\n'
                  f'\t\t\t\t\t<Constant Name="ItemClass" Value="{answer}" />\n\t\t\t\t\t<Constant Name="Amount" Value="{i}" />\n'
                  '\t\t\t\t\t<Constant Name="ShowUINotification" Value="false" />\n'
                  f'\t\t\t\t\t<Edge From="answer_if_{i}.True" To="Exec" />\n\t\t\t\t</EventFunction>\n'
                  + "".join(
                      f'\t\t\t\t<BodyPartOverride Name="{part}_{i}" PositionY="{y + 70 * k}" PositionX="0">\n'
                      '\t\t\t\t\t<Asset Name="Soul" Alias="henry" />\n'
                      f'\t\t\t\t\t<Constant Name="BodyPart" Value="{part.capitalize()}" />\n'
                      f'\t\t\t\t\t<Constant Name="Component" Value="{piece}" />\n'
                      f'\t\t\t\t\t<Edge From="chosen_{i}.State" To="IsActive" />\n\t\t\t\t</BodyPartOverride>\n'
                      for k, (part, piece) in enumerate((("head", face["head"]), ("body", face["body"]), ("underwear", HENRY_UNDERWEAR)))))
    module = f"{pack_id}_faces"
    return module, ('<?xml version="1.0" encoding="utf-8"?>\n'
                    '<Database xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" Name="brambora">\n'
                    '\t<!-- Written by make_face_pack.py of KCD2 Male Framework from faces.toml. Each face: its token turns it on, and the\n'
                    '\t     framework\'s reset turns it off; it answers the framework\'s question with its id, and puts its head and body,\n'
                    '\t     and Henry\'s underwear, on Henry while it is on. -->\n'
                    f'\t<Skald>\n\t\t<Module Name="{module}">\n\t\t\t<Nodes>\n' + nodes
                    + '\t\t\t</Nodes>\n\t\t\t<Assets>\n'
                    f'\t\t\t\t<SoulAsset Name="henry" SharedSoulGuids="{HENRY_SOUL}" />\n'
                    f'\t\t\t</Assets>\n\t\t\t<Text Text="{module}" />\n\t\t</Module>\n\t</Skald>\n</Database>\n')


def skald_project(pack_id, module):
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<Database xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" Name="brambora">\n'
            '\t<!-- Written by make_face_pack.py of KCD2 Male Framework: the faces of this mod (MAKING_FACES.md). -->\n'
            f'\t<Skald>\n\t\t<Project Name="{pack_id}">\n\t\t\t<Definitions>\n'
            f'\t\t\t\t<Definition File="{pack_id}/{module}.xml" />\n\t\t\t</Definitions>\n'
            f'\t\t\t<Nodes>\n\t\t\t\t<{module} Name="{module}" PositionY="0" PositionX="0" />\n\t\t\t</Nodes>\n'
            f'\t\t\t<Text Text="{pack_id}" />\n\t\t\t<ObjectiveValueTypes>\n'
            '\t\t\t\t<ObjectiveValueType Type="None" IsPast="false" Icon="Exclamation" />\n'
            '\t\t\t\t<ObjectiveValueType Type="Started" IsPast="false" Icon="Exclamation" Hint="objective_HintStarted" />\n'
            '\t\t\t\t<ObjectiveValueType Type="Updated" IsPast="false" Icon="Exclamation" Hint="objective_HintUpdated" />\n'
            '\t\t\t\t<ObjectiveValueType Type="Completed" IsPast="true" Icon="Check" Hint="objective_HintCompleted" />\n'
            '\t\t\t\t<ObjectiveValueType Type="Canceled" IsPast="true" Icon="Cross" Hint="objective_HintCanceled" />\n'
            '\t\t\t</ObjectiveValueTypes>\n\t\t</Project>\n\t</Skald>\n</Database>\n')


def lua_file(pack_id, faces):
    lines = [f"-- Written by make_face_pack.py of KCD2 Male Framework from faces.toml: the faces of {pack_id}.",
             "-- The framework reads every file of Scripts/MaleCore/Looks and keeps these with its own looks.",
             "if not (MaleCore and MaleCore.RegisterLooks) then",
             f'\tSystem.LogAlways("[{pack_id}] this version of KCD2 Male Framework has no RegisterLooks: these faces need a newer one")',
             "\treturn", "end", f'MaleCore.RegisterLooks("{pack_id}", {{']
    for face in faces:
        beards = ", ".join(f'"{b}"' for b in face["beards"])
        lines.append(f'\t{{ id = {face["id"]}, name = "{face["name"]}", hair = "{face["hair"]}", beard = "{face["beard"]}", '
                     f'age = "{face.get("age", "young")}", token = "{face["token"]}", beards = {{ {beards} }} }},')
    lines += ["})", ""]
    return "\n".join(lines)


# The beards every head needs: those of the barber of a man with a look, and the two the framework puts on to rebuild the
# face (male_core.lua, REBUILD_BEARD and REFRESH_BEARD). A beard without its mesh on the head has closed the game.
def required_beards():
    barber = tomllib.loads((FRAMEWORK / "barber.toml").read_text(encoding="utf-8")).get("beard", [])
    return sorted({b["mesh"] for b in barber} | {"m_beard_17", "m_beard_18"} - {MESHLESS_BEARD})


def copy_material(source, target):
    """The material of a head of your own, next to its head: the textures it names next to it (File="./...") go there too,
    with their mipmaps (.dds.1...), and those it names by their full path stay where they are."""
    text = source.read_text(encoding="utf-8")
    for texture in sorted(set(re.findall(r'File="\./([^"/]+)\.[a-z]+"', text))):
        files = [p for p in source.parent.iterdir() if p.is_file() and p.name.lower().startswith(texture.lower() + ".")]
        if not files:
            print(f"WARNING: {source} names ./{texture}, which is not next to it: give it its full path in your mod")
        for path in files:
            if path.parent.resolve() != target.parent.resolve():
                (target.parent / path.name).write_bytes(path.read_bytes())
    target.write_text(text, encoding="utf-8", newline="")


def load_fp_mask():
    import importlib.util
    spec = importlib.util.spec_from_file_location("fp_mask", pathlib.Path(__file__).resolve().with_name("fp_mask.py"))
    fp_mask = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fp_mask)
    path = f"objects/characters/humans/male/head/{fp_mask.HENRY}/{fp_mask.HENRY}.skin"
    for pak in sorted((GAME / "Data").glob("*Head*.pak")):
        with zipfile.ZipFile(pak) as archive:
            for name in archive.namelist():
                if name.replace("\\", "/").lower() == path:
                    return fp_mask, archive.read(name)
    raise SystemExit(f"Henry's head is not in the game's paks: {path}")


def head_folder(mod, face):
    return mod / f"data/Objects/characters/humans/male/head/{face['head']}"


def own_head(mod, face, fp_mask, henry):
    """A head of your own, made on the game's male skeleton with the UVs of the game's men's heads, as the game's are: with
    its LODs (<head>_lod1.skin...), its face poses (<head>_poses.xml) and its beards (beards/m_beard_04.skin, with their
    LODs) next to it. Its copy and its beards are hidden in first-person view, as the framework hides the game's
    (fp_mask.py), and its material goes next to it."""
    source = mod / face["head_mesh"]
    stem, head = source.name[:-len(".skin")], face["head"]
    out = head_folder(mod, face)
    (out / "beards").mkdir(parents=True, exist_ok=True)
    for path in sorted(source.parent.glob(stem + "*.skin")):
        lod = path.name[len(stem):-len(".skin")]
        if lod and not re.fullmatch(r"_lod\d", lod):
            continue
        mesh = path.read_bytes()
        if not lod:
            mesh, stats = fp_mask.make(henry, mesh)
            print(f"{head}: {stats}")
            if stats.get("no_uv"):
                print("WARNING: some vertices of the head have no UV of Henry's head: they may show in first-person view")
        (out / f"{head}{lod}.skin").write_bytes(mesh)
        print(f"Written: {out / (head + lod + '.skin')}")
    poses = source.with_name(stem + "_poses.xml")
    if poses.is_file():
        (out / f"{head}_poses.xml").write_bytes(poses.read_bytes())
    else:
        print(f"WARNING: {poses} is not there: his face keeps still, with no expressions")
    for path in sorted(source.parent.glob("beards/m_beard_*.skin")):
        if re.fullmatch(r"m_beard_\d+(_lod\d)?\.skin", path.name):
            mesh = path.read_bytes()
            (out / "beards" / path.name).write_bytes(mesh if "_lod" in path.name else fp_mask.hide(mesh))
    copy_material(mod / face["material"], out / f"{head}.mtl")
    print(f"Written: {out}, with {len(list((out / 'beards').glob('*.skin')))} beard meshes")


def head_table(pack_id, faces):
    """The node of each head of your own, under the man's Head, with the man's branch and its Head as the game has them."""
    tree = ET.parse(COMPONENTS).getroot()
    male = next(n for n in tree.iter() if n.get("Name") == "Male" and n.tag == "Component")
    head = next(n for n in male.find("DerivedComponents") if n.get("Name") == "Head")
    attributes = lambda node: " ".join(f'{k}="{v}"' for k, v in node.attrib.items())
    elements = "".join(f"\t\t\t\t\t\t\t{ET.tostring(e, encoding='unicode').strip()}\n" for e in head.find("Elements"))
    nodes = "".join(
        f'\t\t\t\t\t\t\t\t<Head Name="{face["head"]}" FilePath="humans/male/head/{face["head"]}" '
        f'Paleness="{face.get("paleness", "Pale Ordinary Suntanned")}" Age="{"Old" if face.get("age") == "old" else "YoungAdult"}">\n'
        '\t\t\t\t\t\t\t\t\t<Elements>\n'
        f'\t\t\t\t\t\t\t\t\t\t<SkinElement EquipmentPart="face" Model="{face["head"]}.skin" Material="{face["head"]}.mtl" />\n'
        '\t\t\t\t\t\t\t\t\t</Elements>\n\t\t\t\t\t\t\t\t</Head>\n'
        for face in faces)
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<database xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" name="barbora" xsi:noNamespaceSchemaLocation="../database.xsd">\n'
            '\t<!-- Written by make_face_pack.py of KCD2 Male Framework: the heads of this mod. -->\n'
            '\t<CharacterComponents version="6">\n'
            f'\t\t<Component {attributes(male)}>\n\t\t\t<DerivedComponents>\n'
            f'\t\t\t\t<Head {attributes(head)}>\n\t\t\t\t\t<Elements>\n{elements}\t\t\t\t\t</Elements>\n'
            '\t\t\t\t\t<DerivedComponents>\n' + nodes + '\t\t\t\t\t</DerivedComponents>\n\t\t\t\t</Head>\n'
            '\t\t\t</DerivedComponents>\n\t\t</Component>\n\t</CharacterComponents>\n</database>\n')


def manifest(pack):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<kcd_mod>\n\t<info>\n'
            f'\t\t<name>{pack.get("name", pack["id"])}</name>\n\t\t<modid>{pack["id"]}</modid>\n'
            f'\t\t<description>{pack.get("description", "Faces for KCD2 Male Framework")}</description>\n'
            f'\t\t<author>{pack.get("author", "")}</author>\n\t\t<version>{pack.get("version", "0.1.0")}</version>\n'
            '\t\t<modifies_level>false</modifies_level>\n\t</info>\n'
            '\t<supports>\n\t\t<version>1.5*</version>\n\t</supports>\n</kcd_mod>\n')


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    mod = pathlib.Path(sys.argv[1])
    pack, faces = read_faces(mod)
    pack_id = pack["id"]
    heads, bodies = framework_looks()
    hairs = man_hairs()
    block = pack.get("block", zlib.crc32(pack_id.encode()) % BLOCKS)
    if not isinstance(block, int) or not 0 <= block < BLOCKS:
        raise SystemExit(f"faces.toml: block is a number from 0 to {BLOCKS - 1}")
    for n, face in enumerate(faces):
        name = face.get("name", "")
        problems = []
        if not NAME.fullmatch(name):
            problems.append("its name is in lowercase letters, digits and _")
        if face.get("head_mesh"):
            # A head of your own, with its beards next to it (own_head).
            mesh, material = mod / face["head_mesh"], mod / face.get("material", "")
            face["head"] = f"{pack_id}_{name}"
            face["beards"] = sorted({p.name[:-len(".skin")] for p in mesh.parent.glob("beards/m_beard_*.skin")
                                     if re.fullmatch(r"m_beard_\d+\.skin", p.name)} | {MESHLESS_BEARD})
            if not mesh.is_file():
                problems.append(f"head_mesh {face['head_mesh']} is not in your mod")
            elif mesh.parent.resolve() == head_folder(mod, face).resolve():
                problems.append(f"keep the files of your head out of {head_folder(mod, face)}: the tool writes its head there")
            if not face.get("material") or not material.is_file():
                problems.append("a head of your own needs its material: material = path of its .mtl in your mod")
            missing = sorted(set(required_beards()) - set(face["beards"]))
            if missing:
                problems.append(f"its head needs these beards in beards/ next to it, or the game closes: {', '.join(missing)}")
        elif face.get("head") not in heads:
            problems.append(f"head {face.get('head')} is not a head of the framework (LOOKS.md)")
        else:
            face["beards"] = head_beards(face["head"])
        if face.get("body") not in bodies:
            problems.append(f"body {face.get('body')} is not a body of the framework's looks ({', '.join(sorted(bodies))})")
        if face.get("hair") not in hairs:
            problems.append(f"hair {face.get('hair')} is not a man's hair of the game")
        face.setdefault("beards", [])
        if face.get("beard") not in face["beards"]:
            problems.append(f"beard {face.get('beard')} has no mesh on that head: one of {', '.join(face['beards'])}")
        if problems:
            raise SystemExit(f"faces.toml, face {name or '?'}: " + "; ".join(problems))
        face["id"] = FIRST_ID + BLOCK * block + n
        face["token"] = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{pack_id}/ml_mf_face/{name}"))
    reset, ask, answer = framework_value("RESET_TOKEN"), framework_value("ASK_TOKEN"), framework_value("ANSWER_ITEM")
    module, module_text = skald_module(pack_id, faces, reset, ask, answer)
    data = mod / "data"
    files = {
        data / f"Libs/Tables/item/item__{pack_id}.xml":
            '<?xml version="1.0" encoding="us-ascii"?>\n'
            '<database xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" name="barbora" xsi:noNamespaceSchemaLocation="item.xsd">\n'
            '\t<ItemClasses version="8">\n'
            '\t\t<!-- Written by make_face_pack.py of KCD2 Male Framework: the token of each face. -->\n'
            + "".join(token_row(face["token"], f"{pack_id}_face_{face['id']}") + "\n" for face in faces)
            + "\t</ItemClasses>\n</database>\n",
        data / f"Quests/{pack_id}.xml": skald_project(pack_id, module),
        data / f"Quests/{pack_id}/{module}.xml": module_text,
        data / f"Scripts/MaleCore/Looks/{pack_id}.lua": lua_file(pack_id, faces),
    }
    if not (mod / "mod.manifest").exists():
        files[mod / "mod.manifest"] = manifest(pack)
    own = [face for face in faces if face.get("head_mesh")]
    if own:
        files[data / f"Libs/Tables/Character/CharacterComponent__{pack_id}.xml"] = head_table(pack_id, own)
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"Written: {path}")
    if own:
        fp_mask, henry = load_fp_mask()
        for face in own:
            own_head(mod, face, fp_mask, henry)
    first = FIRST_ID + BLOCK * block
    print(f"{pack_id}: {len(faces)} faces, block {block}, ids {first} to {first + len(faces) - 1}")


if __name__ == "__main__":
    main()

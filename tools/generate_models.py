"""Catalog of looks: adds the game's faces that fit and generates everything for each look.

Reads mod/kcd_female_framework/looks.toml and mod/kcd_male_framework/looks.toml, or the one that is there. Adds to them, with the next ids, the
game's faces that fit and are missing: the generic ones of men and of women, of every age, and those of named characters
that have their files and, for men, the five beards of the barber, so that the barber fits all of them. It never changes
an entry that is already there: entries can be edited by hand. Then it writes:

- In each framework: the souls and the STORM rules of the preview models, and the look tokens.
- In each framework, its graph, its tokens and its Lua: the look on Henry and on the character of KCD2 Life. KCD2 Life
  no longer has anything generated: it only calls the frameworks.
- In each framework, LOOKS.md, and the characters of each look in its Lua: who wears each face in the game, from the
  STORM rules and the English names of the game.

The meshes come afterwards: generate_women.py (KCDFF) and generate_heads.py (KCDMF) read this data.

Usage, from the root of the repository: python -I -X utf8 tools/generate_models.py
"""
import collections
import hashlib
import html
import os
import pathlib
import re
import tomllib
import uuid
import xml.etree.ElementTree as ET
import zipfile

# KCD2_GAME, or the game in the default Steam library, or in the maintainer's.
GAME_PLACES = (r"C:\Program Files (x86)\Steam\steamapps\common\KingdomComeDeliverance2", r"E:\SteamLibrary\steamapps\common\KingdomComeDeliverance2")
GAME = pathlib.Path(os.environ.get("KCD2_GAME") or next((p for p in GAME_PLACES if os.path.isfile(os.path.join(p, "Data", "Tables.pak"))), GAME_PLACES[0]))
EXTRACTED = pathlib.Path("game_files")
CHARACTER_COMPONENTS = EXTRACTED / "Tables.pak/Libs/Tables/Character/CharacterComponent.xml"
SOUL_TABLES = EXTRACTED / "Tables.pak/Libs/Tables/rpg"
APPEARANCE = EXTRACTED / "IPL_GameData_storm/Libs/Storm/appearance"
GUID_NAMESPACE = "medieval_life"
BARBER_BEARDS = ["m_beard_04", "m_beard_13", "m_beard_16", "m_beard_17", "m_beard_18"]
HAIR_COLORS = ["dark_brown", "black", "light_brown", "blonde", "ginger", "dark_ginger", "dark_grey", "grey", "white"]
# The women's hairstyles that generate_women.py copies, each with its number of colors. Style 3 has no grey.
HAIR_STYLES = {1: 9, 2: 9, 3: 6, 4: 9, 5: 9, 6: 9, 7: 9}
# Henry is the player: his face is not a look.
EXCLUDED_HEADS = {"m_head_henry"}
VILLAGE_TABLE = re.compile(r"soul__[tk][a-z]{3}\.xml$")
NOBLE, IMMORTAL, CUMAN = {14}, {4, 12, 13, 15}, {43}

GENDERS = {
    "man": {"folder": pathlib.Path("mod/kcd_male_framework"), "prefix": "ml_mf_"},
    "woman": {"folder": pathlib.Path("mod/kcd_female_framework"), "prefix": "ml_ff_"},
}
# Each framework has its own public repository, and builds there alone: the one whose folder is missing is left out.
PRESENT = [g for g, d in GENDERS.items() if (d["folder"] / "mod.manifest").is_file()]


# --- Reading the game ---------------------------------------------------------------------------------------------------

def head_files():
    files = collections.defaultdict(set)
    for pak in sorted((GAME / "Data").glob("*Head*.pak")):
        with zipfile.ZipFile(pak) as z:
            for name in z.namelist():
                m = re.match(r"objects/characters/humans/(?:male|female)/head/([^/]+)/(.*)", name.replace("\\", "/").lower())
                if m:
                    files[m.group(1)].add(m.group(2))
    return files


def usable_heads():
    files = head_files()
    result = {}
    for node in ET.parse(CHARACTER_COMPONENTS).getroot().iter("Head"):
        name = node.get("Name") or ""
        m = re.fullmatch(r"([mf])_head_([a-z0-9]+)", name)
        if not m or name in EXCLUDED_HEADS or f"{name}.skin" not in files.get(name, ()):
            continue
        gender = "man" if m.group(1) == "m" else "woman"
        if gender == "man" and not all(f"beards/{b}.skin" in files[name] for b in BARBER_BEARDS):
            continue
        result[name] = {
            "gender": gender,
            "age": "old" if re.search(r"Old|Ancient", node.get("Age") or "") else "young",
            "paleness": (node.get("Paleness") or "").split(),
            "generic": bool(re.fullmatch(r"[mf]_head_\d+", name)),
            "beards": {f[len("beards/"):-len(".skin")] for f in files[name] if re.fullmatch(r"beards/m_beard_\d+\.skin", f)},
        }
    return result


def man_hairs():
    """Every hair of the game for a man: the leaves under Hair in the Male branch, each colour its own."""
    male = next(n for n in ET.parse(CHARACTER_COMPONENTS).getroot().iter() if n.get("Name") == "Male")
    return sorted(n.get("Name") for n in male.iter("Hair") if n.get("Name") and not any(c is not n for c in n.iter("Hair")))


def head_beards(files, head):
    """The beards that a head has a mesh for, and the meshless one, which goes on any head. A beard without its
    mesh on the head has crashed the game."""
    found = {f[len("beards/"):-len(".skin")] for f in files.get(head, ()) if re.fullmatch(r"beards/m_beard_\d+\.skin", f)}
    return sorted(found | {MESHLESS_BEARD})


def head_uses():
    """Per head, the souls that wear it in the game's STORM rules, with their hair, beard and body. The rules write the
    attribute both as name and as Name: Olda of Semine's is <hasName Name="tsem_seminjr" />."""
    souls = {}
    for table in SOUL_TABLES.glob("soul*.xml"):
        for row in re.findall(r"<soul [^>]*>", table.read_text(encoding="utf-8", errors="replace")):
            a = dict(re.findall(r'(\w+)="([^"]*)"', row))
            if "soul_name" in a:
                souls[a["soul_name"].lower()] = {
                    "village": bool(VILLAGE_TABLE.search(table.name)), "class": int(a.get("social_class_id") or 0),
                    "vip": int(a.get("soul_vip_class_id") or 0), "faction": a.get("factionName", ""),
                    "soul_name": a["soul_name"], "character": a.get("skald_character_name", "")}
    uses = collections.defaultdict(list)
    for xml in sorted(APPEARANCE.rglob("*.xml")):
        quest = xml.relative_to(APPEARANCE).parts[0] == "quests"
        for rule in re.findall(r"<rule .*?</rule>", xml.read_text(encoding="utf-8", errors="replace"), re.S | re.I):
            head = re.search(r'<setHead name="([^"]+)"', rule, re.I)
            if not head:
                continue
            # m_head_036_b00 is the same head with another material.
            base = re.sub(r"_b\d+$", "", head.group(1))
            parts = {k: (re.search(rf'<set{k} name="([^"]+)"', rule, re.I) or [None, None])[1] for k in ("Hair", "Beard", "Body")}
            for soul in re.findall(r'<hasName name="([^"]+)"', rule, re.I):
                if soul.lower() in souls:
                    uses[base].append({**souls[soul.lower()], **parts, "quest": quest})
    return uses


def character_names():
    """The English name of each character of the game with a name of its own, by its Skald character: char_SEMIN_JUNIOR is
    Olda of Semine, from char_SEMIN_JUNIOR_uiName. The generic souls have none."""
    with zipfile.ZipFile(GAME / "Localization" / "English_xml.pak") as pak:
        text = pak.read("text_ui_soul.xml").decode("utf-8", errors="replace")
    rows = re.findall(r"<Row><Cell>([^<]*)_uiName</Cell><Cell>[^<]*</Cell><Cell>([^<]*)</Cell>", text)
    return {key: html.unescape(name).strip() for key, name in rows if name.strip()}


def look_characters(uses, names):
    """Per head, the characters with a name of their own that wear it, in alphabetical order, each once, with the hair and
    the beard of its rule: the one out of a quest if there is one."""
    found = collections.defaultdict(dict)
    for head, wearers in uses.items():
        for use in sorted(wearers, key=lambda u: u["quest"]):
            name = names.get(use["character"])
            if name and name not in found[head]:
                found[head][name] = {"name": name, "hair": use["Hair"], "beard": use["Beard"]}
    return {head: sorted(by_name.values(), key=lambda c: c["name"].casefold()) for head, by_name in found.items()}


def villager_use(uses):
    """The first one that wears it and is from a village, neither noble nor immortal nor from a quest: its hair is not
    that of someone known."""
    return next((u for u in uses if u["village"] and not u["quest"] and u["class"] not in NOBLE and u["vip"] not in IMMORTAL), None)


# --- Catalog -------------------------------------------------------------------------------------------------------------

def ethnicity_of(info, uses):
    if not info["generic"]:
        return ""
    # Romani if its paleness is only Roma, or if the game gives it to the people of the nomad camp.
    if ("Roma" in info["paleness"] and "Pale" not in info["paleness"]) or any(re.search(r"romani", u["faction"], re.I) for u in uses):
        return "romani"
    if any(u["class"] in CUMAN or re.search(r"kuman|cuman", u["faction"], re.I) for u in uses):
        return "hungarian"
    return "czech"


def man_defaults(head, info, example, ethnicity):
    hair = (example or {}).get("Hair") or ""
    if not hair.startswith("m_hair_"):
        hair = "m_hair_013_black" if ethnicity in ("romani", "hungarian") else "m_hair_009_dark_brown"
    beard = (example or {}).get("Beard") or "m_beard_00"
    if beard != "m_beard_00" and beard not in info["beards"]:
        beard = "m_beard_00"
    body = (example or {}).get("Body") or ""
    if not body.startswith("m_body_"):
        old = info["age"] == "old"
        body = {"romani": "m_body_tan_old_05" if old else "m_body_roma_02",
                "hungarian": "m_body_tan_old_01" if old else "m_body_tan_05"}.get(ethnicity, "m_body_pale_old_01" if old else "m_body_pale_02")
    return hair, beard, body


def woman_defaults(head, info, example, ethnicity):
    hair = (example or {}).get("Hair") or ""
    m = re.fullmatch(r"f_hair_(\d{3})_(\w+)", hair)
    if not m or int(m.group(1)) not in HAIR_STYLES or m.group(2) not in HAIR_COLORS[:HAIR_STYLES[int(m.group(1))]]:
        color = "grey" if info["age"] == "old" else ("black" if ethnicity in ("romani", "hungarian") else "dark_brown")
        hair = f"f_hair_002_{color}"
    old = info["age"] == "old"
    if ethnicity == "romani":
        body = "f_body_old_roma" if old else "f_body_tan_03"
    elif ethnicity == "hungarian":
        body = "f_body_old_tan_01" if old else "f_body_tan_03"
    else:
        body = "f_body_old_pale_01" if old else ("f_body_pale_02" if int(re.sub(r"\D", "", head) or 0) % 2 == 0 else "f_body_pale_04")
    return hair, None, body


def guid(text):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{GUID_NAMESPACE}/{text}"))


def lua_list(texts):
    """A Lua list of strings."""
    return "{ " + ", ".join('"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"' for s in texts) + " }"


def toml_entry(look):
    lines = [f"id = {look['id']}", f'name = "{look["name"]}"', f'head = "{look["head"]}"', f'ethnicity = "{look["ethnicity"]}"',
             f'age = "{look["age"]}"', f'villager = {"true" if look["villager"] else "false"}', f'body = "{look["body"]}"',
             f'hair = "{look["hair"]}"']
    if look.get("beard"):
        lines.append(f'beard = "{look["beard"]}"')
    lines += [f'soul = "{look["soul"]}"', f'token = "{look["token"]}"']
    return "\n[[look]]\n" + "\n".join(lines) + "\n"


def extend_catalog():
    catalogs = {g: tomllib.loads((GENDERS[g]["folder"] / "looks.toml").read_text(encoding="utf-8"))["look"] for g in PRESENT}
    # The ids are shared by both frameworks: KCD2 Life tells a face by its id. With one framework alone, a new id may be one
    # the other uses, so the repository with both stops here when two looks share one.
    ids = collections.Counter(l["id"] for c in catalogs.values() for l in c)
    shared = sorted(i for i, n in ids.items() if n > 1)
    if shared:
        raise SystemExit(f"looks.toml: more than one look with the id {shared}. Give each look its own id.")
    next_id = max(ids) + 1
    heads, uses = usable_heads(), head_uses()
    new_looks = collections.defaultdict(list)
    for head, info in sorted(heads.items(), key=lambda c: (not c[1]["generic"], c[0])):
        gender = info["gender"]
        if gender not in PRESENT or any(l["head"] == head for l in catalogs[gender] + new_looks[gender]):
            continue
        ethnicity = ethnicity_of(info, uses.get(head, []))
        hair, beard, body = (man_defaults if gender == "man" else woman_defaults)(head, info, villager_use(uses.get(head, [])), ethnicity)
        prefix = GENDERS[gender]["prefix"]
        if ethnicity:
            made = sum(1 for l in catalogs[gender] + new_looks[gender] if l["ethnicity"] == ethnicity)
            name = f"{gender}_{ethnicity}_{made + 1}"
        else:
            name = head if gender == "man" else prefix + head[len("f_"):]
        new_looks[gender].append({"id": next_id, "name": name, "head": head, "ethnicity": ethnicity, "age": info["age"],
                                  "villager": info["generic"], "body": body, "hair": hair, "beard": beard,
                                  "soul": guid(f"{prefix}model_{head}"), "token": guid(f"{prefix}look_{head}")})
        next_id += 1
    for gender in PRESENT:
        d = GENDERS[gender]
        if new_looks[gender]:
            path = d["folder"] / "looks.toml"
            path.write_text(path.read_text(encoding="utf-8") + "".join(toml_entry(l) for l in new_looks[gender]),
                            encoding="utf-8", newline="\n")
        catalogs[gender] += new_looks[gender]
        print(f"{gender}: {len(catalogs[gender])} looks, {len(new_looks[gender])} new")
    return catalogs


# --- Writing -------------------------------------------------------------------------------------------------------------

def read_file(path):
    return pathlib.Path(path).read_text(encoding="utf-8")


def write_file(path, text):
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_text(text, encoding="utf-8", newline="\n")


def replace_lines(text, pattern, new_lines):
    """Removes the lines that match the pattern and puts the new ones where the first one was."""
    lines = text.split("\n")
    positions = [i for i, l in enumerate(lines) if re.fullmatch(pattern, l)]
    if not positions:
        raise SystemExit(f"No lines match {pattern}")
    indent = re.match(r"\t*", lines[positions[0]]).group(0)
    rest = [l for i, l in enumerate(lines) if i not in set(positions)]
    return "\n".join(rest[:positions[0]] + [indent + n for n in new_lines] + rest[positions[0]:])


def component(look, gender):
    """A woman's look uses the copies of KCDFF: ml_ff_ instead of the game's f_."""
    return lambda part: ("ml_ff_" + look[part][len("f_"):]) if gender == "woman" else look[part]


def write_frameworks(catalogs):
    for gender in PRESENT:
        d = GENDERS[gender]
        folder, prefix, looks = d["folder"], d["prefix"], catalogs[gender]
        # Tokens.
        path = folder / f"data/Libs/Tables/item/item__{folder.name}.xml"
        text = read_file(path)
        template = re.search(rf'\t\t<MiscItem [^\n]*Name="{prefix}look_\d+" />', text).group(0)
        rows = [re.sub(r'Id="[^"]+" Name="[^"]+"', f'Id="{l["token"]}" Name="{prefix}look_{l["id"]}"', template).strip() for l in looks]
        write_file(path, replace_lines(text, rf'\t\t<MiscItem [^\n]*Name="{prefix}look_\d+" />', rows))
        # Souls of the models.
        path = folder / f"data/Libs/Tables/rpg/soul__{folder.name}.xml"
        text = read_file(path)
        template = re.search(r'\t\t<soul [^\n]*/>', text).group(0)
        rows = [re.sub(r'soul_id="[^"]+"', f'soul_id="{l["soul"]}"', re.sub(r'soul_name="[^"]+"', f'soul_name="{prefix}model_{l["id"]}"', template)).strip()
                for l in looks]
        write_file(path, replace_lines(text, r'\t\t<soul [^\n]*/>', rows))
        # STORM rules: the model wears the parts of the game that the look copies.
        path = folder / f"data/Libs/Storm/appearance/{folder.name}.xml"
        text = read_file(path)
        rules = "".join(
            f'\t\t<rule name="{prefix}model_{l["id"]}_look">\n\t\t\t<selectors>\n\t\t\t\t<hasName name="{prefix}model_{l["id"]}" />\n'
            f'\t\t\t</selectors>\n\t\t\t<operations>\n\t\t\t\t<setHead name="{l["head"]}" />\n\t\t\t\t<setHair name="{l["hair"]}" />\n'
            f'\t\t\t\t<setBody name="{l["body"]}" />\n' + (f'\t\t\t\t<setBeard name="{l["beard"]}" />\n' if l.get("beard") else "")
            + "\t\t\t</operations>\n\t\t</rule>\n" for l in looks)
        text = re.sub(r"\t<rules>\n.*\t</rules>\n", lambda m: "\t<rules>\n" + rules + "\t</rules>\n", text, flags=re.S)
        write_file(path, text)


HENRY_SOUL = "4c2dcffb-dea1-6263-72d7-b39f4db2d8b5"
# What KCDFF adds to the answer: Henry's head and body kept on after ml_ff_henry, and that he was a woman in this save.
HENRY_KEPT_ANSWER, WAS_WOMAN_ANSWER = 500, 1000
# And that her state woman is still on: with a man, KCDFF turns it off on the load.
WOMAN_ON_ANSWER = 2000
# Henry's underwear, in the game's STORM rule appearance_player_henry. Each look of a man and Henry's own face put it on
# with an override, as her look puts on her shift: turned off, an override of hers left her shift in the soul.
HENRY_UNDERWEAR = "m_underwear01_m01"


def answer_nodes(looks, ask, answer):
    """The look worn lives in the states of Skald, which the save keeps, and not in an item that shows in the
    inventory. Lua asks with a token, and Skald answers with as many units of another one as the id of the look that
    is on. With no look, it answers nothing."""
    nodes = ('\t\t\t\t<Function Name="ask_descriptor" PositionY="-750" PositionX="-900" MethodName="wh::entitymodule::CreateItemClassDescriptor" DeclaringType="wh::entitymodule">\n'
             f'\t\t\t\t\t<Constant Name="ItemClass" Value="{ask}" />\n\t\t\t\t\t<Constant Name="Amount" Value="1" />\n\t\t\t\t</Function>\n'
             '\t\t\t\t<ItemDescriptorTrigger Name="ask_token" PositionY="-750" PositionX="-600">\n'
             '\t\t\t\t\t<Edge From="henry.Inventory" To="Inventory" />\n'
             '\t\t\t\t\t<Edge From="ask_descriptor.ItemDescriptor" To="ItemDescriptor" />\n'
             '\t\t\t\t\t<Edge From="always_on.State" To="IsActive" />\n\t\t\t\t</ItemDescriptorTrigger>\n')
    for n, l in enumerate(looks):
        i, y = l["id"], 200 * n
        nodes += (f'\t\t\t\t<If Name="answer_if_{i}" PositionY="{y}" PositionX="300">\n'
                  f'\t\t\t\t\t<Edge From="chosen_{i}.State" To="Condition" />\n'
                  '\t\t\t\t\t<Edge From="ask_token.OnAcquire" To="Exec" />\n\t\t\t\t</If>\n'
                  f'\t\t\t\t<EventFunction Name="answer_{i}" PositionY="{y}" PositionX="600" MethodName="wh::entitymodule::CreatePlayerReward" DeclaringType="wh::entitymodule">\n'
                  f'\t\t\t\t\t<Constant Name="ItemClass" Value="{answer}" />\n\t\t\t\t\t<Constant Name="Amount" Value="{i}" />\n'
                  '\t\t\t\t\t<Constant Name="ShowUINotification" Value="false" />\n'
                  f'\t\t\t\t\t<Edge From="answer_if_{i}.True" To="Exec" />\n\t\t\t\t</EventFunction>\n')
    return nodes


# A beard without a mesh (Model="dummy"): it replaces any beard on the head of a woman, where one with a mesh crashes the
# game, and it makes the game's barber screen safe. Now she does not reach that screen,
# and it stays as a safeguard.
MESHLESS_BEARD = "m_beard_00"

# The soul of KCD2 Life's own character, ml_player. The frameworks put the look on it just as on Henry.
NEW_LIFE_SOUL = "e9f088ff-48e3-5fa1-b733-80504a56d1dc"


def new_life_nodes(looks, piece, started):
    """The look of KCD2 Life's own character, the soul ml_player. Life gives Henry the
    token of the look, the one in looks.toml, before SwitchPlayer, and the started token when it ends: SwitchPlayer does
    not show what was turned on before. As in KCD2 Life, a new life is chosen once, so the states are only turned
    on. piece(look, part) gives the component of each part."""
    nodes = ('\t\t\t\t<Function Name="new_started_descriptor" PositionY="-900" PositionX="900" MethodName="wh::entitymodule::CreateItemClassDescriptor" DeclaringType="wh::entitymodule">\n'
             f'\t\t\t\t\t<Constant Name="ItemClass" Value="{started}" />\n\t\t\t\t\t<Constant Name="Amount" Value="1" />\n\t\t\t\t</Function>\n'
             '\t\t\t\t<ItemDescriptorTrigger Name="new_started_token" PositionY="-900" PositionX="1200">\n'
             '\t\t\t\t\t<Edge From="henry.Inventory" To="Inventory" />\n'
             '\t\t\t\t\t<Edge From="new_started_descriptor.ItemDescriptor" To="ItemDescriptor" />\n'
             '\t\t\t\t\t<Edge From="always_on.State" To="IsActive" />\n\t\t\t\t</ItemDescriptorTrigger>\n'
             '\t\t\t\t<State Name="new_in_use" PositionY="-900" PositionX="1500" TypeT="bool">\n'
             '\t\t\t\t\t<Constant Name="DefaultValue" Value="false" />\n'
             '\t\t\t\t\t<Edge From="new_started_token.OnAcquire" To="SetTrue" />\n\t\t\t\t</State>\n')
    for n, l in enumerate(looks):
        i, y = l["id"], 200 * n
        nodes += (f'\t\t\t\t<Function Name="new_descriptor_{i}" PositionY="{y}" PositionX="900" MethodName="wh::entitymodule::CreateItemClassDescriptor" DeclaringType="wh::entitymodule">\n'
                  f'\t\t\t\t\t<Constant Name="ItemClass" Value="{l["token"]}" />\n\t\t\t\t\t<Constant Name="Amount" Value="1" />\n\t\t\t\t</Function>\n'
                  f'\t\t\t\t<ItemDescriptorTrigger Name="new_token_{i}" PositionY="{y}" PositionX="1200">\n'
                  '\t\t\t\t\t<Edge From="henry.Inventory" To="Inventory" />\n'
                  f'\t\t\t\t\t<Edge From="new_descriptor_{i}.ItemDescriptor" To="ItemDescriptor" />\n'
                  '\t\t\t\t\t<Edge From="always_on.State" To="IsActive" />\n\t\t\t\t</ItemDescriptorTrigger>\n'
                  f'\t\t\t\t<State Name="new_chosen_{i}" PositionY="{y}" PositionX="1500" TypeT="bool">\n'
                  '\t\t\t\t\t<Constant Name="DefaultValue" Value="false" />\n'
                  f'\t\t\t\t\t<Edge From="new_token_{i}.OnAcquire" To="SetTrue" />\n\t\t\t\t</State>\n'
                  f'\t\t\t\t<Function Name="new_on_{i}" PositionY="{y}" PositionX="1800" MethodName="math::boolean::And" DeclaringType="math::boolean">\n'
                  f'\t\t\t\t\t<Edge From="new_chosen_{i}.State" To="A" />\n\t\t\t\t\t<Edge From="new_in_use.State" To="B" />\n\t\t\t\t</Function>\n'
                  + "".join(
                      f'\t\t\t\t<BodyPartOverride Name="new_{part}_{i}" PositionY="{y + 70 * k}" PositionX="2100">\n'
                      '\t\t\t\t\t<Asset Name="Soul" Alias="new_life" />\n'
                      f'\t\t\t\t\t<Constant Name="BodyPart" Value="{part.capitalize()}" />\n'
                      f'\t\t\t\t\t<Constant Name="Component" Value="{piece(l, part)}" />\n'
                      f'\t\t\t\t\t<Edge From="new_on_{i}.bool" To="IsActive" />\n\t\t\t\t</BodyPartOverride>\n'
                      for k, part in enumerate(("head", "body"))))
    return nodes


def add_new_prefix(rules):
    """Henry's clothes rules, for the new character: every node with new_ in front, and on its soul."""
    names = set(re.findall(r'<(?:SetGameContext|State|Function|MakeArray|MemberFunction|If|Timer|EventFunction) Name="([a-z_]+)"', rules))
    renames = {n: "new_" + n for n in names} | {"woman": "new_woman", "watch": "new_watch", "henry": "new_life_props"}
    rules = re.sub(r'(<(?:SetGameContext|State|Function|MakeArray|MemberFunction|If|Timer|EventFunction) Name=")([a-z_]+)"',
                   lambda m: f'{m.group(1)}{renames[m.group(2)]}"', rules)
    rules = re.sub(r'From="([a-z_]+)\.', lambda m: f'From="{renames.get(m.group(1), m.group(1))}.', rules)
    return rules.replace('Alias="henry"', 'Alias="new_life"')


def write_kcdmf_standalone(looks):
    """KCDMF on Henry, without other mods: one token per look and one that takes it off. The graph
    turns on the head and the body of the look on Henry's soul, and tells which one it is if Lua asks. ml_mf_state is no
    longer used: it is only kept to remove it from older saves."""
    folder = GENDERS["man"]["folder"]
    reset, state, own_face = guid("ml_mf_reset"), guid("ml_mf_state"), guid("ml_mf_henry_face")
    ask, answer, started = guid("ml_mf_ask"), guid("ml_mf_answer"), guid("ml_mf_new_started")
    # The barber: a free haircut, and its price, the game's or that of Realish Economy, for a moment on each load.
    free, low, game = guid("ml_mf_free_haircut"), guid("ml_mf_price_low"), guid("ml_mf_price_game")
    tokens = {l["id"]: guid(f"ml_mf_set_{l['head']}") for l in looks}
    # Tokens.
    path = folder / f"data/Libs/Tables/item/item__{folder.name}.xml"
    text = read_file(path)
    template = re.search(r'\t\t<MiscItem [^\n]*Name="ml_mf_look_\d+" />', text).group(0)
    text = re.sub(r'\t\t<!-- On Henry:[^\n]*-->\n', "", text)
    text = re.sub(r'\t\t<MiscItem [^\n]*Name="ml_mf_(?:set_\d+|reset|state|henry_face|ask|answer|new_started|free_haircut|price_low|price_game)" />\n', "", text)
    text = text.replace(SCENE_REBUILD_ROW, "")
    row = lambda g, n: re.sub(r'Id="[^"]+" Name="[^"]+"', f'Id="{g}" Name="{n}"', template) + "\n"
    text = text.replace("\t</ItemClasses>",
                        "\t\t<!-- On Henry: one token per look, one that takes it away, and the question and the answer of the look he wears, and the one of a scene that dressed him, for a moment. ml_mf_state is from older saves. -->\n"
                        + "".join(row(tokens[l["id"]], f"ml_mf_set_{l['id']}") for l in looks)
                        + row(reset, "ml_mf_reset") + row(state, "ml_mf_state") + row(own_face, "ml_mf_henry_face")
                        + row(ask, "ml_mf_ask") + row(answer, "ml_mf_answer") + row(started, "ml_mf_new_started")
                        + row(free, "ml_mf_free_haircut") + row(low, "ml_mf_price_low") + row(game, "ml_mf_price_game")
                        + SCENE_REBUILD_ROW
                        + "\t</ItemClasses>", 1)
    write_file(path, text)
    # Graph.
    nodes = [answer_nodes(looks, ask, answer), new_life_nodes(looks, lambda l, part: l[part], started),
        '\t\t\t\t<ObjectProperties Name="henry" PositionY="0" PositionX="-1200" DeclaringType="wh::rpgmodule::I_Soul">\n'
        '\t\t\t\t\t<Asset Name="I_Soul" Alias="henry" />\n\t\t\t\t</ObjectProperties>\n'
        '\t\t\t\t<State Name="always_on" PositionY="-150" PositionX="-1200" TypeT="bool">\n'
        '\t\t\t\t\t<Constant Name="DefaultValue" Value="true" />\n\t\t\t\t</State>\n'
        '\t\t\t\t<Function Name="reset_descriptor" PositionY="-300" PositionX="-900" MethodName="wh::entitymodule::CreateItemClassDescriptor" DeclaringType="wh::entitymodule">\n'
        f'\t\t\t\t\t<Constant Name="ItemClass" Value="{reset}" />\n\t\t\t\t\t<Constant Name="Amount" Value="1" />\n\t\t\t\t</Function>\n'
        '\t\t\t\t<ItemDescriptorTrigger Name="reset_token" PositionY="-300" PositionX="-600">\n'
        '\t\t\t\t\t<Edge From="henry.Inventory" To="Inventory" />\n'
        '\t\t\t\t\t<Edge From="reset_descriptor.ItemDescriptor" To="ItemDescriptor" />\n'
        '\t\t\t\t\t<Edge From="always_on.State" To="IsActive" />\n\t\t\t\t</ItemDescriptorTrigger>\n'
        # Henry's head and body as one more look. Barber:Commit saves in the soul the head that is shown, so to give
        # him back his own it has to be shown and confirmed.
        '\t\t\t\t<Function Name="henry_descriptor" PositionY="-450" PositionX="-900" MethodName="wh::entitymodule::CreateItemClassDescriptor" DeclaringType="wh::entitymodule">\n'
        f'\t\t\t\t\t<Constant Name="ItemClass" Value="{own_face}" />\n\t\t\t\t\t<Constant Name="Amount" Value="1" />\n\t\t\t\t</Function>\n'
        '\t\t\t\t<ItemDescriptorTrigger Name="henry_token" PositionY="-450" PositionX="-600">\n'
        '\t\t\t\t\t<Edge From="henry.Inventory" To="Inventory" />\n'
        '\t\t\t\t\t<Edge From="henry_descriptor.ItemDescriptor" To="ItemDescriptor" />\n'
        '\t\t\t\t\t<Edge From="always_on.State" To="IsActive" />\n\t\t\t\t</ItemDescriptorTrigger>\n'
        '\t\t\t\t<State Name="henry_face" PositionY="-450" PositionX="-300" TypeT="bool">\n'
        '\t\t\t\t\t<Constant Name="DefaultValue" Value="false" />\n'
        '\t\t\t\t\t<Edge From="henry_token.OnAcquire" To="SetTrue" />\n'
        '\t\t\t\t\t<Edge From="reset_token.OnAcquire" To="SetFalse" />\n\t\t\t\t</State>\n'
        + "".join(
            f'\t\t\t\t<BodyPartOverride Name="henry_{part}" PositionY="{-450 + 70 * k}" PositionX="0">\n'
            '\t\t\t\t\t<Asset Name="Soul" Alias="henry" />\n'
            f'\t\t\t\t\t<Constant Name="BodyPart" Value="{part.capitalize()}" />\n'
            f'\t\t\t\t\t<Constant Name="Component" Value="{piece}" />\n'
            '\t\t\t\t\t<Edge From="henry_face.State" To="IsActive" />\n\t\t\t\t</BodyPartOverride>\n'
            for k, (part, piece) in enumerate((("head", "henry"), ("body", "henry_body"), ("underwear", HENRY_UNDERWEAR))))]
    for n, l in enumerate(looks):
        i, y = l["id"], 200 * n
        nodes.append(
            f'\t\t\t\t<Function Name="set_descriptor_{i}" PositionY="{y}" PositionX="-900" MethodName="wh::entitymodule::CreateItemClassDescriptor" DeclaringType="wh::entitymodule">\n'
            f'\t\t\t\t\t<Constant Name="ItemClass" Value="{tokens[i]}" />\n\t\t\t\t\t<Constant Name="Amount" Value="1" />\n\t\t\t\t</Function>\n'
            f'\t\t\t\t<ItemDescriptorTrigger Name="set_token_{i}" PositionY="{y}" PositionX="-600">\n'
            '\t\t\t\t\t<Edge From="henry.Inventory" To="Inventory" />\n'
            f'\t\t\t\t\t<Edge From="set_descriptor_{i}.ItemDescriptor" To="ItemDescriptor" />\n'
            '\t\t\t\t\t<Edge From="always_on.State" To="IsActive" />\n\t\t\t\t</ItemDescriptorTrigger>\n'
            f'\t\t\t\t<State Name="chosen_{i}" PositionY="{y}" PositionX="-300" TypeT="bool">\n'
            '\t\t\t\t\t<Constant Name="DefaultValue" Value="false" />\n'
            f'\t\t\t\t\t<Edge From="set_token_{i}.OnAcquire" To="SetTrue" />\n'
            '\t\t\t\t\t<Edge From="reset_token.OnAcquire" To="SetFalse" />\n\t\t\t\t</State>\n'
            + "".join(
                f'\t\t\t\t<BodyPartOverride Name="{part}_{i}" PositionY="{y + 70 * k}" PositionX="0">\n'
                '\t\t\t\t\t<Asset Name="Soul" Alias="henry" />\n'
                f'\t\t\t\t\t<Constant Name="BodyPart" Value="{part.capitalize()}" />\n'
                f'\t\t\t\t\t<Constant Name="Component" Value="{piece}" />\n'
                f'\t\t\t\t\t<Edge From="chosen_{i}.State" To="IsActive" />\n\t\t\t\t</BodyPartOverride>\n'
                for k, (part, piece) in enumerate((("head", l["head"]), ("body", l["body"]), ("underwear", HENRY_UNDERWEAR)))))
    write_file(folder / "data/Quests/kcd_male_framework/ml_mf_face.xml",
               '<?xml version="1.0" encoding="utf-8"?>\n'
               '<Database xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" Name="brambora">\n'
               '\t<!-- Generated by tools/generate_models.py from looks.toml. Edit that file, not this one. The face of a look on Henry\n'
               '\t     himself: its token turns on its head and body, and the reset token turns every look off. The states live in the\n'
               '\t     project, so every map and every save keeps them, and the ask token gets as many answer tokens as the id of the\n'
               '\t     look on. The new_ nodes put the look on the character of KCD2 Life. -->\n'
               '\t<Skald>\n\t\t<Module Name="ml_mf_face">\n\t\t\t<Nodes>\n' + "".join(nodes)
               + '\t\t\t</Nodes>\n\t\t\t<Assets>\n'
               f'\t\t\t\t<SoulAsset Name="henry" SharedSoulGuids="{HENRY_SOUL}" />\n'
               f'\t\t\t\t<SoulAsset Name="new_life" SharedSoulGuids="{NEW_LIFE_SOUL}" />\n'
               '\t\t\t</Assets>\n\t\t\t<Text Text="ml_mf_face" />\n\t\t</Module>\n\t</Skald>\n</Database>\n')
    hairs, beards = write_kcdmf_barber(free, low, game)
    # Lua.
    lua = ["-- Generated by tools/generate_models.py from looks.toml. Edit that file, not this one. The looks in menu order, each",
           "-- with its id, shared with KCD2 Female Framework, the hair and beard it starts with, and its token on Henry.",
           f'MaleCore.RESET_TOKEN = "{reset}"', f'MaleCore.HENRY_TOKEN = "{own_face}"',
           f'MaleCore.ASK_TOKEN = "{ask}"', f'MaleCore.ANSWER_ITEM = "{answer}"',
           "-- Older saves kept the look in its amount: it is only taken away.", f'MaleCore.OLD_STATE_ITEM = "{state}"',
           "-- KCD2 Life gives it to Henry when SwitchPlayer ends: its new character is in use.", f'MaleCore.NEW_STARTED_TOKEN = "{started}"',
           "-- With it in Henry's inventory, his next haircut at a barber is free (ml_mf_barber.xml).", f'MaleCore.FREE_HAIRCUT_TOKEN = "{free}"',
           "-- One of these on each load sets the price of his haircut: 5 groschen with Realish Economy, or the game's 50.",
           f'MaleCore.PRICE_LOW_TOKEN = "{low}"', f'MaleCore.PRICE_GAME_TOKEN = "{game}"',
           "-- The hair and the beards of the barber of a man with a look, in the order of its talk (barber.toml).",
           "MaleCore.BARBER_HAIRS = { " + ", ".join(f'"{h["mesh"]}"' for h in hairs) + " }",
           "MaleCore.BARBER_BEARDS = { " + ", ".join(f'"{b["mesh"]}"' for b in beards) + " }",
           "-- Every hair of the game for a man: ml_mf_look and MaleCore.SetLook take any of them instead of the look's.",
           "MaleCore.HAIRS = {"]
    hair_names = man_hairs()
    lua += ["\t" + ", ".join(f'"{h}"' for h in hair_names[i:i + 6]) + "," for i in range(0, len(hair_names), 6)]
    lua += ["}",
           "-- A scene of the game gives it when it dresses the player or takes the outfit off: the face rebuilds (the pillory).",
           "-- KCD2 Female Framework has the same one.",
           f'MaleCore.SCENE_REBUILD_TOKEN = "{SCENE_REBUILD_TOKEN}"',
           "-- new_token picks the look of that new character, and soul is the model that shows it in a selector. characters",
           "-- are the characters of the game with a name of their own who wear its face (LOOKS.md). beards are those its head",
           "-- has a mesh for, which ml_mf_look takes instead of the look's.",
           "MaleCore.LOOKS = {"]
    files = head_files()
    for l in looks:
        ethnicity = f'"{l["ethnicity"]}"' if l["ethnicity"] else "nil"
        lua.append(f'\t{{ id = {l["id"]}, name = "{l["name"]}", ethnicity = {ethnicity}, age = "{l["age"]}", '
                   f'villager = {"true" if l["villager"] else "false"}, hair = "{l["hair"]}", beard = "{l["beard"]}", token = "{tokens[l["id"]]}", '
                   f'new_token = "{l["token"]}", soul = "{l["soul"]}", beards = {lua_list(head_beards(files, l["head"]))}, '
                   f'characters = {lua_list(c["name"] for c in l["characters"])} }},')
    lua += ["}", ""]
    write_file(folder / "data/Scripts/MaleCore/looks_data.lua", "\n".join(lua))


# The garments that the clothes rules of KCDFF take off, and the text that tells about each one. not_men is for Henry
# back as a man.
CLOTHES_NOTICES = {"torso": "ml_ff_stripped_torso", "gloves": "ml_ff_stripped_gloves", "legs": "ml_ff_stripped_legs",
                   "shoes": "ml_ff_stripped_shoes", "cap": "ml_ff_stripped_cap", "not_men": "ml_ff_stripped_not_men"}

# The clothes rules of ml_look.xml of KCD2 Life, on Henry's soul. Without the men's clothes flag or the naked one,
# which belong to KCD2 Life. watch checks them once per second from the first look: the woman's rules while he is a
# woman, and after ml_ff_henry the ones that do not let a man wear her copies.
CLOTHES_RULES = """\
				<!-- Lua cannot read what Henry wears, so Skald looks once per second: the clothes of a woman give a buff when equipped, and
				     men's clothes are in a slot without that buff. A dress sends off men's clothes from the torso, the hands and the legs;
				     men's clothes on the chest send off women's shoes and headwear. With the chest free anything goes. Each token tells
				     Lua what came off. -->
				<If Name="if_woman_watch" PositionY="-1650" PositionX="-900">
					<Edge From="woman.State" To="Condition" />
					<Edge From="watch.OnFinished" To="Exec" />
				</If>
				<Function Name="dress_on_woman" PositionY="-1500" PositionX="-150" MethodName="math::boolean::And" DeclaringType="math::boolean">
					<Edge From="dress_worn.State" To="A" />
					<Edge From="woman.State" To="B" />
				</Function>
				<SetGameContext Name="no_naked_reactions" PositionY="-1500" PositionX="0">
					<Constant Name="Context" Value="speech_disableNakedPlayerReactions" />
					<Edge From="dress_on_woman.bool" To="IsActive" />
				</SetGameContext>
				<State Name="dress_worn" PositionY="-1500" PositionX="-300" TypeT="bool">
					<Constant Name="DefaultValue" Value="false" />
					<Edge From="if_dress.True" To="SetTrue" />
					<Edge From="if_dress.False" To="SetFalse" />
				</State>
				<Function Name="wears_dress" PositionY="-1350" PositionX="-1200" MethodName="wh::rpgmodule::BuffTagCheck" DeclaringType="wh::rpgmodule">
					<Asset Name="Souls" Alias="henry" />
					<Constant Name="BuffTag" Value="200" />
				</Function>
				<Function Name="wears_shoes" PositionY="-1300" PositionX="-1200" MethodName="wh::rpgmodule::BuffTagCheck" DeclaringType="wh::rpgmodule">
					<Asset Name="Souls" Alias="henry" />
					<Constant Name="BuffTag" Value="201" />
				</Function>
				<Function Name="wears_cap" PositionY="-1250" PositionX="-1200" MethodName="wh::rpgmodule::BuffTagCheck" DeclaringType="wh::rpgmodule">
					<Asset Name="Souls" Alias="henry" />
					<Constant Name="BuffTag" Value="202" />
				</Function>
				<MakeArray Name="chest_slots" PositionY="-1200" PositionX="-1500" TypeT="wh::entitymodule::EquipmentSlotIds">
					<Constant Name="A" Value="body_cloth" />
					<Constant Name="B" Value="body_cloth_padded" />
					<Constant Name="C" Value="body_coat" />
					<Constant Name="D" Value="body_chainmail" />
					<Constant Name="E" Value="body_plate" />
				</MakeArray>
				<MakeArray Name="man_torso_slots" PositionY="-1150" PositionX="-1500" TypeT="wh::entitymodule::EquipmentSlotIds">
					<Constant Name="A" Value="body_cloth_padded" />
					<Constant Name="B" Value="body_coat" />
					<Constant Name="C" Value="body_chainmail" />
					<Constant Name="D" Value="body_plate" />
				</MakeArray>
				<MakeArray Name="gloves_slot" PositionY="-1100" PositionX="-1500" TypeT="wh::entitymodule::EquipmentSlotIds">
					<Constant Name="A" Value="gloves" />
				</MakeArray>
				<MakeArray Name="leg_slots" PositionY="-1050" PositionX="-1500" TypeT="wh::entitymodule::EquipmentSlotIds">
					<Constant Name="A" Value="leg_trousers" />
					<Constant Name="B" Value="leg_trousers_padded" />
					<Constant Name="C" Value="leg_armor" />
				</MakeArray>
				<MakeArray Name="boot_slot" PositionY="-1000" PositionX="-1500" TypeT="wh::entitymodule::EquipmentSlotIds">
					<Constant Name="A" Value="boot" />
				</MakeArray>
				<MakeArray Name="cap_slot" PositionY="-950" PositionX="-1500" TypeT="wh::entitymodule::EquipmentSlotIds">
					<Constant Name="A" Value="head_cap" />
				</MakeArray>
				<MemberFunction Name="bare_chest" PositionY="-1200" PositionX="-1200" MethodName="CheckEquipment" DeclaringType="wh::rpgmodule::I_Soul">
					<Asset Name="Soul" Alias="henry" />
					<Edge From="chest_slots.Array" To="FreeSlots" />
				</MemberFunction>
				<MemberFunction Name="free_man_torso" PositionY="-1150" PositionX="-1200" MethodName="CheckEquipment" DeclaringType="wh::rpgmodule::I_Soul">
					<Asset Name="Soul" Alias="henry" />
					<Edge From="man_torso_slots.Array" To="FreeSlots" />
				</MemberFunction>
				<MemberFunction Name="free_gloves" PositionY="-1100" PositionX="-1200" MethodName="CheckEquipment" DeclaringType="wh::rpgmodule::I_Soul">
					<Asset Name="Soul" Alias="henry" />
					<Edge From="gloves_slot.Array" To="FreeSlots" />
				</MemberFunction>
				<MemberFunction Name="free_legs" PositionY="-1050" PositionX="-1200" MethodName="CheckEquipment" DeclaringType="wh::rpgmodule::I_Soul">
					<Asset Name="Soul" Alias="henry" />
					<Edge From="leg_slots.Array" To="FreeSlots" />
				</MemberFunction>
				<Function Name="man_torso_on" PositionY="-1150" PositionX="-900" MethodName="math::boolean::Not" DeclaringType="math::boolean">
					<Edge From="free_man_torso.bool" To="Value" />
				</Function>
				<Function Name="gloves_on" PositionY="-1100" PositionX="-900" MethodName="math::boolean::Not" DeclaringType="math::boolean">
					<Edge From="free_gloves.bool" To="Value" />
				</Function>
				<Function Name="legs_on" PositionY="-1050" PositionX="-900" MethodName="math::boolean::Not" DeclaringType="math::boolean">
					<Edge From="free_legs.bool" To="Value" />
				</Function>
				<Function Name="no_dress" PositionY="-1350" PositionX="-900" MethodName="math::boolean::Not" DeclaringType="math::boolean">
					<Edge From="wears_dress.HaveBuffTag" To="Value" />
				</Function>
				<Function Name="covered_chest" PositionY="-1200" PositionX="-900" MethodName="math::boolean::Not" DeclaringType="math::boolean">
					<Edge From="bare_chest.bool" To="Value" />
				</Function>
				<Function Name="man_chest" PositionY="-1250" PositionX="-750" MethodName="math::boolean::And" DeclaringType="math::boolean">
					<Edge From="covered_chest.bool" To="A" />
					<Edge From="no_dress.bool" To="B" />
				</Function>
				<If Name="if_dress" PositionY="-1350" PositionX="-600">
					<Edge From="wears_dress.HaveBuffTag" To="Condition" />
					<Edge From="if_woman_watch.True" To="Exec" />
				</If>
				<If Name="if_man_chest" PositionY="-1250" PositionX="-600">
					<Edge From="man_chest.bool" To="Condition" />
					<Edge From="if_woman_watch.True" To="Exec" />
				</If>
				<If Name="if_man_torso" PositionY="-1150" PositionX="-450">
					<Edge From="man_torso_on.bool" To="Condition" />
					<Edge From="if_dress.True" To="Exec" />
				</If>
				<If Name="if_gloves" PositionY="-1100" PositionX="-450">
					<Edge From="gloves_on.bool" To="Condition" />
					<Edge From="if_dress.True" To="Exec" />
				</If>
				<If Name="if_man_legs" PositionY="-1050" PositionX="-450">
					<Edge From="legs_on.bool" To="Condition" />
					<Edge From="if_dress.True" To="Exec" />
				</If>
				<If Name="if_woman_shoes" PositionY="-1000" PositionX="-450">
					<Edge From="wears_shoes.HaveBuffTag" To="Condition" />
					<Edge From="if_man_chest.True" To="Exec" />
				</If>
				<If Name="if_woman_cap" PositionY="-950" PositionX="-450">
					<Edge From="wears_cap.HaveBuffTag" To="Condition" />
					<Edge From="if_man_chest.True" To="Exec" />
				</If>
				<MemberFunction Name="strip_man_torso" PositionY="-1150" PositionX="-150" MethodName="UnequipPlayersArmorSlots" DeclaringType="wh::entitymodule::EquipmentManager">
					<Edge From="man_torso_slots.Array" To="ArmorSlots" />
					<Edge From="henry.EquipmentManager" To="EquipmentManager" />
					<Edge From="if_man_torso.True" To="Exec" />
				</MemberFunction>
				<MemberFunction Name="strip_gloves" PositionY="-1100" PositionX="-150" MethodName="UnequipPlayersArmorSlots" DeclaringType="wh::entitymodule::EquipmentManager">
					<Edge From="gloves_slot.Array" To="ArmorSlots" />
					<Edge From="henry.EquipmentManager" To="EquipmentManager" />
					<Edge From="if_gloves.True" To="Exec" />
				</MemberFunction>
				<MemberFunction Name="strip_man_legs" PositionY="-1050" PositionX="-150" MethodName="UnequipPlayersArmorSlots" DeclaringType="wh::entitymodule::EquipmentManager">
					<Edge From="leg_slots.Array" To="ArmorSlots" />
					<Edge From="henry.EquipmentManager" To="EquipmentManager" />
					<Edge From="if_man_legs.True" To="Exec" />
				</MemberFunction>
				<MemberFunction Name="strip_boot" PositionY="-1000" PositionX="-150" MethodName="UnequipPlayersArmorSlots" DeclaringType="wh::entitymodule::EquipmentManager">
					<Edge From="boot_slot.Array" To="ArmorSlots" />
					<Edge From="henry.EquipmentManager" To="EquipmentManager" />
					<Edge From="if_woman_shoes.True" To="Exec" />
					<Edge From="if_man_in_shoes.True" To="Exec" />
				</MemberFunction>
				<MemberFunction Name="strip_cap" PositionY="-950" PositionX="-150" MethodName="UnequipPlayersArmorSlots" DeclaringType="wh::entitymodule::EquipmentManager">
					<Edge From="cap_slot.Array" To="ArmorSlots" />
					<Edge From="henry.EquipmentManager" To="EquipmentManager" />
					<Edge From="if_woman_cap.True" To="Exec" />
					<Edge From="if_man_in_cap.True" To="Exec" />
				</MemberFunction>
				<!-- After ml_ff_henry, a man cannot wear what belongs to a woman: her copies are in the tree of men. -->
				<MakeArray Name="dress_slot" PositionY="-850" PositionX="-1500" TypeT="wh::entitymodule::EquipmentSlotIds">
					<Constant Name="A" Value="body_cloth" />
				</MakeArray>
				<If Name="if_man_in_dress" PositionY="-850" PositionX="-450">
					<Edge From="wears_dress.HaveBuffTag" To="Condition" />
					<Edge From="if_woman_watch.False" To="Exec" />
				</If>
				<If Name="if_man_in_shoes" PositionY="-800" PositionX="-450">
					<Edge From="wears_shoes.HaveBuffTag" To="Condition" />
					<Edge From="if_woman_watch.False" To="Exec" />
				</If>
				<If Name="if_man_in_cap" PositionY="-750" PositionX="-450">
					<Edge From="wears_cap.HaveBuffTag" To="Condition" />
					<Edge From="if_woman_watch.False" To="Exec" />
				</If>
				<MemberFunction Name="strip_dress" PositionY="-850" PositionX="-150" MethodName="UnequipPlayersArmorSlots" DeclaringType="wh::entitymodule::EquipmentManager">
					<Edge From="dress_slot.Array" To="ArmorSlots" />
					<Edge From="henry.EquipmentManager" To="EquipmentManager" />
					<Edge From="if_man_in_dress.True" To="Exec" />
				</MemberFunction>
"""
# Which rules give each notice.
NOTICE_RULES = {"torso": ["if_man_torso"], "gloves": ["if_gloves"], "legs": ["if_man_legs"], "shoes": ["if_woman_shoes"],
                "cap": ["if_woman_cap"], "not_men": ["if_man_in_dress", "if_man_in_shoes", "if_man_in_cap"]}


def write_kcdff_standalone(looks):
    """KCDFF on Henry, without other mods. Like KCDMF: one token per look, one that takes
    them off, and the question and the answer of the look worn. With the first look Henry becomes a woman: the women's
    underwear and the clothes rules turn on, on his soul. Henry's token puts on his head and his body, as in KCDMF,
    and makes him a man again. They stay on until she is a woman again, or a look of KCDMF takes their place: a Commit
    does not give his head back to his soul after hers. ml_ff_state is no longer used:
    it is only kept to remove it from older saves."""
    folder = GENDERS["woman"]["folder"]
    reset, state, own_face = guid("ml_ff_reset"), guid("ml_ff_state"), guid("ml_ff_henry_face")
    ask, answer, started = guid("ml_ff_ask"), guid("ml_ff_answer"), guid("ml_ff_new_started")
    free_haircut = guid("ml_ff_free_haircut")
    # The price of her haircut, for a moment on each load: the game's, or that of Realish Economy.
    price_low, price_game = guid("ml_ff_price_low"), guid("ml_ff_price_game")
    tokens = {l["id"]: guid(f"ml_ff_set_{l['head']}") for l in looks}
    notices = {part: guid(f"ml_ff_henry_stripped_{part}") for part in CLOTHES_NOTICES}
    # The answer adds these to the id of the look, so every id must stay below the first one.
    if max(l["id"] for l in looks) >= HENRY_KEPT_ANSWER:
        raise SystemExit(f"A look id reaches {HENRY_KEPT_ANSWER}: raise HENRY_KEPT_ANSWER and WAS_WOMAN_ANSWER")
    # Tokens.
    path = folder / f"data/Libs/Tables/item/item__{folder.name}.xml"
    text = read_file(path)
    template = re.search(r'\t\t<MiscItem [^\n]*Name="ml_ff_look_\d+" />', text).group(0)
    # The comment takes more than one line: without re.S it stayed, and every run added another one.
    text = re.sub(r'\t\t<!-- On Henry:.*?-->\n', "", text, flags=re.S)
    text = re.sub(r'\t\t<MiscItem [^\n]*Name="ml_ff_(?:set_\d+|reset|state|henry_face|ask|answer|new_started|free_haircut|price_low|price_game|rebuild|henry_stripped_[a-z_]+)" />\n', "", text)
    text = text.replace(SCENE_REBUILD_ROW, "")
    row = lambda g, n: re.sub(r'Id="[^"]+" Name="[^"]+"', f'Id="{g}" Name="{n}"', template) + "\n"
    text = text.replace("\t</ItemClasses>",
                        "\t\t<!-- On Henry: one token per look, one that takes it away, the question and the answer of the look she wears, and the\n"
                        "\t\t     ones that say what clothes came off, the one of a free haircut and those of its price, and the one of a scene that\n"
                        "\t\t     dressed her, for a moment. ml_ff_state is from older saves. -->\n"
                        + "".join(row(tokens[l["id"]], f"ml_ff_set_{l['id']}") for l in looks)
                        + row(reset, "ml_ff_reset") + row(state, "ml_ff_state") + row(own_face, "ml_ff_henry_face")
                        + row(ask, "ml_ff_ask") + row(answer, "ml_ff_answer") + row(started, "ml_ff_new_started")
                        + row(free_haircut, "ml_ff_free_haircut") + row(price_low, "ml_ff_price_low") + row(price_game, "ml_ff_price_game")
                        + SCENE_REBUILD_ROW
                        + "".join(row(g, f"ml_ff_henry_stripped_{p}") for p, g in notices.items())
                        + "\t</ItemClasses>", 1)
    write_file(path, text)
    # Graph. The clothes rules, with their notices, go on Henry and, with new_ in front, on the character of KCD2 Life.
    rules = CLOTHES_RULES + "".join(
        f'\t\t\t\t<EventFunction Name="told_{p}" PositionY="{-1150 + 50 * k}" PositionX="150" MethodName="wh::entitymodule::CreatePlayerReward" DeclaringType="wh::entitymodule">\n'
        f'\t\t\t\t\t<Constant Name="ItemClass" Value="{notices[p]}" />\n\t\t\t\t\t<Constant Name="Amount" Value="1" />\n'
        '\t\t\t\t\t<Constant Name="ShowUINotification" Value="false" />\n'
        + "".join(f'\t\t\t\t\t<Edge From="{rule}.True" To="Exec" />\n' for rule in NOTICE_RULES[p])
        + '\t\t\t\t</EventFunction>\n'
        for k, p in enumerate(CLOTHES_NOTICES))
    new_nodes = (new_life_nodes(looks, lambda l, part: component(l, "woman")(part), started)
                 + '\t\t\t\t<ObjectProperties Name="new_life_props" PositionY="-1050" PositionX="1500" DeclaringType="wh::rpgmodule::I_Soul">\n'
                 '\t\t\t\t\t<Asset Name="I_Soul" Alias="new_life" />\n\t\t\t\t</ObjectProperties>\n'
                 # Every life of KCDFF is a woman's, and her rules run once per second from when the character is in use. With
                 # a man's life, the men's rules: he does not wear the women's copies.
                 '\t\t\t\t<State Name="new_woman" PositionY="-1200" PositionX="1500" TypeT="bool">\n'
                 '\t\t\t\t\t<Constant Name="DefaultValue" Value="false" />\n'
                 + "".join(f'\t\t\t\t\t<Edge From="new_token_{l["id"]}.OnAcquire" To="SetTrue" />\n' for l in looks)
                 + '\t\t\t\t</State>\n'
                 '\t\t\t\t<Function Name="new_woman_on" PositionY="-1200" PositionX="1800" MethodName="math::boolean::And" DeclaringType="math::boolean">\n'
                 '\t\t\t\t\t<Edge From="new_woman.State" To="A" />\n\t\t\t\t\t<Edge From="new_in_use.State" To="B" />\n\t\t\t\t</Function>\n'
                 '\t\t\t\t<BodyPartOverride Name="new_woman_underwear" PositionY="-1200" PositionX="2100">\n'
                 '\t\t\t\t\t<Asset Name="Soul" Alias="new_life" />\n'
                 '\t\t\t\t\t<Constant Name="BodyPart" Value="Underwear" />\n'
                 '\t\t\t\t\t<Constant Name="Component" Value="ml_ff_underwear01_m01" />\n'
                 '\t\t\t\t\t<Edge From="new_woman_on.bool" To="IsActive" />\n\t\t\t\t</BodyPartOverride>\n'
                 '\t\t\t\t<BodyPartOverride Name="new_woman_beard" PositionY="-1130" PositionX="2100">\n'
                 '\t\t\t\t\t<Asset Name="Soul" Alias="new_life" />\n'
                 '\t\t\t\t\t<Constant Name="BodyPart" Value="Beard" />\n'
                 f'\t\t\t\t\t<Constant Name="Component" Value="{MESHLESS_BEARD}" />\n'
                 '\t\t\t\t\t<Edge From="new_woman_on.bool" To="IsActive" />\n\t\t\t\t</BodyPartOverride>\n'
                 '\t\t\t\t<Timer Name="new_watch" PositionY="-1350" PositionX="1500">\n'
                 '\t\t\t\t\t<Constant Name="Duration" Value="1s" />\n\t\t\t\t\t<Constant Name="TimeType" Value="GameTime" />\n'
                 '\t\t\t\t\t<Edge From="new_started_token.OnAcquire" To="SetRunning" />\n'
                 '\t\t\t\t\t<Edge From="new_watch.OnFinished" To="SetRunning" />\n\t\t\t\t</Timer>\n'
                 + add_new_prefix(rules))
    nodes = [answer_nodes(looks, ask, answer), new_nodes,
        '\t\t\t\t<ObjectProperties Name="henry" PositionY="0" PositionX="-1200" DeclaringType="wh::rpgmodule::I_Soul">\n'
        '\t\t\t\t\t<Asset Name="I_Soul" Alias="henry" />\n\t\t\t\t</ObjectProperties>\n'
        '\t\t\t\t<State Name="always_on" PositionY="-150" PositionX="-1200" TypeT="bool">\n'
        '\t\t\t\t\t<Constant Name="DefaultValue" Value="true" />\n\t\t\t\t</State>\n'
        '\t\t\t\t<Function Name="reset_descriptor" PositionY="-300" PositionX="-900" MethodName="wh::entitymodule::CreateItemClassDescriptor" DeclaringType="wh::entitymodule">\n'
        f'\t\t\t\t\t<Constant Name="ItemClass" Value="{reset}" />\n\t\t\t\t\t<Constant Name="Amount" Value="1" />\n\t\t\t\t</Function>\n'
        '\t\t\t\t<ItemDescriptorTrigger Name="reset_token" PositionY="-300" PositionX="-600">\n'
        '\t\t\t\t\t<Edge From="henry.Inventory" To="Inventory" />\n'
        '\t\t\t\t\t<Edge From="reset_descriptor.ItemDescriptor" To="ItemDescriptor" />\n'
        '\t\t\t\t\t<Edge From="always_on.State" To="IsActive" />\n\t\t\t\t</ItemDescriptorTrigger>\n'
        # Henry's head and body as one more look, after ml_ff_henry. They stay on: after hers, a Commit did not give his
        # head back to his soul (204 and 209). The reset token takes them off for a look of KCDMF,
        # and a woman's look too.
        '\t\t\t\t<Function Name="henry_descriptor" PositionY="-450" PositionX="-900" MethodName="wh::entitymodule::CreateItemClassDescriptor" DeclaringType="wh::entitymodule">\n'
        f'\t\t\t\t\t<Constant Name="ItemClass" Value="{own_face}" />\n\t\t\t\t\t<Constant Name="Amount" Value="1" />\n\t\t\t\t</Function>\n'
        '\t\t\t\t<ItemDescriptorTrigger Name="henry_token" PositionY="-450" PositionX="-600">\n'
        '\t\t\t\t\t<Edge From="henry.Inventory" To="Inventory" />\n'
        '\t\t\t\t\t<Edge From="henry_descriptor.ItemDescriptor" To="ItemDescriptor" />\n'
        '\t\t\t\t\t<Edge From="always_on.State" To="IsActive" />\n\t\t\t\t</ItemDescriptorTrigger>\n'
        '\t\t\t\t<State Name="henry_face" PositionY="-450" PositionX="-300" TypeT="bool">\n'
        '\t\t\t\t\t<Constant Name="DefaultValue" Value="false" />\n'
        '\t\t\t\t\t<Edge From="henry_token.OnAcquire" To="SetTrue" />\n'
        '\t\t\t\t\t<Edge From="reset_token.OnAcquire" To="SetFalse" />\n'
        + "".join(f'\t\t\t\t\t<Edge From="set_token_{l["id"]}.OnAcquire" To="SetFalse" />\n' for l in looks)
        + '\t\t\t\t</State>\n'
        # Whether Henry was ever a woman in this save: then her head may be his soul's own, and KCDMF puts his head
        # back on through KCDFF when his own face comes back.
        # Henry's token too: a save where she became a woman with an older version has it off.
        '\t\t\t\t<State Name="was_woman" PositionY="-675" PositionX="-300" TypeT="bool">\n'
        '\t\t\t\t\t<Constant Name="DefaultValue" Value="false" />\n'
        + "".join(f'\t\t\t\t\t<Edge From="set_token_{l["id"]}.OnAcquire" To="SetTrue" />\n' for l in looks)
        + '\t\t\t\t\t<Edge From="henry_token.OnAcquire" To="SetTrue" />\n'
        '\t\t\t\t</State>\n'
        # The ask token also learns these three, added to the id of the look.
        + "".join(
            f'\t\t\t\t<If Name="answer_if_{name}" PositionY="{y}" PositionX="300">\n'
            f'\t\t\t\t\t<Edge From="{name}.State" To="Condition" />\n'
            '\t\t\t\t\t<Edge From="ask_token.OnAcquire" To="Exec" />\n\t\t\t\t</If>\n'
            f'\t\t\t\t<EventFunction Name="answer_{name}" PositionY="{y}" PositionX="600" MethodName="wh::entitymodule::CreatePlayerReward" DeclaringType="wh::entitymodule">\n'
            f'\t\t\t\t\t<Constant Name="ItemClass" Value="{answer}" />\n\t\t\t\t\t<Constant Name="Amount" Value="{amount}" />\n'
            '\t\t\t\t\t<Constant Name="ShowUINotification" Value="false" />\n'
            f'\t\t\t\t\t<Edge From="answer_if_{name}.True" To="Exec" />\n\t\t\t\t</EventFunction>\n'
            for name, amount, y in (("henry_face", HENRY_KEPT_ANSWER, -450), ("was_woman", WAS_WOMAN_ANSWER, -675),
                                    ("woman", WOMAN_ON_ANSWER, -600)))
        + "".join(
            f'\t\t\t\t<BodyPartOverride Name="henry_{part}" PositionY="{-450 + 70 * k}" PositionX="0">\n'
            '\t\t\t\t\t<Asset Name="Soul" Alias="henry" />\n'
            f'\t\t\t\t\t<Constant Name="BodyPart" Value="{part.capitalize()}" />\n'
            f'\t\t\t\t\t<Constant Name="Component" Value="{piece}" />\n'
            '\t\t\t\t\t<Edge From="henry_face.State" To="IsActive" />\n\t\t\t\t</BodyPartOverride>\n'
            for k, (part, piece) in enumerate((("head", "henry"), ("body", "henry_body"), ("underwear", HENRY_UNDERWEAR))))
        # A woman from the first look until ml_ff_henry. The reset turns it off too: a look of KCD2 Male Framework
        # sends it before its own, and with her underwear and her beard left on, her shift came out on his doubles. A
        # change of her look sends a token of a look right after the reset, which turns it on again.
        + '\t\t\t\t<State Name="woman" PositionY="-600" PositionX="-300" TypeT="bool">\n'
        '\t\t\t\t\t<Constant Name="DefaultValue" Value="false" />\n'
        + "".join(f'\t\t\t\t\t<Edge From="set_token_{l["id"]}.OnAcquire" To="SetTrue" />\n' for l in looks)
        + '\t\t\t\t\t<Edge From="henry_token.OnAcquire" To="SetFalse" />\n'
        '\t\t\t\t\t<Edge From="reset_token.OnAcquire" To="SetFalse" />\n'
        '\t\t\t\t</State>\n'
        '\t\t\t\t<BodyPartOverride Name="woman_underwear" PositionY="-600" PositionX="0">\n'
        '\t\t\t\t\t<Asset Name="Soul" Alias="henry" />\n'
        '\t\t\t\t\t<Constant Name="BodyPart" Value="Underwear" />\n'
        '\t\t\t\t\t<Constant Name="Component" Value="ml_ff_underwear01_m01" />\n'
        '\t\t\t\t\t<Edge From="woman.State" To="IsActive" />\n\t\t\t\t</BodyPartOverride>\n'
        # No beard on her head, whatever the game's barber screen chooses.
        '\t\t\t\t<BodyPartOverride Name="woman_beard" PositionY="-530" PositionX="0">\n'
        '\t\t\t\t\t<Asset Name="Soul" Alias="henry" />\n'
        '\t\t\t\t\t<Constant Name="BodyPart" Value="Beard" />\n'
        f'\t\t\t\t\t<Constant Name="Component" Value="{MESHLESS_BEARD}" />\n'
        '\t\t\t\t\t<Edge From="woman.State" To="IsActive" />\n\t\t\t\t</BodyPartOverride>\n'
        # A buff with no effect and no icon says that she is a woman, to the copies of the game's scenes that put
        # Henry's parts on the player (write_story_scenes).
        '\t\t\t\t<BuffEffect Name="woman_mark" PositionY="-460" PositionX="0">\n'
        '\t\t\t\t\t<Asset Name="Souls" Alias="henry" />\n'
        f'\t\t\t\t\t<Constant Name="BuffGUID" Value="{WOMAN_BUFF}" />\n'
        '\t\t\t\t\t<Edge From="woman.State" To="IsActive" />\n\t\t\t\t</BuffEffect>\n'
        '\t\t\t\t<Timer Name="watch" PositionY="-1500" PositionX="-1200">\n'
        '\t\t\t\t\t<Constant Name="Duration" Value="1s" />\n\t\t\t\t\t<Constant Name="TimeType" Value="GameTime" />\n'
        + "".join(f'\t\t\t\t\t<Edge From="set_token_{l["id"]}.OnAcquire" To="SetRunning" />\n' for l in looks)
        + '\t\t\t\t\t<Edge From="watch.OnFinished" To="SetRunning" />\n\t\t\t\t</Timer>\n'
        + rules]
    for n, l in enumerate(looks):
        i, y, c = l["id"], 200 * n, component(l, "woman")
        nodes.append(
            f'\t\t\t\t<Function Name="set_descriptor_{i}" PositionY="{y}" PositionX="-900" MethodName="wh::entitymodule::CreateItemClassDescriptor" DeclaringType="wh::entitymodule">\n'
            f'\t\t\t\t\t<Constant Name="ItemClass" Value="{tokens[i]}" />\n\t\t\t\t\t<Constant Name="Amount" Value="1" />\n\t\t\t\t</Function>\n'
            f'\t\t\t\t<ItemDescriptorTrigger Name="set_token_{i}" PositionY="{y}" PositionX="-600">\n'
            '\t\t\t\t\t<Edge From="henry.Inventory" To="Inventory" />\n'
            f'\t\t\t\t\t<Edge From="set_descriptor_{i}.ItemDescriptor" To="ItemDescriptor" />\n'
            '\t\t\t\t\t<Edge From="always_on.State" To="IsActive" />\n\t\t\t\t</ItemDescriptorTrigger>\n'
            f'\t\t\t\t<State Name="chosen_{i}" PositionY="{y}" PositionX="-300" TypeT="bool">\n'
            '\t\t\t\t\t<Constant Name="DefaultValue" Value="false" />\n'
            f'\t\t\t\t\t<Edge From="set_token_{i}.OnAcquire" To="SetTrue" />\n'
            '\t\t\t\t\t<Edge From="reset_token.OnAcquire" To="SetFalse" />\n\t\t\t\t</State>\n'
            + "".join(
                f'\t\t\t\t<BodyPartOverride Name="{part}_{i}" PositionY="{y + 70 * k}" PositionX="0">\n'
                '\t\t\t\t\t<Asset Name="Soul" Alias="henry" />\n'
                f'\t\t\t\t\t<Constant Name="BodyPart" Value="{part.capitalize()}" />\n'
                f'\t\t\t\t\t<Constant Name="Component" Value="{c(part)}" />\n'
                f'\t\t\t\t\t<Edge From="chosen_{i}.State" To="IsActive" />\n\t\t\t\t</BodyPartOverride>\n'
                for k, part in enumerate(("head", "body"))))
    write_file(folder / "data/Quests/kcd_female_framework/ml_ff_face.xml",
               '<?xml version="1.0" encoding="utf-8"?>\n'
               '<Database xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" Name="brambora">\n'
               '\t<!-- Generated by tools/generate_models.py from looks.toml. Edit that file, not this one. A woman\'s look on Henry\n'
               '\t     himself: its token turns on its head and body, and the reset token turns every look off. The first look makes him a\n'
               '\t     woman, with her underwear and the rules of her clothes, and Henry\'s token makes him a man again, with his head and\n'
               '\t     body on until a woman\'s look or the reset token. The states live in the project, so every map and every save keeps\n'
               f'\t     them, and the ask token gets as many answer tokens as the id of the look on, plus {HENRY_KEPT_ANSWER} with his head kept on and {WAS_WOMAN_ANSWER}\n'
               '\t     if he was a woman. The new_ nodes do the same on the character of KCD2 Life. -->\n'
               '\t<Skald>\n\t\t<Module Name="ml_ff_face">\n\t\t\t<Nodes>\n' + "".join(nodes)
               + '\t\t\t</Nodes>\n\t\t\t<Assets>\n'
               f'\t\t\t\t<SoulAsset Name="henry" SharedSoulGuids="{HENRY_SOUL}" />\n'
               f'\t\t\t\t<SoulAsset Name="new_life" SharedSoulGuids="{NEW_LIFE_SOUL}" />\n'
               '\t\t\t</Assets>\n\t\t\t<Text Text="ml_ff_face" />\n\t\t</Module>\n\t</Skald>\n</Database>\n')
    # Lua.
    lua = ["-- Generated by tools/generate_models.py from looks.toml. Edit that file, not this one. The looks in menu order, each",
           "-- with its id, shared with KCD2 Male Framework, the hair style and color it starts with, and its token on Henry.",
           f'FemaleCore.RESET_TOKEN = "{reset}"', f'FemaleCore.HENRY_TOKEN = "{own_face}"',
           f'FemaleCore.ASK_TOKEN = "{ask}"', f'FemaleCore.ANSWER_ITEM = "{answer}"',
           "-- Added to the id of the look in the answer: Henry's head and body kept on, and that he was a woman in this save.",
           f"FemaleCore.HENRY_KEPT_ANSWER = {HENRY_KEPT_ANSWER}", f"FemaleCore.WAS_WOMAN_ANSWER = {WAS_WOMAN_ANSWER}",
           "-- And that her state woman is on: a man with it on gets it turned off on the load.",
           f"FemaleCore.WOMAN_ON_ANSWER = {WOMAN_ON_ANSWER}",
           "-- Older saves kept the look in its amount: it is only taken away.", f'FemaleCore.OLD_STATE_ITEM = "{state}"',
           "-- KCD2 Life gives it to Henry when SwitchPlayer ends: its new character is in use.", f'FemaleCore.NEW_STARTED_TOKEN = "{started}"',
           "-- With it in Henry's inventory, her next haircut at a barber is free (ml_ff_barber.xml).", f'FemaleCore.FREE_HAIRCUT_TOKEN = "{free_haircut}"',
           "-- One of these on each load sets the price of her haircut: 5 groschen with Realish Economy, or the game's 50.",
           f'FemaleCore.PRICE_LOW_TOKEN = "{price_low}"', f'FemaleCore.PRICE_GAME_TOKEN = "{price_game}"',
           "-- A scene of the game gives it when it dresses the player or takes the outfit off: the look rebuilds (the pillory).",
           "-- KCD2 Male Framework has the same one.",
           f'FemaleCore.REBUILD_TOKEN = "{SCENE_REBUILD_TOKEN}"',
           "-- Skald gives one of these when it takes clothes off.", "FemaleCore.STRIPPED = {"]
    lua += [f'\t["{notices[p]}"] = "@{notice_text}",' for p, notice_text in CLOTHES_NOTICES.items()]
    lua += ["}", "-- new_token picks the look of the new character of KCD2 Life, and soul is the model that shows it in a selector.",
            "-- characters are the characters of the game with a name of their own who wear its face (LOOKS.md).",
            "FemaleCore.LOOKS = {"]
    for l in looks:
        ethnicity = f'"{l["ethnicity"]}"' if l["ethnicity"] else "nil"
        m = re.fullmatch(r"f_hair_(\d{3})_(\w+)", l["hair"])
        lua.append(f'\t{{ id = {l["id"]}, name = "{l["name"]}", ethnicity = {ethnicity}, age = "{l["age"]}", '
                   f'villager = {"true" if l["villager"] else "false"}, style = {int(m.group(1))}, color = {HAIR_COLORS.index(m.group(2)) + 1}, '
                   f'token = "{tokens[l["id"]]}", new_token = "{l["token"]}", soul = "{l["soul"]}", '
                   f'characters = {lua_list(c["name"] for c in l["characters"])} }},')
    lua += ["}", ""]
    write_file(folder / "data/Scripts/FemaleCore/looks_data.lua", "\n".join(lua))


# The barber of a man with a look of KCDMF: a talk, as the one of a woman in KCDFF, with the hair and the beards
# of barber.toml in place of styles and colors. The game's screen stays for Henry with his own face, with its list whole.
PLAYER_ANY_SOUL = "9a502475-ea84-448b-8922-7af61739b941"
COIN = "5ef63059-322e-4e1b-abe8-926e100c770e"


def mf_dialog(hairs, beards):
    """The talk: hair or beard, each named tries it on him at once, and only Accept keeps it (MaleCore.Barber)."""
    vo = 'VoiceoverFallbackLevel="2" VoiceoverFallbackLevelRoles="BARBER HENRY"'

    def options(kind, items, variable, call, decision):
        out = ""
        for i, item in enumerate(items, 1):
            out += (f'\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<Sequence EntryCondition="gvar(\'{variable}\') != {i}" EndType="GoTo" GoToDecision="{decision}" '
                    f'ExitScript="MaleCore.Barber.{call}({i})" Name="seq_mf_{kind}_{i}">\n'
                    f'\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<UiPrompt StringName="{item["text"]}" />\n'
                    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<Elements>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<Response Role="HENRY" />\n'
                    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</Elements>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</Sequence>\n')
        return out + (f'\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<Sequence EndType="GoTo" GoToDecision="dec_mf_man_hair" Name="seq_mf_{kind}_back">\n'
                      '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<UiPrompt StringName="ui_ml_mf_back" />\n'
                      '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<Elements>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<Response Role="HENRY" />\n'
                      '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</Elements>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</Sequence>\n')

    def menu(kind, prompt, decision, body):
        return (f'\t\t\t\t\t\t\t\t\t\t\t\t<Sequence EndType="Decision" Name="seq_mf_select_{kind}">\n'
                f'\t\t\t\t\t\t\t\t\t\t\t\t\t<UiPrompt StringName="{prompt}" />\n'
                '\t\t\t\t\t\t\t\t\t\t\t\t\t<Elements>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t<Response Role="HENRY" />\n\t\t\t\t\t\t\t\t\t\t\t\t\t</Elements>\n'
                f'\t\t\t\t\t\t\t\t\t\t\t\t\t<Decision Name="{decision}" Priority="Repair" {vo}>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t<Sequences>\n'
                + body + '\t\t\t\t\t\t\t\t\t\t\t\t\t\t</Sequences>\n\t\t\t\t\t\t\t\t\t\t\t\t\t</Decision>\n\t\t\t\t\t\t\t\t\t\t\t\t</Sequence>\n')

    hair_menu = menu("hair", "ui_ml_mf_hair_select_style", "dec_mf_hair",
                     options("hair", hairs, "ml_mf_hair", "Hair", "dec_mf_hair"))
    beard_menu = menu("beard", "ui_ml_mf_beard_select", "dec_mf_beard",
                      options("beard", beards, "ml_mf_beard", "Beard", "dec_mf_beard"))
    return f'''<?xml version="1.0" encoding="utf-8"?>
<Database xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" Name="brambora">
	<!-- Generated by tools/generate_models.py from barber.toml. The barber's talk for a man with a look of the framework: a
	     hair and a beard, among those every head of the catalog has. The screen of the game shows one list to every head,
	     and its beards, or those of other mods, may not exist for the head of the look. As the barber of a woman in KCD2
	     Female Framework: the camera of a normal talk, each one named tries it on him at once, and only Accept keeps it
	     (MaleCore.Barber, in Scripts/MaleCore/barber.lua). Lua keeps ml_mf_model, ml_mf_hair and ml_mf_beard up to date; 0
	     hides nothing. It takes the place of the game's haircut, with its own line, "Give me a haircut": while a look is
	     on, the copy of the game's barber dialog that the tools write hides that one. -->
	<Skald>
		<FaderDialog Name="ml_mf_barber_dialog">
			<Ports>
				<Port Name="accepted" Direction="Out" Type="trigger" />
			</Ports>
			<Text Text="ml_mf_barber_dialog" />
			<Dialogue TechnicalStatus="Enabled">
				<SelectedSouls>
					<SelectedSoul Role="HENRY" Voice="tomMcKay" Type="Wave" Language="ENG" />
					<SelectedSoul Role="BARBER" Voice="bobBordeaux" Type="Wave" Language="ENG" />
				</SelectedSouls>
				<Decision Name="dec_mf_root" Priority="Repair" {vo}>
					<Sequences>
						<Sequence EntryCondition="gvar('ml_mf_model') == 1" EndType="Decision" Type="PaymentBarber" Name="seq_mf_cut">
							<UiPrompt StringName="ui_barber_di_seq5_3vfx" />
							<Elements>
								<Response Role="HENRY" />
							</Elements>
							<Decision Name="dec_mf_money" Autoselect="true" {vo}>
								<Sequences>
									<Sequence EntryCondition="GetActorMoney()[0] &lt; Port('Payment_seq_mf_cut')" EndType="EndDialogue" Name="seq_mf_no_money">
										<Elements>
											<Response Role="BARBER">
												<Text StringName="ml_mf_barber_no_money" />
											</Response>
										</Elements>
									</Sequence>
									<Sequence EntryCondition="GetActorMoney()[0] &gt;= Port('Payment_seq_mf_cut')" EndType="Decision" ExitScript="MaleCore.Barber.Open()" Name="seq_mf_man_cut">
										<Elements>
											<Response Role="BARBER" />
										</Elements>
										<Decision Name="dec_mf_man_hair" Priority="Repair" {vo}>
											<Sequences>
{hair_menu}{beard_menu}												<Sequence EndType="EndDialogue" ExitScript="MaleCore.Barber.Accept()" Name="seq_mf_accept">
													<UiPrompt StringName="ui_ml_mf_hair_accept" />
													<Triggers>
														<Port Name="accepted" />
													</Triggers>
													<Elements>
														<Response Role="HENRY" />
													</Elements>
												</Sequence>
												<Sequence EndType="EndDialogue" ExitScript="MaleCore.Barber.Cancel()" Name="seq_mf_cancel">
													<UiPrompt StringName="ui_ml_mf_never_mind" />
													<Elements>
														<Response Role="HENRY" />
													</Elements>
												</Sequence>
											</Sequences>
										</Decision>
									</Sequence>
								</Sequences>
							</Decision>
						</Sequence>
					</Sequences>
				</Decision>
			</Dialogue>
		</FaderDialog>
	</Skald>
</Database>
'''


def mf_gameplay(free, low, game):
    """The price, free with the token of a free haircut, and 5 groschen with Realish Economy, and the payment: as
    ml_ff_barber.xml of KCDFF."""
    def descriptor(name, item, y):
        return (f'\t\t\t\t<Function Name="{name}" PositionY="{y}" PositionX="-900" MethodName="wh::entitymodule::CreateItemClassDescriptor" DeclaringType="wh::entitymodule">\n'
                f'\t\t\t\t\t<Constant Name="ItemClass" Value="{item}" />\n\t\t\t\t\t<Constant Name="Amount" Value="1" />\n\t\t\t\t</Function>\n')

    def trigger(name, owner, desc, y):
        return (f'\t\t\t\t<ItemDescriptorTrigger Name="{name}" PositionY="{y}" PositionX="-600">\n'
                f'\t\t\t\t\t<Edge From="{owner}.Inventory" To="Inventory" />\n\t\t\t\t\t<Edge From="{desc}.ItemDescriptor" To="ItemDescriptor" />\n'
                '\t\t\t\t\t<Edge From="always_on.State" To="IsActive" />\n\t\t\t\t</ItemDescriptorTrigger>\n')

    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<Database xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" Name="brambora">\n'
            '\t<!-- Generated by tools/generate_models.py. A man\'s haircut with a look of the framework, at the barbers of the game: any\n'
            '\t     NPC with the role BARBER. The talk (ml_mf_barber_dialog.xml) shows when Lua says the character in use wears a look\n'
            '\t     (ml_mf_model), Henry or the new character of KCD2 Life. 50 groschen is the price of the game, or 5 with Realish\n'
            '\t     Economy, and coins go in tenths. The free haircut token, in Henry\'s inventory, makes the next one free: KCD2 Life\n'
            '\t     gives it before its new character starts. It hangs from the project to reach every map. -->\n'
            '\t<Skald>\n\t\t<Gameplay Name="ml_mf_barber">\n\t\t\t<Definitions>\n'
            '\t\t\t\t<Definition File="ml_mf_barber/ml_mf_barber_dialog.xml" />\n\t\t\t</Definitions>\n\t\t\t<Nodes>\n'
            '\t\t\t\t<ObjectProperties Name="henry" PositionY="-600" PositionX="-1200" DeclaringType="wh::rpgmodule::I_Soul">\n'
            '\t\t\t\t\t<Asset Name="I_Soul" Alias="henry" />\n\t\t\t\t</ObjectProperties>\n'
            '\t\t\t\t<ObjectProperties Name="new_life" PositionY="-150" PositionX="-1200" DeclaringType="wh::rpgmodule::I_Soul">\n'
            '\t\t\t\t\t<Asset Name="I_Soul" Alias="new_life" />\n\t\t\t\t</ObjectProperties>\n'
            '\t\t\t\t<State Name="always_on" PositionY="-750" PositionX="-1200" TypeT="bool">\n'
            '\t\t\t\t\t<Constant Name="DefaultValue" Value="true" />\n\t\t\t\t</State>\n'
            + descriptor("free_descriptor", free, -600)
            + trigger("free_token", "henry", "free_descriptor", -600)
            + '\t\t\t\t<State Name="free_cut" PositionY="-450" PositionX="-600" TypeT="bool">\n'
            '\t\t\t\t\t<Constant Name="DefaultValue" Value="false" />\n'
            '\t\t\t\t\t<Edge From="free_token.OnAcquire" To="SetTrue" />\n\t\t\t\t\t<Edge From="free_or_paid.True" To="SetFalse" />\n'
            '\t\t\t\t</State>\n'
            + descriptor("low_descriptor", low, -300) + descriptor("game_descriptor", game, -200)
            + trigger("low_henry", "henry", "low_descriptor", -350) + trigger("low_life", "new_life", "low_descriptor", -300)
            + trigger("game_henry", "henry", "game_descriptor", -250) + trigger("game_life", "new_life", "game_descriptor", -200)
            + '\t\t\t\t<State Name="low_price" PositionY="-300" PositionX="-450" TypeT="bool">\n'
            '\t\t\t\t\t<Constant Name="DefaultValue" Value="false" />\n'
            '\t\t\t\t\t<Edge From="low_henry.OnAcquire" To="SetTrue" />\n\t\t\t\t\t<Edge From="low_life.OnAcquire" To="SetTrue" />\n'
            '\t\t\t\t\t<Edge From="game_henry.OnAcquire" To="SetFalse" />\n\t\t\t\t\t<Edge From="game_life.OnAcquire" To="SetFalse" />\n'
            '\t\t\t\t</State>\n'
            '\t\t\t\t<Switch Name="full_price" PositionY="-300" PositionX="-300" TypeT="bool" ValueTypes="float" SwitchValues="true">\n'
            '\t\t\t\t\t<Constant Name="DefaultValue1" Value="50" />\n\t\t\t\t\t<Constant Name="trueValue1" Value="5" />\n'
            '\t\t\t\t\t<Edge From="low_price.State" To="Switch" />\n\t\t\t\t</Switch>\n'
            '\t\t\t\t<Switch Name="coins_amount" PositionY="650" PositionX="0" TypeT="bool" ValueTypes="int" SwitchValues="true">\n'
            '\t\t\t\t\t<Constant Name="DefaultValue1" Value="500" />\n\t\t\t\t\t<Constant Name="trueValue1" Value="50" />\n'
            '\t\t\t\t\t<Edge From="low_price.State" To="Switch" />\n\t\t\t\t</Switch>\n'
            '\t\t\t\t<Switch Name="price" PositionY="-150" PositionX="-300" TypeT="bool" ValueTypes="float" SwitchValues="true">\n'
            '\t\t\t\t\t<Edge From="full_price.Value1" To="DefaultValue1" />\n\t\t\t\t\t<Constant Name="trueValue1" Value="0" />\n'
            '\t\t\t\t\t<Edge From="free_cut.State" To="Switch" />\n\t\t\t\t</Switch>\n'
            '\t\t\t\t<ml_mf_barber_dialog Name="dialog" PositionY="0" PositionX="0">\n'
            '\t\t\t\t\t<Edge From="price.Value1" To="Payment_seq_mf_cut" />\n\t\t\t\t</ml_mf_barber_dialog>\n'
            '\t\t\t\t<IfFunction Name="free_or_paid" PositionY="50" PositionX="600" TypeT="bool" MethodName="Control::Compare" DeclaringType="Control">\n'
            '\t\t\t\t\t<Constant Name="Op" Value="Equals" />\n\t\t\t\t\t<Constant Name="ValueB" Value="true" />\n'
            '\t\t\t\t\t<Edge From="free_cut.State" To="ValueA" />\n\t\t\t\t\t<Edge From="dialog.accepted" To="Exec" />\n'
            '\t\t\t\t</IfFunction>\n'
            '\t\t\t\t<ObjectProperties Name="customer" PositionY="200" PositionX="300" DeclaringType="wh::rpgmodule::I_Soul">\n'
            '\t\t\t\t\t<Asset Name="I_Soul" Alias="player_any" />\n\t\t\t\t</ObjectProperties>\n'
            '\t\t\t\t<ObjectProperties Name="barber" PositionY="350" PositionX="300" DeclaringType="wh::rpgmodule::I_Soul">\n'
            '\t\t\t\t\t<Edge From="dialog.BARBER" To="I_Soul" />\n\t\t\t\t</ObjectProperties>\n'
            '\t\t\t\t<Function Name="coins" PositionY="500" PositionX="300" MethodName="wh::entitymodule::CreateItemClassDescriptor" DeclaringType="wh::entitymodule">\n'
            f'\t\t\t\t\t<Constant Name="ItemClass" Value="{COIN}" />\n\t\t\t\t\t<Edge From="coins_amount.Value1" To="Amount" />\n'
            '\t\t\t\t</Function>\n'
            '\t\t\t\t<EventMemberFunction Name="pay" PositionY="200" PositionX="600" MethodName="MoveItems" DeclaringType="wh::entitymodule::Inventory">\n'
            '\t\t\t\t\t<Constant Name="AllowPartialMatch" Value="false" />\n\t\t\t\t\t<Constant Name="ShowUINotification" Value="true" />\n'
            '\t\t\t\t\t<Edge From="free_or_paid.False" To="Exec" />\n\t\t\t\t\t<Edge From="coins.ItemDescriptor" To="ItemDescriptor" />\n'
            '\t\t\t\t\t<Edge From="customer.Inventory" To="SourceInventory" />\n\t\t\t\t\t<Edge From="barber.Inventory" To="TargetInventory" />\n'
            '\t\t\t\t</EventMemberFunction>\n\t\t\t</Nodes>\n\t\t\t<Assets>\n'
            f'\t\t\t\t<SoulAsset Name="henry" SharedSoulGuids="{HENRY_SOUL}" />\n'
            f'\t\t\t\t<SoulAsset Name="player_any" SharedSoulGuids="{PLAYER_ANY_SOUL}" />\n'
            f'\t\t\t\t<SoulAsset Name="new_life" SharedSoulGuids="{NEW_LIFE_SOUL}" />\n'
            '\t\t\t</Assets>\n\t\t\t<Text Text="ml_mf_barber" />\n\t\t</Gameplay>\n\t</Skald>\n</Database>\n')


def write_kcdmf_barber(free, low, game):
    """The talk and the graph of the barber of KCDMF, and the hair and the beards for its Lua."""
    folder = GENDERS["man"]["folder"]
    barber = tomllib.loads((folder / "barber.toml").read_text("utf-8"))
    hairs, beards = barber["hair"], barber["beard"]
    quests = folder / "data/Quests/kcd_male_framework"
    (quests / "ml_mf_barber").mkdir(parents=True, exist_ok=True)
    write_file(quests / "ml_mf_barber/ml_mf_barber_dialog.xml", mf_dialog(hairs, beards))
    write_file(quests / "ml_mf_barber.xml", mf_gameplay(free, low, game))
    return hairs, beards


# The game's barber dialog, with its haircut only for a man: while Henry is a woman, the women's haircut of
# KCDFF goes in its place. A file of the mod with the same path replaces the game's one. It is copied from the game
# of whoever builds, like the meshes, and is not versioned. The two haircut options are the normal one and the one of
# the denied shop.
BARBER_DIALOG = "Quests/Final/Barbora/open_world/barber/barber/barber_dialog/barber_dialogue.xml"
BARBER_HAIRCUTS = (
    "!Port('shop_is_denied') AND Port('seller_in_shop')",
    "Port('shop_is_denied') AND !Port('bad_reputation') AND Port('seller_in_shop')",
)
# Not for a woman of KCDFF, nor for a man with a look of KCDMF, who have their own barber's talk. Both
# frameworks ship the same copy, so either one alone, or both, hides the haircut of the game as it must.
MEN_ONLY = " AND gvar('ml_ff_woman') != 1 AND gvar('ml_mf_model') != 1"
# The game's file as the copy was checked against (game 1.5.6). If an update of the game changes it, the old copy would
# hide the change, so the tool stops until someone reads the new file and updates this hash.
BARBER_DIALOG_SHA256 = "8d72bf2c16dd8d59021928437fc7d5e4a6e0f40138083973230fa4587ab01173"


def write_game_barber_dialog():
    with zipfile.ZipFile(GAME / "Data" / "Scripts.pak") as z:
        raw = z.read(BARBER_DIALOG)
    found = hashlib.sha256(raw).hexdigest()
    if found != BARBER_DIALOG_SHA256:
        raise SystemExit(f"{BARBER_DIALOG} changed in the game (sha256 {found}). Compare it with the copy of KCD2 Female "
                         "Framework, check its two haircut options, and then update BARBER_DIALOG_SHA256.")
    text = raw.decode("utf-8-sig")
    for condition in BARBER_HAIRCUTS:
        old = f'EntryCondition="{condition}"'
        if text.count(old) != 1:
            raise SystemExit(f"{BARBER_DIALOG}: {old} not found exactly once. Did the game change?")
        text = text.replace(old, f'EntryCondition="{condition}{MEN_ONLY}"')
    for gender in PRESENT:
        dest = GENDERS[gender]["folder"] / "data" / BARBER_DIALOG
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8-sig", newline="")


# The game's own scenes that put Henry's parts on the player soul: wet, wounded and bandaged in the prologue in
# Trosecko, and wet at the swimming contest of the Cumans. An override of a quest of the level wins over hers, which lives
# in the project, so while Henry was a woman she showed his wounded head, his body and his breeches there (kcd.log and
# screenshots of 2026-11-09). A copy of each scene, from the game of whoever builds, puts those parts on only while the
# player has no buff with the tag ml_ff_woman, which the graph keeps on her (woman_mark). Head, body and underwear: she
# keeps her own, and her shift. A look of KCD2 Male Framework had Henry's wounded head on his face the same way: its
# buff ml_mf_look keeps Henry's head and body off him, and his breeches stay, a man's clothes. Each framework
# works on its own, so both ship the same copies, and both have both tags. Every other override in the game is on another
# soul.
# Each file is checked against the game's, like the barber's talk.
# Each scene: its sha256, how many overrides of the player it has, and their kind.
STORY_SCENES = {
    "Quests/Final/Barbora/trosecko/prepadeni/prepadeni/mokry_jindrich_a_ptacek.xml":
        ("bfdcc506fd5a47e8a035a4e82fcbd4639b7bbd46a9b62cd3742eca0f24cff4f9", 2, "BodyPartOverride"),
    "Quests/Final/Barbora/trosecko/prepadeni/hibernovana_cast/honicka_ve_skalach/nastaveni_ptacka_a_jindricha.xml":
        ("91458e2efe585197d5897386b1201870a1155de3f40a930311887c7ee49e8e72", 3, "BodyPartOverride"),
    "Quests/Final/Barbora/trosecko/zachrana/henryho_morfovani_tel_a_obvazu/henry__pred_prvni_cs.xml":
        ("ef8fdf7853579bb949422231d73ec00fd1119c2346fc0386d5c154fc97adf087", 3, "BodyPartOverride"),
    "Quests/Final/Barbora/trosecko/zachrana/henryho_morfovani_tel_a_obvazu.xml":
        ("7825d1025a0ab4bb57ba11be52d89c78bfb87633dba48bbb65bcdc2700545eb0", 4, "BodyPartOverride"),
    "Quests/Final/Barbora/trosecko/kumaniNaTrosecku/hibernation/kumansky_tabor/party_s_kumany/soutez_v_plavani.xml":
        ("3c235c5960cb361448363311606c542f8d12b397fb71c69c43fde5175e0a33e8", 2, "BodyPartOverride"),
}
# The scenes that dress the player with a PlayerOutfitOverride, and keep doing it for her. In the pillory in Troskowitz,
# socky_Henry_cutscene_NoShirt puts Henry's hose and boots on the player. That outfit put his body under her head,
# but a load in the middle of the pillory showed her right, in the hose and boots, as the cutscene shows her: the outfit
# goes on the model without her overrides, and a rebuild puts them back. U369 took the outfit off her and she stayed in
# her own clothes; she wants the hose, as in the cutscene. So the copy keeps the outfit and gives the player the
# token ml_scene_rebuild when it goes on and when it comes off, and the tick of the framework of the character in use
# rebuilds the look. A face of KCD2 Male Framework is an override too. Each framework works on its own, so both
# ship the same copy, as they do the barber's talk, and the same row of the token: whichever loads last, the scene and
# the token are the same. KCD2 Female Framework takes the token while a woman is in use, KCD2 Male Framework the rest
# of the time, and either one always when the other is not there.
# The game has about 40 more PlayerOutfitOverrides (a disguise, tournaments, baths), each still to be checked when she
# meets it. Each scene: its sha256, how many outfits of the player it has, and the outputs where they go on and off.
OUTFIT_SCENES = {
    "Quests/Final/Barbora/trosecko/socky/hibernable/pranyr.xml":
        ("74f518c9550a0b8f39d8d0b8f7aad84051b3f539c26fc506c4fa6952fa38e72b", 1,
         ("cin_m0360t_socky__stocks_dialogue.after_play", "cin_m0370t_socky__stocks_release.afterplay")),
}
SCENE_REBUILD_TOKEN = guid("ml_scene_rebuild")
# The same row in the item table of both frameworks.
SCENE_REBUILD_ROW = (f'\t\t<MiscItem Type="5" SubType="0" IsDivisible="true" IconId="loot_sackOfNails" UIInfo="ui_in_ml_scene_rebuild" '
                     f'UIName="ui_nm_ml_scene_rebuild" Model="manmade/common_furniture/sacks/sack_items/sack_items.cgf" Weight="0" '
                     f'Price="0" FadeCoef="1" VisibilityCoef="1" Id="{SCENE_REBUILD_TOKEN}" Name="ml_scene_rebuild" />\n')
# buff__kcd_female_framework.xml and buff_ai_tag__kcd_female_framework.xml, written by hand, have the same values.
WOMAN_BUFF = guid("ml_ff_woman_buff")
WOMAN_BUFF_TAG = 204
# buff__kcd_male_framework.xml and buff_ai_tag__kcd_male_framework.xml, written by hand, have the same values, and
# MaleCore.LOOK_BUFF: a look of KCD2 Male Framework on Henry. Both frameworks have both tags.
MAN_LOOK_BUFF = guid("ml_mf_look_buff")
MAN_LOOK_BUFF_TAG = 205
# A woman is either of two things. The check reads the buff when the condition of the scene changes: that is enough
# while the game runs. After a load, the scene can read it before the buff is back, so the bandaged body came back at
# Bozhena's (kcd.log of 2026-11-09). So the scene also keeps a state that the buff sets when it arrives and clears
# when it goes, and KCD2 Female Framework gives the buff again after each load (female_core.lua, markWoman).
WOMAN_CHECK = (
    '<Function Name="ml_ff_woman_check" PositionY="{y}" PositionX="{x}" MethodName="wh::rpgmodule::BuffTagCheck" DeclaringType="wh::rpgmodule">\n'
    '\t\t\t\t\t<Asset Name="Souls" Alias="player" />\n'
    f'\t\t\t\t\t<Constant Name="BuffTag" Value="{WOMAN_BUFF_TAG}" />\n'
    '\t\t\t\t</Function>\n'
    '\t\t\t\t<State Name="ml_ff_always_on" PositionY="{y2}" PositionX="{x}" TypeT="bool">\n'
    '\t\t\t\t\t<Constant Name="DefaultValue" Value="true" />\n'
    '\t\t\t\t</State>\n'
    '\t\t\t\t<MakeArray Name="ml_ff_woman_tags" PositionY="{y3}" PositionX="{x}" TypeT="wh::rpgmodule::BuffDefinitionAITags">\n'
    f'\t\t\t\t\t<Constant Name="A" Value="{WOMAN_BUFF_TAG}" />\n'
    '\t\t\t\t</MakeArray>\n'
    '\t\t\t\t<BuffTagTrigger Name="ml_ff_woman_buff" PositionY="{y2}" PositionX="{x2}">\n'
    '\t\t\t\t\t<Asset Name="Souls" Alias="player" />\n'
    '\t\t\t\t\t<Edge From="ml_ff_always_on.State" To="IsActive" />\n'
    '\t\t\t\t\t<Edge From="ml_ff_woman_tags.Array" To="BuffTags" />\n'
    '\t\t\t\t</BuffTagTrigger>\n'
    '\t\t\t\t<State Name="ml_ff_woman_seen" PositionY="{y2}" PositionX="{x3}" TypeT="bool">\n'
    '\t\t\t\t\t<Constant Name="DefaultValue" Value="false" />\n'
    '\t\t\t\t\t<Edge From="ml_ff_woman_buff.OnAdded" To="SetTrue" />\n'
    '\t\t\t\t\t<Edge From="ml_ff_woman_buff.OnRemoved" To="SetFalse" />\n'
    '\t\t\t\t</State>\n'
    '\t\t\t\t<Function Name="ml_ff_is_woman" PositionY="{y}" PositionX="{x3}" MethodName="math::boolean::Or" DeclaringType="math::boolean">\n'
    '\t\t\t\t\t<Edge From="ml_ff_woman_check.HaveBuffTag" To="A" />\n'
    '\t\t\t\t\t<Edge From="ml_ff_woman_seen.State" To="B" />\n'
    '\t\t\t\t</Function>\n'
    '\t\t\t\t<Function Name="ml_ff_not_woman" PositionY="{y}" PositionX="{x4}" MethodName="math::boolean::Not" DeclaringType="math::boolean">\n'
    '\t\t\t\t\t<Edge From="ml_ff_is_woman.bool" To="Value" />\n'
    '\t\t\t\t</Function>\n\t\t\t\t'
    # The same for a look of KCD2 Male Framework, with its buff ml_mf_look, and whether either look is on.
    '<Function Name="ml_mf_look_check" PositionY="{y4}" PositionX="{x}" MethodName="wh::rpgmodule::BuffTagCheck" DeclaringType="wh::rpgmodule">\n'
    '\t\t\t\t\t<Asset Name="Souls" Alias="player" />\n'
    f'\t\t\t\t\t<Constant Name="BuffTag" Value="{MAN_LOOK_BUFF_TAG}" />\n'
    '\t\t\t\t</Function>\n'
    '\t\t\t\t<MakeArray Name="ml_mf_look_tags" PositionY="{y5}" PositionX="{x}" TypeT="wh::rpgmodule::BuffDefinitionAITags">\n'
    f'\t\t\t\t\t<Constant Name="A" Value="{MAN_LOOK_BUFF_TAG}" />\n'
    '\t\t\t\t</MakeArray>\n'
    '\t\t\t\t<BuffTagTrigger Name="ml_mf_look_buff" PositionY="{y5}" PositionX="{x2}">\n'
    '\t\t\t\t\t<Asset Name="Souls" Alias="player" />\n'
    '\t\t\t\t\t<Edge From="ml_ff_always_on.State" To="IsActive" />\n'
    '\t\t\t\t\t<Edge From="ml_mf_look_tags.Array" To="BuffTags" />\n'
    '\t\t\t\t</BuffTagTrigger>\n'
    '\t\t\t\t<State Name="ml_mf_look_seen" PositionY="{y5}" PositionX="{x3}" TypeT="bool">\n'
    '\t\t\t\t\t<Constant Name="DefaultValue" Value="false" />\n'
    '\t\t\t\t\t<Edge From="ml_mf_look_buff.OnAdded" To="SetTrue" />\n'
    '\t\t\t\t\t<Edge From="ml_mf_look_buff.OnRemoved" To="SetFalse" />\n'
    '\t\t\t\t</State>\n'
    '\t\t\t\t<Function Name="ml_mf_is_look" PositionY="{y4}" PositionX="{x3}" MethodName="math::boolean::Or" DeclaringType="math::boolean">\n'
    '\t\t\t\t\t<Edge From="ml_mf_look_check.HaveBuffTag" To="A" />\n'
    '\t\t\t\t\t<Edge From="ml_mf_look_seen.State" To="B" />\n'
    '\t\t\t\t</Function>\n'
    '\t\t\t\t<Function Name="ml_any_look" PositionY="{y4}" PositionX="{x4}" MethodName="math::boolean::Or" DeclaringType="math::boolean">\n'
    '\t\t\t\t\t<Edge From="ml_ff_is_woman.bool" To="A" />\n'
    '\t\t\t\t\t<Edge From="ml_mf_is_look.bool" To="B" />\n'
    '\t\t\t\t</Function>\n'
    '\t\t\t\t<Function Name="ml_no_look" PositionY="{y4}" PositionX="{x5}" MethodName="math::boolean::Not" DeclaringType="math::boolean">\n'
    '\t\t\t\t\t<Edge From="ml_any_look.bool" To="Value" />\n'
    '\t\t\t\t</Function>\n\t\t\t\t')


def gate_player_overrides(text, scene, kind):
    """Each override of the given kind on the player soul goes on only with its own condition AND no look: Henry's
    head and body neither on a woman of KCD2 Female Framework nor on a look of KCD2 Male Framework, his breeches not on
    a woman, and on a man they stay. Its condition, with any vertex of the editor, moves into an And in front of
    it."""
    gated = []

    def gate(found):
        block = found.group(0)
        if 'Alias="player"' not in block:
            return block
        node = re.search(r'Name="([^"]+)"', block).group(1)
        y, x = (int(re.search(rf'{a}="(-?\d+)"', block).group(1)) for a in ("PositionY", "PositionX"))
        edges = re.findall(r'<Edge From="[^"]+" To="IsActive"(?: />|>.*?</Edge>)', block, flags=re.S)
        if len(edges) != 1:
            raise SystemExit(f"{scene}: {node} has {len(edges)} conditions, not one. Did the game change?")
        name = f"ml_ff_gate_{node}"
        condition = edges[0].replace('To="IsActive"', 'To="A"')
        part = re.search(r'<Constant Name="BodyPart" Value="([^"]+)"', block)
        if not part or part.group(1) not in ("Head", "Body", "Underwear"):
            raise SystemExit(f"{scene}: {node} overrides {part and part.group(1)}, not the head, the body or the underwear. Did the game change?")
        unless = "ml_ff_not_woman" if part.group(1) == "Underwear" else "ml_no_look"
        gated.append((y, x))
        return (f'<Function Name="{name}" PositionY="{y}" PositionX="{x - 250}" MethodName="math::boolean::And" DeclaringType="math::boolean">\n'
                f'\t\t\t\t\t{condition}\n'
                f'\t\t\t\t\t<Edge From="{unless}.bool" To="B" />\n'
                '\t\t\t\t</Function>\n\t\t\t\t'
                + block.replace(edges[0], f'<Edge From="{name}.bool" To="IsActive" />'))

    text = re.sub(rf'<{kind} .*?</{kind}>', gate, text, flags=re.S)
    y = min(p[0] for p in gated) - 200
    x = min(p[1] for p in gated) - 800
    first = '<Function Name="ml_ff_gate_'
    text = text.replace(first, WOMAN_CHECK.format(y=y, y2=y - 100, y3=y - 200, y4=y - 300, y5=y - 400,
                                                  x=x, x2=x + 250, x3=x + 500, x4=x + 750, x5=x + 1000) + first, 1)
    return text, len(gated)


def write_story_scenes():
    with zipfile.ZipFile(GAME / "Data" / "Scripts.pak") as z:
        names = {n.replace("\\", "/").lower(): n for n in z.namelist()}
        for scene, (sha, expected, kind) in STORY_SCENES.items():
            raw = z.read(names[scene.lower()])
            found = hashlib.sha256(raw).hexdigest()
            if found != sha:
                raise SystemExit(f"{scene} changed in the game (sha256 {found}). Compare it with the copy of KCD2 Female "
                                 "Framework, check its overrides of the player, and then update STORY_SCENES.")
            text, count = gate_player_overrides(raw.decode("utf-8-sig"), scene, kind)
            if count != expected:
                raise SystemExit(f"{scene}: {count} overrides of the player, not {expected}. Did the game change?")
            for gender in PRESENT:
                dest = GENDERS[gender]["folder"] / "data" / scene
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(text, encoding="utf-8-sig", newline="")
        for scene, (sha, expected, outputs) in OUTFIT_SCENES.items():
            raw = z.read(names[scene.lower()])
            found = hashlib.sha256(raw).hexdigest()
            if found != sha:
                raise SystemExit(f"{scene} changed in the game (sha256 {found}). Compare it with the copy of KCD2 Female "
                                 "Framework, check its outfits of the player, and then update OUTFIT_SCENES.")
            text = rebuild_on_outfits(raw.decode("utf-8-sig"), scene, expected, outputs)
            for gender in PRESENT:
                dest = GENDERS[gender]["folder"] / "data" / scene
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(text, encoding="utf-8-sig", newline="")


def rebuild_on_outfits(text, scene, expected, outputs):
    """The scene as the game's, plus a CreatePlayerReward of ml_scene_rebuild on each output where an outfit of the
    player goes on or off. The framework of the character in use takes the token and rebuilds the look."""
    outfits = re.findall(r'<PlayerOutfitOverride Name="([^"]+)" PositionY="(-?\d+)" PositionX="(-?\d+)">', text)
    if len(outfits) != expected or len(outfits) != text.count("<PlayerOutfitOverride "):
        raise SystemExit(f"{scene}: {len(outfits)} outfits of the player, not {expected}. Did the game change?")
    name, y, x = outfits[0]
    nodes = ""
    for k, output in enumerate(outputs):
        if f'<Edge From="{output}" ' not in text:
            raise SystemExit(f"{scene}: no edge from {output}. Did the game change?")
        nodes += (f'<EventFunction Name="ml_scene_rebuild_{k}" PositionY="{int(y) - 200 - 100 * k}" PositionX="{x}" MethodName="wh::entitymodule::CreatePlayerReward" DeclaringType="wh::entitymodule">\n'
                  f'\t\t\t\t\t<Constant Name="ItemClass" Value="{SCENE_REBUILD_TOKEN}" />\n'
                  '\t\t\t\t\t<Constant Name="Amount" Value="1" />\n'
                  '\t\t\t\t\t<Constant Name="ShowUINotification" Value="false" />\n'
                  f'\t\t\t\t\t<Edge From="{output}" To="Exec" />\n'
                  '\t\t\t\t</EventFunction>\n\t\t\t\t')
    first = f'<PlayerOutfitOverride Name="{name}" '
    return text.replace(first, nodes + first, 1)


PEOPLE = {"czech": "Czech", "hungarian": "Hungarian", "romani": "Romani", "": "named"}


# The hairs of women of the story that KCDFF fits too, out of the barber: generate_women.py mounts them, and
# FemaleCore.NAMED_HAIRS takes them by name.
NAMED_HAIRS = ["katherine", "rose", "mother", "miriam"]


def woman_hair_words(hair):
    """The words of ml_ff_hair, and of ml_ff_look after the look, for a hair of the game that the framework has, or
    nothing."""
    m = re.fullmatch(r"f_hair_(\d{3})_(\w+)", hair or "")
    style = int(m.group(1)) if m else 0
    if style in HAIR_STYLES and m.group(2) in HAIR_COLORS[:HAIR_STYLES[style]]:
        return f"{style} {m.group(2)}"
    named = re.fullmatch(r"f_hair_(\w+)", hair or "")
    if named and named.group(1) in NAMED_HAIRS:
        return named.group(1)
    return ""


def write_look_maps(catalogs):
    """LOOKS.md in each framework: who wears each face in the game, by look and by character."""
    for gender in PRESENT:
        prefix = GENDERS[gender]["prefix"]
        looks = sorted(catalogs[gender], key=lambda l: l["id"])
        title = "KCD2 Male Framework" if gender == "man" else "KCD2 Female Framework"
        lines = [f"# {title}: the faces and who wears them", "",
                 "<!-- Written by tools/generate_models.py from looks.toml and the game's files: edit those, not this file. -->", "",
                 "The game gives each of its faces to several of its characters. Here are, for every look of the framework, the "
                 "characters of the game with a name of their own who wear its face, as the game's appearance rules give it. "
                 f"`{prefix}looks` writes the same names in the console, next to each look.", "",
                 f"`{prefix}look <name>` puts on the face with the look's own hair{' and beard' if gender == 'man' else ''}, "
                 "which may not be that character's. The second table has the hair "
                 f"{'and the beard ' if gender == 'man' else ''}each character wears in the game, and the command that puts "
                 "on the face with them.", "",
                 "The game's generic people, a peasant or a guard with no name of their own, wear these faces too and are not "
                 "listed. A character may have more than one face: a quest can give another.", "",
                 "## By look", "", "| Id | Look | Head | People | Age | Characters with this face |", "|---:|---|---|---|---|---|"]
        for l in looks:
            names = ", ".join(c["name"] for c in l["characters"]) or "—"
            lines.append(f"| {l['id']} | `{l['name']}` | `{l['head']}` | {PEOPLE[l['ethnicity']]} | {l['age']} | {names} |")
        rows = sorted(((c, l) for l in looks for c in l["characters"]), key=lambda p: (p[0]["name"].casefold(), p[1]["id"]))
        code = lambda text: f"`{text}`" if text else "—"  # noqa: E731
        lines += ["", "## By character", ""]
        if gender == "man":
            command = lambda c, l: " ".join(filter(None, [f"ml_mf_look {l['name']}", c["hair"], c["beard"]]))  # noqa: E731
            lines += ["| Character | Look | Their hair | Their beard | In the console |", "|---|---|---|---|---|"]
            lines += [f"| {c['name']} | `{l['name']}` | {code(c['hair'])} | {code(c['beard'])} | `{command(c, l)}` |" for c, l in rows]
        else:
            command = lambda c, l: " ".join(filter(None, [f"ml_ff_look {l['name']}", woman_hair_words(c["hair"])]))  # noqa: E731
            lines += ["| Character | Look | Her hair | In the console |", "|---|---|---|---|"]
            lines += [f"| {c['name']} | `{l['name']}` | {code(c['hair'])} | `{command(c, l)}` |" for c, l in rows]
        write_file(GENDERS[gender]["folder"] / "LOOKS.md", "\n".join(lines) + "\n")
        print(f"{gender}: LOOKS.md, {len(rows)} characters")


def main():
    catalogs = extend_catalog()
    characters = look_characters(head_uses(), character_names())
    for catalog in catalogs.values():
        for look in catalog:
            look["characters"] = characters.get(look["head"], [])
    write_look_maps(catalogs)
    write_frameworks(catalogs)
    if "man" in PRESENT:
        write_kcdmf_standalone(sorted(catalogs["man"], key=lambda l: l["id"]))
    if "woman" in PRESENT:
        write_kcdff_standalone(sorted(catalogs["woman"], key=lambda l: l["id"]))
    write_game_barber_dialog()
    write_story_scenes()
    counts =collections.Counter((g, l["age"], l["ethnicity"] or "named") for g, c in catalogs.items() for l in c)
    for key in sorted(counts):
        print(key, counts[key])


main()

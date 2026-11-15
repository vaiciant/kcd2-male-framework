# KCD2 Male Framework: faces from your mod

A face is a look: a head, a body, a hair and a beard. Your mod can add faces of its own, next to the framework's, without changing the framework's files. Players use them like any other look: `ml_mf_look <name>`, and your mod can start the game with one (`RegisterStartCharacter`, in [MODDING.md](MODDING.md)).

This is not like clothes. Clothes for men fit every face as they are ([MAKING_CLOTHES.md](MAKING_CLOTHES.md)). A face changes Henry's head and body, and the save has to keep which face is on. So a face pack needs a few pieces of its own, and a tool writes them all from one file.

## What you write

A `faces.toml` at the root of your mod. [`examples/sample_men_faces/faces.toml`](examples/sample_men_faces/faces.toml) is a template with every field explained:

```toml
[pack]
id = "my_faces"                  # the id of your mod
name = "My Faces"

[[face]]
name = "my_hero"                 # the name players type: ml_mf_look my_hero
head = "m_head_008"              # a head of the framework
body = "m_body_tan_03"           # a body of the framework's looks
hair = "m_hair_009_dark_brown"   # a man's hair of the game
beard = "m_beard_04"             # a beard that head has
```

- **Heads:** those of the framework, which [LOOKS.md](LOOKS.md) lists, or a head of your own (see "A head of your own" below).
- **Bodies:** those of the framework's looks, `m_body_pale_01`, `m_body_tan_03` and the rest. The tool lists them if one is wrong.
- **Hair:** any man's hair of the game, as `ml_mf_look` takes it.
- **Beard:** one that the head has a mesh for, or `m_beard_00`, no beard. If the beard is wrong, the tool lists the ones the head has.
- **Up to ten faces** in a pack.

## Running the tool

You need the framework's repository, Python 3.11 or later, and the game's tables, extracted once with `tools/extract_game.py`. From the root of the repository:

```bash
python -I -X utf8 mod/kcd_male_framework/tools/make_face_pack.py path/to/your_mod
```

It writes into your mod:

| File | What |
|---|---|
| `data/Libs/Tables/item/item__<id>.xml` | One token per face |
| `data/Quests/<id>.xml` and `data/Quests/<id>/<id>_faces.xml` | Your Skald project: each face turns on with its token and off with the framework's reset, puts its head and body on Henry, and tells the framework its id when asked |
| `data/Scripts/MaleCore/Looks/<id>.lua` | Registers your faces with `MaleCore.RegisterLooks`, with the beards each head has |
| `mod.manifest` | Only if your mod has none |

Run it again after every change of `faces.toml`. The framework does the rest: the barber, the black screen and the save work with your faces as with its own.

## A head of your own

A face can bring its own head instead of one of the framework's. Give its mesh and its material in place of `head`:

```toml
[[face]]
name = "my_hero"
head_mesh = "source/my_head/my_head.skin"   # your head, in your mod
material = "source/my_head/my_head.mtl"     # its material
body = "m_body_tan_03"
hair = "m_hair_009_dark_brown"
beard = "m_beard_04"
```

The head is a man's head as the game's are: on the game's male skeleton, with the UVs of the game's men's heads. The easiest start is a head of the game, changed in your 3D tool. Next to `my_head.skin` go:

| File | What |
|---|---|
| `my_head_lod1.skin`, `my_head_lod2.skin` | Its LODs, the head from farther away |
| `my_head_poses.xml` | Its face poses. Without them, his face keeps still when he talks |
| `beards/m_beard_04.skin` and the rest | Its beards, each with its LODs (`m_beard_04_lod1.skin`...), made for that head |

Every head needs the beards of the framework's barber and the two the framework puts on to rebuild the face: `m_beard_04`, `m_beard_13`, `m_beard_16`, `m_beard_17` and `m_beard_18`. A beard without its mesh on the head closes the game, so the tool does not write a head without them. Any other beard of yours goes in too, and players can choose it with `ml_mf_look`.

The tool writes the head into `data/Objects/characters/humans/male/head/<id>_<face>/`, under the name `<id>_<face>`, and its node into `data/Libs/Tables/Character/CharacterComponent__<id>.xml`. Your source files stay where they are: keep them out of `data/` if you do not want them packed with your mod.

- **First-person view:** the tool hides the head and its beards there, as the framework hides the game's heads. It finds the part to hide by the UVs of Henry's head. If some vertices have no UV of his, the tool warns that they may show in first-person view.
- **Textures:** those that the material names next to it, as `File="./my_head_diff.tif"`, go with the head, with their mipmaps (`.dds`, `.dds.1`...). Those it names by their full path in your mod stay where they are.

[`examples/sample_men_own_head`](examples/sample_men_own_head) is a face with a head of its own. Its head is a stand-in: its `stand_in.py` copies a head of the game into `source/`, where yours would go, so you can try the tool before you have one.

## The ids

The save keeps a face by a number, shared by both frameworks. A pack takes a block of ten, from 1000 to 1299: block 0 is 1000 to 1009, block 1 is 1010 to 1019, up to block 29. The tool picks the block from the id of your mod, and says which. To choose it, set `block` in `[pack]`.

If two packs land on the same block, the framework keeps the first one it reads and leaves out the faces of the other. The log says it: `look <name> of <pack> left out`. Then set another `block` in one of them. Once players have saves with your faces, keep your block and the order of your faces: a save with a face whose id changed shows another face, or none.

## Trying it

1. Install your mod with the framework, and enable both.
2. In the log, `[ML_MF] looks of <id>: <count>` says how many of your faces went in.
3. In the console: `ml_mf_looks` lists them at the end, and `ml_mf_look <name>` puts one on.
4. Save, load, and check that he still has your face.
5. With a head of your own: look down in first-person view, and try each beard of the barber on it.

The framework's own samples are [`examples/sample_men_faces`](examples/sample_men_faces), with two faces, `sample_bearded` and `sample_shaven`, and [`examples/sample_men_own_head`](examples/sample_men_own_head), with `sample_own_man`.

## With a character of your mod

To start every game with one of your faces, register it as the start character, by its name. [`examples/template_mod`](examples/template_mod) does it, ready to copy:

```lua
MaleCore.RegisterStartCharacter({ name = "My Hero", look = "my_hero" })
```

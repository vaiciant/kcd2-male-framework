# KCD2 Male Framework: clothes from other mods

Every look of the framework is Henry with another man's head. His soul, his skeleton and his body stay a man's, as the men of the game. So clothes and armour for men, from the game or from your mod, fit every face as they fit the men of the game. There is nothing to register and no tool to run.

## Making clothes for men

Make them as for any man of the game:

- **The pieces:** a `Clothing` in the Male branch, in `Libs/Tables/Character/CharacterComponent__<yourmod>.xml`, under one of the game's groups (Torso, Legs, Head…), with `FilePath="humans/male/clothing/"`.
- **The meshes:** skinned to the man's skeleton, under `Objects/characters/humans/male/clothing/`.
- **The items:** in `Libs/Tables/item/item__<yourmod>.xml`.

**Declare only your own nodes.** To place a piece under a node of the game, your table has to name that node. A node declared again takes the attributes you give it, for every NPC too. A missing `ArmorType`, `HidingGroups` or `Morphs` breaks the men's clothes of the whole game. Copy each node of the game above yours with all its attributes, as the game has it.

## Hats, helmets and hair

- **One mesh fits every head.** The game's hats, helmets, coifs, hoods and men's hair have no morph for the size of a head. A hat or a hair of your mod fits every face, as the game's do.
- **Henry's own coif** is the exception: it has `#morph_henry`, which only his head turns on.
- **A hair shaped to one head**, like a painted scalp, shows as a cap on the others. The game's `m_hair_barber_16`, painted for Henry's head, does that on the other faces.
- **The barber.** With a look on, the framework's barber offers its own list of hairs and beards, those every face has (`barber.toml`). With Henry's own face, the game's barber shows yours too.

## Beards

A beard is one mesh per head: each head of the game has its own. A beard of your mod needs a mesh for each head that should wear it. A face wears it only if its head has it: `ml_mf_look <look> <hair> <beard>` checks it, and puts the look's own beard on if not.

## Trying them

1. Get your pieces with `wh_cheat_addItem <name of the item>`, and put them on.
2. `ml_mf_look man_czech_2` gives Henry a face, `ml_mf_random` another, and `ml_mf_looks` lists them all.
3. Try a young face and an old one: 13 looks wear the game's old body, as the old men of the game.
4. `ml_mf_henry` gives Henry his own face back.

## With KCD2 Female Framework

A man's piece of your mod goes on her too, since her soul is Henry's. But it is a man's mesh, and does not fit her body. To make it fit her, refit it to her and register it with `back = true`, so a man gets your piece back: KCD2 Female Framework's [MAKING_CLOTHES.md](https://github.com/vaiciant/kcd2-female-framework/blob/main/mod/kcd_female_framework/MAKING_CLOTHES.md) explains it, in "By hand".

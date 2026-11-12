# KCD2 Male Framework (`kcd_male_framework`)

**Works on its own or with [KCD2 Female Framework](https://github.com/vaiciant/kcd2-female-framework). Required by [KCD2 Life](https://github.com/vaiciant/kcd2-life).**

A small library for *Kingdom Come: Deliverance II* (PC, game version 1.5) that gives Henry another man's face, and changes nothing else. One command gives him his own face back. It is the men's side of [KCD2 Female Framework](https://github.com/vaiciant/kcd2-female-framework), and much simpler: a man's face already fits the player's skeleton, so there is no body or clothing to adapt. Any mod may use it, with a credit as the only condition.

## How it works

- **The look.** Head and body are `BodyPartOverride` nodes in the framework's Skald project, on Henry's soul, and so is Henry's own underwear, `m_underwear01_m01`: after a woman of KCD2 Female Framework, her shift stayed on the soul when her look went off, as her head once did. Lua picks a look with a token in Henry's inventory. The native `Barber` object puts on the look's hair and beard, and two real beard changes force the model to rebuild and show the overrides.
- **Saves.** The states live in the project, so every map and every save keeps the look. After a load, Lua asks Skald which look is on: Skald answers with as many tokens as its id, and Lua rebuilds the model.
- **Back to Henry.** `Barber:Commit` keeps in the soul the head that is shown. So Henry's own head and body go on as one more look, the commit happens with them in view, and then every look goes off. After a woman of KCD2 Female Framework, that framework keeps Henry's head on instead: a look of this one takes its place, and `ml_mf_henry` puts it back.
- **Henry's doubles in the cutscenes.** In a cutscene of the engine, Henry is an `AnimChar` of the cutscene's layer, and the soul in its `Properties.Body.guidBodyPresetId` gives its look. Most use the player's soul, so they show the face of his look, with the hair and the beard chosen at a barber. 27 use a soul of their own that the game gives Henry's head: wet at the lake, wounded when he falls, his arm bandaged, dreaming, whipped, naked in the romances. While a look is on, the framework gives those the player's soul too: it wraps `AnimChar.SetFromProperties`, which the game looks up when a layer makes its doubles, and while a cutscene plays it checks once a second the doubles that are there already. Out of cutscenes it searches nothing. A face needs no new mesh for it. With his own face, Henry sees them as always. KCD2 Female Framework does the same for a woman, and the two agree.
- **The game's scenes.** Five scenes of the game put Henry's own parts on the player with overrides of their own: wet, wounded and bandaged in the prologue in Trosecko, and wet at the Cumans' swimming contest. An override of a quest wins over the face, so a look showed Henry's wounded head there. While a look is on, the framework keeps a buff with no effect and no icon on Henry, `ml_mf_look`, and ships the game's files of those five scenes, the same as KCD2 Female Framework's: Henry's head and body go on only with no look of either framework, and his breeches only with no woman. The face and the body of the look stay, with no wounds or bandages, and the breeches go on as the game's. Henry with his own face sees the scenes as they were.
- **The pillory.** In Troskowitz the pillory dresses the player in Henry's hose and boots with an outfit of its own, `PlayerOutfitOverride`, which goes on the model without the face's overrides. The framework ships a copy of that scene, the same as KCD2 Female Framework's, that gives the player a token, `ml_scene_rebuild`, when the outfit goes on and when it comes off, and the face rebuilds. The tools copy the file from your game, so it is not in the repository.
- **First-person heads.** The game's heads and beards are copied with the `FirstPersonView` bit of their vertex colors set, so the face and the beard hide in first person.
- **The barber.** The game's barber screen shows one list, `barber_option.xml`, to every head, and some of its beards, or those of other mods, have no mesh for the head of a look: one missing has crashed the game. So, while a look is on, the barber's haircut is the framework's own talk, `ml_mf_barber`, with the game's line *Give me a haircut*: a hair and a beard among those every face has (`barber.toml`). Each choice calls `TryHair` or `TryBeard` on a `Barber` session, *I'll take this one* commits it, and leaving the talk reverts it. The game's haircut is hidden for him: the framework ships the game's `barber_dialogue.xml` with `gvar('ml_ff_woman') != 1 AND gvar('ml_mf_model') != 1` added to its two haircut options, the same copy as KCD2 Female Framework. With his own face, Henry has the game's screen and its whole list, also what other mods add to it.

## Features

| Feature | What it does |
|---|---|
| Every face of the game | All 73 generic men's faces, young and old, and one named man of the story whose face fits |
| Head and body | Each face comes with its body, so the arms and the skin match |
| First-person heads | Each face is rebuilt so it hides in first person, like Henry's |
| His haircut | With a look, at any barber of the game, the hair and the beard are chosen in the talk and tried on at once, among those every face can wear, for the game's price: 50 groschen, or 5 with Realish Economy |
| A new character of another mod | The same looks on the playable character of KCD2 Life |

## Console commands

| Command | What it does |
|---|---|
| `ml_mf_looks` | Lists every face: its name, its people, its age, its id and the characters of the game who wear it. [LOOKS.md](mod/kcd_male_framework/LOOKS.md) has the same list, and who wears what |
| `ml_mf_look <name>` | Gives Henry that look, head and body, like `ml_mf_look man_czech_2` |
| `ml_mf_random` | Gives Henry a look at random among all, with its hair and beard |
| `ml_mf_henry` | Gives Henry his own face back |
| `ml_mf_refresh` | Rebuilds the model, for when the face does not show |
| `ml_mf_start [look]` | The next game that starts or loads begins with the face of that look: type it in the main menu before New Game |
| `ml_mf_uninstall` | Gives Henry his face back before removing the mod. Then save, and remove it |

While the model changes, the screen goes black for a few seconds. A last `true` leaves it as it is. Typed with the inventory, the map or a menu open, a command waits until you close it. [COMMANDS.md](mod/kcd_male_framework/COMMANDS.md) has every command, with its Lua call.

## For modders

One call gives Henry another man's face: `MaleCore.SetLook(name)` from your mod, and `MaleCore.Henry()` brings his own back. [MODDING.md](mod/kcd_male_framework/MODDING.md) shows how, in a few lines.

## Compatibility and known limits

- **The barber's talk.** The framework replaces the game's `barber_dialogue.xml`, with its haircut hidden while a look is on, or a woman of KCD2 Female Framework, which ships the same copy. A mod that replaces the same file clashes with it, and the one that loads last wins.
- **The game's scenes.** The six scene files, the five above and the pillory, replace the game's, the same copies as KCD2 Female Framework's: a mod that replaces the same files clashes with them.
- **Wounds and bandages.** With a look, the body of the scene is the look's, so the wet skin, the arrow wound and the bandaged shoulder of the prologue do not show.
- **The doubles' clothes.** A double with the player's soul wears what he wears, where the cutscene does not dress it: at the lake, when he falls and when he wakes up wounded. Its wet hair, its wounds and its bandages are Henry's alone, so they do not show.
- **Videos.** A few cutscenes are videos, with Henry inside, like the dream after the fall in the prologue: they show Henry.
- **Head meshes.** The heads and their beards replace the game's at their own paths. A mod that replaces the same meshes wins or loses by load order.
- **With a woman.** After `ml_ff_female` of KCD2 Female Framework, `ml_mf_look` and `ml_mf_random` turn her back into Henry with that framework and put the face on, under one black screen, with KCD2 Female Framework 0.4.0 or later. The other commands do nothing while she is a woman, and none do with the character of a mod that plays its own.
- **Game updates.** The meshes must be rebuilt if their sources change.

## Installing

Subscribe on the Steam Workshop, or download it from Nexus Mods and put its folder in the game's `Mods` folder. No launch options and no tools: the meshes come ready in the mod.

## Building from source

The meshes derive from the game's files, so they are not in this repository. You build them from your own copy of the game, with Python 3.11 or later. From the root of the repository:

```bash
python -I tools/extract_game.py
python -I -X utf8 tools/generate_models.py
python -I -X utf8 mod/kcd_male_framework/tools/generate_heads.py mod/kcd_male_framework
python -I tools/install_mod.py mod/kcd_male_framework
```

| Tool | What it writes |
|---|---|
| `tools/extract_game.py` | The game tables that the tools read, from your game into `game_files/`. Once, and again after a game update |
| `tools/generate_models.py` | The catalog of looks in `looks.toml` and `LOOKS.md`, the Skald graphs, the tokens and the Lua data of both frameworks, the barber's talk from `barber.toml`, and the game's barber dialog with its haircut hidden while a look is on |
| `tools/generate_heads.py` | The heads and their beards, with the first-person mask. It uses `fp_mask.py` |
| `tools/install_mod.py` | Packs the mod and copies it to the game. The game must be closed |

Set `KCD2_GAME` to the game's folder if it is not in the default Steam library.

## Roadmap to 1.0.0

Plans, not promises.

- **Clothes from other mods:** tested with clothing and armor mods, and a clear pipeline to make their pieces fit every face and body.

## License

Free for any use, also in closed work. The only condition: credit KCD2 Male Framework where people can see it, like a line in your mod's description or credits. Asking for donations or Patreon support is fine, as long as nothing in your mod is only for those who pay: Warhorse's rules do not allow selling KCD2 mods. You do not need to include the license or publish your source. It does not cover the game's files or anything derived from them, such as the meshes. See [LICENSE](LICENSE).

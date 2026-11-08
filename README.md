# KCD2 Male Framework (`kcd_male_framework`)

**Works on its own. Required by [KCD2 Life](https://github.com/vaiciant/kcd2-life).**

A small library for *Kingdom Come: Deliverance II* (PC, game version 1.5) that gives Henry another man's face, and changes nothing else. One command gives him his own face back. It is the men's side of [KCD2 Female Framework](https://github.com/vaiciant/kcd2-female-framework), and much simpler: a man's face already fits the player's skeleton, so there is no body or clothing to adapt. Any mod may use it, with a credit as the only condition.

## How it works

- **The look.** Head and body are `BodyPartOverride` nodes in the framework's Skald project, on Henry's soul. Lua picks a look with a token in Henry's inventory. The native `Barber` object puts on the look's hair and beard, and two real beard changes force the model to rebuild and show the overrides.
- **Saves.** The states live in the project, so every map and every save keeps the look. After a load, Lua asks Skald which look is on: Skald answers with as many tokens as its id, and Lua rebuilds the model.
- **Back to Henry.** `Barber:Commit` keeps in the soul the head that is shown. So Henry's own head and body go on as one more look, the commit happens with them in view, and then every look goes off. After a woman of KCD2 Female Framework, that framework keeps Henry's head on instead: a look of this one takes its place, and `ml_mf_henry` puts it back.
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
| `ml_mf_looks` | Lists every face: its name, its people, its age and its id |
| `ml_mf_look <name>` | Gives Henry that look, head and body, like `ml_mf_look man_czech_2` |
| `ml_mf_random` | Gives Henry a look at random among all, with its hair and beard |
| `ml_mf_henry` | Gives Henry his own face back |
| `ml_mf_refresh` | Rebuilds the model, for when the face does not show |
| `ml_mf_uninstall` | Gives Henry his face back before removing the mod. Then save, and remove it |

While the model changes, the screen goes black for a few seconds. A last `true` leaves it as it is. Typed with the inventory, the map or a menu open, a command waits until you close it. [COMMANDS.md](mod/kcd_male_framework/COMMANDS.md) has every command, with its Lua call.

## For modders

One call gives Henry another man's face: `MaleCore.SetLook(name)` from your mod, and `MaleCore.Henry()` brings his own back. [MODDING.md](mod/kcd_male_framework/MODDING.md) shows how, in a few lines.

## Compatibility and known limits

- **The barber's talk.** The framework replaces the game's `barber_dialogue.xml`, with its haircut hidden while a look is on, or a woman of KCD2 Female Framework, which ships the same copy. A mod that replaces the same file clashes with it, and the one that loads last wins.
- **Head meshes.** The heads and their beards replace the game's at their own paths. A mod that replaces the same meshes wins or loses by load order.
- **With a woman.** After `ml_ff_female` of KCD2 Female Framework, or with the character of a mod that plays its own, the commands do nothing. After `ml_ff_henry` they work again: use version 0.2.0 or later of both.
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
| `tools/generate_models.py` | The catalog of looks in `looks.toml`, the Skald graphs, the tokens and the Lua data of both frameworks, the barber's talk from `barber.toml`, and the game's barber dialog with its haircut hidden while a look is on |
| `tools/generate_heads.py` | The heads and their beards, with the first-person mask. It uses `fp_mask.py` |
| `tools/install_mod.py` | Packs the mod and copies it to the game. The game must be closed |

Set `KCD2_GAME` to the game's folder if it is not in the default Steam library.

## Roadmap to 1.0.0

Plans, not promises.

- **Clothes from other mods:** tested with clothing and armor mods, and a clear pipeline to make their pieces fit every face and body.

## License

Free for any use, also in closed or paid work. The only condition: credit KCD2 Male Framework where people can see it, like a line in your mod's description or credits. You do not need to include the license or publish your source. It does not cover the game's files or anything derived from them, such as the meshes. See [LICENSE](LICENSE).

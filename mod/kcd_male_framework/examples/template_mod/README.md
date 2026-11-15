# Template mod for KCD2 Male Framework

A mod that plays a man of its own, ready to copy and rename. It has:

| File | What |
|---|---|
| `faces.toml` | One face of its own, `template_hero`, and the lines for a head of your own, commented out |
| `data/Scripts/Mods/template_mod.lua` | Its Lua: it checks that the framework is there and new enough, and makes `template_hero` the start character, so every game, new or loaded, plays him |
| `mod.manifest` | Its name, id and version |
| `data/Libs`, `data/Quests`, `data/Scripts/MaleCore` | What the face tool wrote from `faces.toml`. You do not edit them: you run the tool again |

KCD2 Female Framework has the same template for a woman.

## Making it yours

1. **Copy the folder** wherever you keep your mod, and rename `template_mod` to the id of your mod: the folder, `data/Scripts/Mods/template_mod.lua`, the `modid` in `mod.manifest` and the `id` in `faces.toml`. In the Lua, rename `TemplateMod` and `[TEMPLATE_MOD]` too.
2. **Delete what the tool wrote**, the files under `data/Libs`, `data/Quests` and `data/Scripts/MaleCore`, since they carry the old id.
3. **Choose his face** in `faces.toml`: a head of the framework ([LOOKS.md](../../LOOKS.md)) or a head of your own, his body, his hair and his beard. [MAKING_FACES.md](../../MAKING_FACES.md) explains every field.
4. **Run the face tool**, from the root of the framework's repository, after every change of `faces.toml`:

   ```bash
   python -I -X utf8 mod/kcd_male_framework/tools/make_face_pack.py path/to/your_mod
   ```

5. **Point the Lua at him:** in `HERO`, the `look` is the `name` of his face in `faces.toml`, or any look of the framework. Leave `HERO` as `nil` if your mod plays Henry with his own face.
6. **Pack and install it,** with the game closed, from the root of the repository:

   ```bash
   python -I tools/install_mod.py path/to/your_mod
   ```

   Then enable it in your mod manager, next to KCD2 Male Framework.

## Trying it

- In `kcd.log`, `[TEMPLATE_MOD] loaded` when the game opens, and `[ML_MF] looks of template_mod: 1`.
- In a game, new or loaded, `[ML_MF] start character: Template Hero`. A few seconds later, Henry has his face. A new game waits for Henry's part, after the prologue with Godwin.
- `ml_mf_look template_hero` in the console puts his face on at any time, and `ml_mf_henry` takes it off.

## Clothes and armour

Clothes and armour for men fit every face as they are, with nothing to register: [MAKING_CLOTHES.md](../../MAKING_CLOTHES.md). Put them in this same mod, in its own tables and meshes, as for any man of the game.

## More

- Every call of the framework: [MODDING.md](../../MODDING.md).
- The console commands: [COMMANDS.md](../../COMMANDS.md).
- Credit KCD2 Male Framework where people can see it, like a line in your mod's description. That is the only condition of its license.

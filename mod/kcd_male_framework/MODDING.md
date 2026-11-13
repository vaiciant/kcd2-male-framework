# Using KCD2 Male Framework in your mod

How to give Henry another man's face in your story or your mod, with one command and nothing to set up, and how to give him his own face back.

## One command

From the console:

```text
ml_mf_look man_romani_4
```

From the Lua of your mod:

```lua
MaleCore.SetLook("man_romani_4")
```

That is all. Henry keeps playing as himself, with his story, his skills and his things, and the framework does the rest:

- He gets the head and the body of the look. His hair and beard change to the look's.
- His face and his beard hide in first-person view, as before.
- With a look, the barber's haircut is a talk with the hair and the beards that every face can wear. With his own face, Henry has the game's barber.
- Saving and loading keep the face.

`ml_mf_random`, or `MaleCore.SetRandomLook()`, gives him a look at random among all but the one he wears, and returns that look.

It takes a few seconds, under a black screen with a line that says so. If your mod covers the screen on its own, pass `true` as the second argument to leave it as it is: `MaleCore.SetLook("man_romani_4", true)`. A hair and a beard of the game can go on instead of the look's: `MaleCore.SetLook("man_czech_28", false, "m_hair_009_dark_brown", "m_beard_00")`. Any hair of the game for a man goes; a beard only if the head of the look has it, or the look's own goes on. From 0.5.0, `MaleCore.API` is 3. Every command is in [COMMANDS.md](COMMANDS.md).

## From the start of a game

To start a game with another face, choose it before it starts:

```lua
MaleCore.StartAs("man_romani_4")   -- or nil to cancel it; a hair and a beard may follow, as in SetLook
```

The game does not tell a new game from a loaded one, so the face goes on at the next start of the game, new or loaded, once the framework knows his state, a few seconds after the player has control. In a new game it waits for Henry's part, after the prologue with Godwin (the first day of the world), and for the end of any cutscene. It goes on once. Call it when your mod knows a game is about to start, for example from a choice in the main menu. `MaleCore.StartLook()` says which look waits. In the console it is `ml_mf_start`.

## Going back to Henry

```text
ml_mf_henry
```

```lua
MaleCore.Henry()
```

Henry gets his own face, hair and beard back. Use it as often as you like.

## The looks

`ml_mf_looks` writes every look in the console. Each one has a short name that never changes:

| Name | What it is |
|---|---|
| `man_czech_1`, `man_hungarian_1`, `man_romani_1`… | A generic face of the game, by people and number |
| `m_head_chamberlain` and the like | The face of a named character of the story: it keeps its internal name |

From Lua:

```lua
for _, look in ipairs(MaleCore.ListLooks()) do
	-- look.id, look.name, look.ethnicity ("czech", "hungarian", "romani" or nil),
	-- look.age ("young" or "old"), look.villager (false for a named character's face),
	-- look.characters (the characters of the game with a name of their own who wear its face, maybe none)
end
```

[LOOKS.md](LOOKS.md) lists them all, by look and by character.

Use `look.villager` and `look.age` to offer only the faces that suit your story, as KCD2 Life offers only young villagers.

## Adding faces

Every look is an entry of [`looks.toml`](looks.toml): the head of the game, the body, the hair, the beard, and its people. To add a face, even one from another mod:

1. Add an entry with the next `id` and the name of its head. Without `ethnicity`, it shows with its internal name.
2. Run `tools/generate_models.py` and then `tools/generate_heads.py`, from the root of the repository. They write the rest: the model, the token, and the copies of the head and the beards that hide in first-person view.

A face only fits if its head has the five beards of the barber, in `barber.toml`. The generator adds by itself every face of the game that does, and never changes an entry that is already there.

## Before you call it

**Check that the framework is there,** in your `OnGameplayStarted` handler, never when your file loads: the load order of mods is not fixed.

```lua
if not (MaleCore and MaleCore.LOADED) then
	System.LogAlways("[MYMOD] KCD2 Male Framework is missing")
	return
end
```

## If your mod plays its own character

The commands put the look on Henry's soul. If your mod switches to a character of its own, as KCD2 Life does, tell the framework, so its commands do nothing while that character is in use:

```lua
MaleCore.OtherCharacter = function() return MyMod.IsOwnCharacter() end
```

The framework also puts a look on the playable character of KCD2 Life, its soul `ml_player`. KCD2 Life keeps the switch, `SwitchPlayer`, and only calls the framework:

| When | Call |
|---|---|
| Before the switch, with Henry in use | `MaleCore.ChooseNewCharacter(look)`: Henry gets the token of that look |
| Before the switch, if his first haircut should be free | `MaleCore.GiveFreeHaircut()`: his next haircut at a barber costs nothing |
| When the switch ends | Your Skald project gives Henry `MaleCore.NEW_STARTED_TOKEN`, and the look turns on |
| Once the new character is in use | `MaleCore.ShowNewCharacter(look, after)`: hair and beard of the look, and the model rebuilds. `after` runs at the end |
| After every load and every map | `MaleCore.Refresh()` |

A mod that switches to that same soul can do the same.

## With KCD2 Female Framework and KCD2 Life

They work alone or together. After `ml_ff_female` of KCD2 Female Framework, Henry is a woman. `MaleCore.SetLook` then goes straight to the face: it calls `FemaleCore.Henry(true, after)`, which turns her back into Henry, and puts the face on once that is done, under its own black screen. That needs `FemaleCore.API` 4 (KCD2 Female Framework 0.4.0 or later); with an older one it does nothing until `ml_ff_henry`. The other calls do nothing while she is a woman. After `ml_ff_henry` they all work: before a look, this framework calls `FemaleCore.TakeOffHenry()`, so the head of Henry that KCD2 Female Framework keeps on does not cover it, and `ml_mf_henry` calls `FemaleCore.KeepHenry()` before its last rebuild, so a beard never lands on her head. Use 0.2.0 or later of both. A new life of KCD2 Life is its own character, and there they do nothing either. Both frameworks share the numbers of the looks, so a look's id means the same face in both.

## Credit

Use it in any mod, closed or open. Asking for donations or Patreon support is fine, as long as nothing in your mod is only for those who pay: Warhorse's rules do not allow selling KCD2 mods. The only condition is a credit where people can see it, like a line in your mod's description: "Uses KCD2 Male Framework". See [LICENSE](LICENSE).

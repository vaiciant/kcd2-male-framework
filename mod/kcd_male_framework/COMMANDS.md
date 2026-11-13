# KCD2 Male Framework: console commands

Every command of the framework, and the Lua call that does the same from another mod. Open the console with the key under Esc, type the command and press Enter. They need no launch options.

A look is its name or its id: `man_czech_2` or `2`. `ml_mf_looks` lists them all.

**In the game only.** The commands that change the model wait for the game itself: typed with the inventory, the map or a menu open, the change starts once you close it.

| Command | What it does | From Lua |
|---|---|---|
| `ml_mf_looks` | Writes every look in the console: its name, its people, its age, its id and the characters of the game with a name of their own who wear its face, as in [LOOKS.md](LOOKS.md) | `MaleCore.ListLooks()` |
| `ml_mf_look [look] [hair] [beard] [true]` | Gives Henry the head and the body of that look, and its hair and beard. Without a look, the first one. A hair and a beard of the game go on instead of the look's, like `ml_mf_look man_czech_28 m_hair_009_dark_brown m_beard_00`: [LOOKS.md](LOOKS.md) has this command for every character | `MaleCore.SetLook(look, noScreen, hair, beard)` |
| `ml_mf_random [true]` | Gives Henry a look at random among all but the one he wears, with its hair and beard | `MaleCore.SetRandomLook(noScreen)` |
| `ml_mf_henry [true]` | Gives Henry his own face, hair and beard back | `MaleCore.Henry(noScreen)` |
| `ml_mf_refresh` | Rebuilds the model, for when the face of the look does not show | `MaleCore.Refresh()` |
| `ml_mf_start [look] [hair] [beard]` | The next game that starts or loads begins with the face of that look, and the hair and the beard if given, as in `ml_mf_look`. It works in the main menu, before New Game. `none` cancels it; with nothing, it says which look waits | `MaleCore.StartAs(look, hair, beard)` |
| `ml_mf_uninstall` | Gives Henry his face back and clears what the framework left in the save. Run it, save, and then remove the mod | `MaleCore.Uninstall()` |

## A hair and a beard of the game

After the look, `ml_mf_look` takes a hair and a beard by their names in the game, in any order. Any hair of the game for a man goes, also those the barber does not have, like a character's own; whether it sits well on another head is up to the game. A beard goes only if the head of the look has it, because a beard missing on a head has crashed the game: one that does not is left out, the look's own goes on, and the console says so. `m_beard_00` is no beard, and fits any head.

```text
ml_mf_look man_czech_28 m_hair_009_dark_brown m_beard_00
```

## Before the game starts

`ml_mf_start` chooses his face before you play, and works in the main menu too: open the console there, type it, and start a new game.

```text
ml_mf_start man_romani_4
```

The game does not tell a new game from a loaded one, so the face goes on at the next start of the game, new or loaded, a few seconds after you have control, under the black screen. A new game begins with Godwin: the face waits for Henry's part, and for the end of the cutscene that starts it, so it goes on once he rides. It goes on once: `ml_mf_start none` cancels it before that. From Lua, `MaleCore.StartAs(look)` does the same, and `MaleCore.StartLook()` says which look waits.

## The black screen

While the model changes, the screen goes black for a few seconds, with a line that says so, and Henry cannot move. A last `true` leaves the screen as it is:

```text
ml_mf_look man_czech_2 true
ml_mf_henry true
```

From Lua it is the last argument, `noScreen`. Left out, it is `false`, and the screen goes black. A mod that covers the screen on its own, as KCD2 Life does, passes `true`.

## Limits

- **For a moment after a load,** the framework asks for the face in use, and two small tokens may show in the inventory for a second.

## When the commands do nothing

- **Another character in use.** A mod that plays its own character instead of Henry, as KCD2 Life does, turns them off.
- **Henry is a woman.** After `ml_ff_female` of [KCD2 Female Framework](https://github.com/vaiciant/kcd2-female-framework/blob/main/mod/kcd_female_framework/COMMANDS.md), `ml_mf_look` and `ml_mf_random` turn her back into Henry first, with that framework, and then put the face on, under one black screen: no `ml_ff_henry` needed. That needs KCD2 Female Framework 0.4.0 or later; with an older one they do nothing until `ml_ff_henry`. The other commands do nothing while she is a woman.

Each command writes what it did in the console and in `kcd.log`, in lines that start with `[ML_MF]`.

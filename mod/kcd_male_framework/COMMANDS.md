# KCD2 Male Framework: console commands

Every command of the framework, and the Lua call that does the same from another mod. Open the console with the key under Esc, type the command and press Enter. They need no launch options.

A look is its name or its id: `man_czech_2` or `2`. `ml_mf_looks` lists them all.

**In the game only.** The commands that change the model wait for the game itself: typed with the inventory, the map or a menu open, the change starts once you close it.

| Command | What it does | From Lua |
|---|---|---|
| `ml_mf_looks` | Writes every look in the console: its name, its people, its age and its id | `MaleCore.ListLooks()` |
| `ml_mf_look [look] [true]` | Gives Henry the head and the body of that look, and its hair and beard. Without a look, the first one | `MaleCore.SetLook(look, noScreen)` |
| `ml_mf_random [true]` | Gives Henry a look at random among all but the one he wears, with its hair and beard | `MaleCore.SetRandomLook(noScreen)` |
| `ml_mf_henry [true]` | Gives Henry his own face, hair and beard back | `MaleCore.Henry(noScreen)` |
| `ml_mf_refresh` | Rebuilds the model, for when the face of the look does not show | `MaleCore.Refresh()` |
| `ml_mf_uninstall` | Gives Henry his face back and clears what the framework left in the save. Run it, save, and then remove the mod | `MaleCore.Uninstall()` |

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
- **Henry is a woman.** After `ml_ff_female` of [KCD2 Female Framework](https://github.com/vaiciant/kcd2-female-framework/blob/main/mod/kcd_female_framework/COMMANDS.md), they do nothing, so they do not put a man's face on her. After `ml_ff_henry` they work again, with version 0.2.0 or later of both.

Each command writes what it did in the console and in `kcd.log`, in lines that start with `[ML_MF]`.

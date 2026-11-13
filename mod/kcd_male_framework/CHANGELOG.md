# KCD2 Male Framework: changelog

Only minor versions are listed here: 0.1.0, 0.2.0 and so on. Every build between them raises the last number of the version, and those builds are not listed.

## 0.5.0

Any hair and beard of the game goes on with the face, from one command.

### New

- **A hair and a beard in `ml_mf_look`.** `ml_mf_look man_czech_28 m_hair_009_dark_brown m_beard_00` gives Henry that face with that hair and beard: any hair of the game for a man, also those the barber does not have, and a beard the face has. `ml_mf_start` takes them too.
- **LOOKS.md** has, for every character of the game, the command that gives the face with their hair and beard. Olda of Semine is `ml_mf_look man_czech_28 m_hair_009_dark_brown m_beard_00`.
- **For modders:** `MaleCore.SetLook(look, noScreen, hair, beard)` and `MaleCore.StartAs(look, hair, beard)`. `MaleCore.API` is 3.

### Fixes

- **`ml_mf_look`** no longer ignores what comes after the look. A beard the face does not have is left out, and the console says so, because a missing beard has crashed the game.

## 0.4.0

His face now reaches the game's cutscenes, and the framework works on its own.

### New

- **Cutscenes.** The doubles of Henry that the game's cutscenes make wear his face. The five scenes of the prologue and the Cumans' contest show his face and body, not Henry's.
- **The pillory.** His face comes back right after it.
- **On its own.** It no longer needs KCD2 Female Framework, and works with it as before. KCD2 Life needs both.
- **From a woman to a face.** With KCD2 Female Framework, `ml_mf_look` and `ml_mf_random` turn her into a man with that face, without going back to Henry first.
- **LOOKS.md** says which named characters of the game wear each face, and `ml_mf_looks` shows their names. Olda, for one, is `man_czech_28`.
- **For modders:** `MaleCore.Ready()`.

### Fixes

- **Her shift** no longer shows on him after switching from a woman: every face wears Henry's underwear.
- **His beard** no longer goes missing when a command is typed right after loading: commands wait until both frameworks have read the save.
- **The doubles of the cutscenes** keep the haircut from the barber.

## 0.3.0

- **Start a new game with another face.** `ml_mf_start man_romani_4`, in the console of the main menu before New Game, chooses his face. It goes on once Henry's part begins, after the prologue with Godwin and the cutscene that ends it. It works for the next game that starts or loads, once, and `ml_mf_start none` cancels it.
- **For modders:** `MaleCore.StartAs(look)` and `MaleCore.StartLook()` are new. `MaleCore.API` is 2.
- **License:** asking for donations or Patreon support for a mod that uses it is fine, as long as nothing in it is only for those who pay. Warhorse's rules do not allow selling KCD2 mods.

## 0.2.0

- **With KCD2 Female Framework 0.2.0:** a woman can now become Henry again, and the faces of this framework work after that. Before a face of its own goes on, it takes off the head of Henry that KCD2 Female Framework keeps on, and `ml_mf_henry` puts it back, so a beard never lands on a woman's head.
- Use both frameworks at 0.2.0 or later together.

## 0.1.0

The first release.

- **Another face for Henry.** One command, `ml_mf_look`, gives him any of 74 men's faces of the game, with its body, `ml_mf_random` one at random, and `ml_mf_henry` gives him his own back. Other mods can do it from Lua.
- **First person** hides the face and the beard, as it does Henry's.
- **A barber that fits:** with a look, the hair and the beard are chosen in a talk, among those every face can wear, for 50 groschen, or 5 with Realish Economy. Henry with his own face keeps the game's barber.
- **Saves and maps** keep the face.
- **Removing it:** `ml_mf_uninstall` gives Henry his face back first.

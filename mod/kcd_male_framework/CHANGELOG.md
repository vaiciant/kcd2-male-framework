# KCD2 Male Framework: changelog

Only minor versions are listed here: 0.1.0, 0.2.0 and so on. Every build between them raises the last number of the version, and those builds are not listed.

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

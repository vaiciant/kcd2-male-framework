# Contributing to KCD2 Male Framework

Thank you for helping. Every change comes in as a pull request, and the maintainer reads each one and decides whether it goes in. To keep that quick, each pull request has to say what it changes and why.

## A pull request

- **Say what you changed and why.** The template asks three things: what you changed, why (what was wrong or missing), and how you tested it. A pull request without them is closed, and you are welcome to open it again with them.
- **One change per pull request.** A fix and a new feature go in two.
- **In English:** the title of the pull request, its description and every commit message. A short first line of the commit says what it does, like `Fix the rent of the inn at Zhelejov`.
- **Test it in the game,** *Kingdom Come: Deliverance II* 1.5, and say which other mods you had on.
- **Leave the version alone,** in `mod.manifest` and in the changelog. The maintainer sets it for each release.
- **Talk first about big changes.** Open an issue before a new system or a large rework, so you do not spend time on something that will not go in.

## The code

- Code, comments, console output and tool messages are in English. What the player reads goes through the localization files, in English and Spanish.
- Follow the style of the files around yours.
- Some files are written by the tools in `tools/` and `mod/kcd_male_framework/tools/`, from `.toml` files or from the game. Change what the tool reads, run the tool, and commit both.
- To build and install the mod, see "Building from source" in the README.

## What cannot go in

- Files of the game, or made from them: meshes, textures, tables, dialogs. The tools build them from each person's own copy of the game, and git ignores them.
- Code, meshes or tables from other mods, unless their license allows it and the pull request says so.
- Entity classes of the mod saved in the game: a save that holds one does not load once the mod is removed.

## Reporting a problem

Open an issue with:

- the game version, and the mod's version, from its `mod.manifest`;
- your other mods;
- what you did, what you expected and what happened;
- the lines of `kcd.log`, in the game's folder, that start with `[ML_MF]`.

## License

What you contribute goes under the mod's [LICENSE](LICENSE): free for any use, with a credit.

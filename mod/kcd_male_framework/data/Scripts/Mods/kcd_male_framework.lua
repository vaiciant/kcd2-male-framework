-- =============================================================================
-- KCD2 Male Framework: startup. The game loads this file when it opens. It works with
-- Henry in the game with no other mod: MODDING.md.
-- =============================================================================
MaleCore = MaleCore or {}
MaleCore.LOADED = true

Script.LoadScript("Scripts/MaleCore/male_core.lua")
Script.LoadScript("Scripts/MaleCore/looks_data.lua")
Script.LoadScript("Scripts/MaleCore/barber.lua")
Script.LoadScript("Scripts/MaleCore/cutscene_doubles.lua")

if not (MaleCore.SetLook and MaleCore.LOOKS and MaleCore.Barber and MaleCore.CutsceneDoubles) then
	System.LogAlways("[ML_MF] ERROR a file did not load")
	return
end

-- Faces from other mods (MAKING_FACES.md): every Lua file of this folder, in any mod, registers a face pack with
-- MaleCore.RegisterLooks, after the framework's own looks. The folder is read through the paks of all the mods.
MaleCore.LOOKS_FOLDER = "Scripts/MaleCore/Looks"
local scannedLooks, lookFiles = pcall(System.ScanDirectory, MaleCore.LOOKS_FOLDER, SCANDIR_FILES)
for _, file in ipairs(scannedLooks and type(lookFiles) == "table" and lookFiles or {}) do
	if string.lower(string.sub(file, -4)) == ".lua" then
		Script.LoadScript(MaleCore.LOOKS_FOLDER .. "/" .. file)
	end
end

System.AddCCommand("ml_mf_looks", "MaleCore.PrintLooks()", "Lists the men's looks of KCD2 Male Framework: name, people, age and id")
System.AddCCommand("ml_mf_look", "MaleCore.LookCommand(%line)", "Gives Henry the face of a look, by name or id, like ml_mf_look man_romani_4. After it, a hair and a beard of the game instead of the look's, like ml_mf_look man_czech_28 m_hair_009_dark_brown m_beard_00 (LOOKS.md). A last word true leaves out the black screen")
System.AddCCommand("ml_mf_random", "MaleCore.RandomCommand(%line)", "Gives Henry a look at random among all, with its hair and beard. A last word true leaves out the black screen")
System.AddCCommand("ml_mf_henry", "MaleCore.HenryCommand(%line)", "Gives Henry his own face, hair and beard back. ml_mf_henry true leaves out the black screen")
System.AddCCommand("ml_mf_uninstall", "MaleCore.UninstallCommand()", "Gives Henry his own face back, before removing the framework: then save and remove it")
System.AddCCommand("ml_mf_refresh", "MaleCore.RefreshCommand()", "Rebuilds the model, for when the face of the look does not show")
System.AddCCommand("ml_mf_start", "MaleCore.StartCommand(%line)", "The next game that starts or loads begins with the face of that look, like ml_mf_start man_romani_4, and a hair and a beard if given, as in ml_mf_look: type it in the main menu before New Game. ml_mf_start none cancels it")
System.AddCCommand("ml_developer", "MaleCore.DeveloperCommand()", "Turns developer mode on until the game closes: the test commands of KCD2 Male Framework, and of KCD2 Female Framework and KCD2 Life if they are there")

local ok, problem = pcall(function() UIAction.RegisterEventSystemListener(MaleCore, "System", "OnGameplayStarted", "OnGameplayStarted") end)
MaleCore.Log(ok and "listening to OnGameplayStarted" or ("ERROR listener " .. tostring(problem)))

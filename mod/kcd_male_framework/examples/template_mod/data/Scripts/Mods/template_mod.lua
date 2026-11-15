-- =============================================================================
-- Template mod for KCD2 Male Framework (README.md next to faces.toml). The game loads this file when it opens, as it
-- loads every file of Scripts/Mods in every mod. Rename template_mod and TemplateMod everywhere: this file, the folder,
-- mod.manifest and faces.toml.
-- =============================================================================
TemplateMod = TemplateMod or {}

-- The man your mod plays: one of its own faces (faces.toml) or any look of the framework (ml_mf_looks). His face goes
-- on at every start of the game, new or loaded; a new game waits for Henry's part, after the prologue with Godwin.
-- To play Henry with his own face instead, leave HERO as nil.
TemplateMod.HERO = {
	name = "Template Hero",           -- for the log
	look = "template_hero",           -- a look, by name or id
	hair = "m_hair_013_black",        -- optional: any man's hair of the game
	beard = "m_beard_16",             -- optional: a beard his head has
}

-- The framework's API that this mod needs: 5 is KCD2 Male Framework 1.0.0, with the faces of other mods.
TemplateMod.API = 5

local function log(...)
	local parts = {}
	for i = 1, select("#", ...) do
		parts[#parts + 1] = tostring((select(i, ...)))
	end
	System.LogAlways("[TEMPLATE_MOD] " .. table.concat(parts, " "))
end

-- At every start of the game, new or loaded. The framework is looked for here and not when this file loads: the load
-- order of mods is not fixed.
function TemplateMod:OnGameplayStarted()
	if not (MaleCore and MaleCore.LOADED) then
		log("KCD2 Male Framework is missing")
		return
	end
	if (MaleCore.API or 0) < TemplateMod.API then
		log("KCD2 Male Framework is too old: API", tostring(MaleCore.API), "- this mod needs", TemplateMod.API)
		return
	end
	if TemplateMod.HERO then
		-- The same table every time, so the framework knows it is the same man.
		MaleCore.RegisterStartCharacter(TemplateMod.HERO)
	end
	-- What else your mod does with the framework goes here, for example, from a talk or a quest of your mod:
	--   MaleCore.SetLook("man_romani_4")   another face, under a black screen
	--   MaleCore.Henry()                   his own face back
	-- MODDING.md has every call.
end

local ok, problem = pcall(function()
	UIAction.RegisterEventSystemListener(TemplateMod, "System", "OnGameplayStarted", "OnGameplayStarted")
end)
log(ok and "loaded" or ("ERROR listener " .. tostring(problem)))

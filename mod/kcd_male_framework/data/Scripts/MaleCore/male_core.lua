-- =============================================================================
-- MaleCore: the API of KCD2 Male Framework (MODDING.md). It puts the face of a look on
-- Henry himself, and takes it away, with no other mod. Head and body are overrides of
-- ml_mf_face.xml, picked with a token given to Henry. Hair and beard go on his soul with
-- the native Barber object, as the barbers of the game do. The model only shows the
-- overrides after a rebuild, which a real beard change forces.
-- =============================================================================
MaleCore = MaleCore or {}

-- 3: SetLook and StartAs take a hair and a beard besides the look's.
MaleCore.API = 3
MaleCore.TOKEN_MS = 1000
MaleCore.REBUILD_MS = 1000
-- Every head of the catalog has them, and so does Henry's.
MaleCore.REBUILD_BEARD = "m_beard_17"
MaleCore.REFRESH_BEARD = "m_beard_18"
-- A beard is a mesh in the folder of each head, and one missing on the head in use has crashed the game. This one has no
-- mesh, so it is the safe beard while the head changes.
MaleCore.SAFE_BEARD = "m_beard_00"
-- Henry's own hair and beard, from his rule in STORM.
MaleCore.HENRY_HAIR = "m_hair_henry"
MaleCore.HENRY_BEARD = "m_beard_00"
-- MaleCore.LOOKS and the tokens come from looks_data.lua.

-- A mod that plays its own character instead of Henry, like KCD2 Life, puts here a function that says so. The face
-- goes on Henry's soul, so with another character the commands do nothing.
MaleCore.OtherCharacter = MaleCore.OtherCharacter or function() return false end

local function notHenry()
	local ok, other = pcall(MaleCore.OtherCharacter)
	if ok and other then
		MaleCore.Log("the character in use is not Henry: nothing to do")
		return true
	end
	-- After ml_ff_female of KCD2 Female Framework, Henry is a woman until ml_ff_henry true.
	local _, woman = pcall(function() return FemaleCore and FemaleCore.IsWoman and FemaleCore.IsWoman() end)
	if woman then
		MaleCore.Log("Henry is a woman now: nothing to do")
		return true
	end
	return false
end

function MaleCore.Log(...)
	local parts = {}
	for i = 1, select("#", ...) do
		parts[#parts + 1] = tostring((select(i, ...)))
	end
	System.LogAlways("[ML_MF] " .. table.concat(parts, " "))
end

local function try(label, fn, ...)
	local ok, result = pcall(fn, ...)
	if not ok then
		MaleCore.Log("ERROR", label, result)
		return nil
	end
	return result
end

-- Black screen

-- A black screen with a line of text, through the HUD, while the model changes. The player cannot move under it.
MaleCore.SCREEN_TEXT = "@ml_mf_changing_look"
-- Whatever fails, the screen does not stay black longer than this.
MaleCore.SCREEN_MAX_MS = 20000
local FADE_IN = 1
local FADE_OUT = 2
local TEXT_LAYOUT = 3
local TEXT_FADE_MS = 1000
local LOCK_MS = 100
local screen = { up = false, gen = 0 }

local function hud(name, ...)
	local args = { ... }
	try("hud " .. name, function() UIAction.CallFunction("hud", -1, name, unpack(args)) end)
end

-- The engine enables the map again, for example when the console closes, so it is locked in a loop.
local function lockInput()
	if screen.up then
		try("input lock", function() ActionMapManager.EnableActionMap("player", false) end)
		Script.SetTimer(LOCK_MS, lockInput)
	end
end

local function hideScreen()
	if not screen.up then
		return
	end
	screen.up = false
	hud("HideNarrativeSubtitles", TEXT_FADE_MS)
	hud("SetFaderState", FADE_OUT, "")
	try("input lock", function() ActionMapManager.EnableActionMap("player", true) end)
end

-- noScreen true leaves the screen as it is, for a mod that covers it on its own.
local function showScreen(noScreen)
	if noScreen then
		return
	end
	screen.gen = screen.gen + 1
	local gen = screen.gen
	if not screen.up then
		screen.up = true
		lockInput()
	end
	hud("SetFaderState", FADE_IN, "")
	hud("SetNarrativeSubtitles", MaleCore.SCREEN_TEXT, TEXT_LAYOUT, TEXT_FADE_MS)
	Script.SetTimer(MaleCore.SCREEN_MAX_MS, function()
		if screen.gen == gen then
			hideScreen()
		end
	end)
end

-- Skald reacts when it arrives.
local function sendToken(guid)
	try("token", function() player.inventory:CreateItem(guid, 1, 1) end)
	Script.SetTimer(MaleCore.TOKEN_MS, function()
		try("token", function() player.inventory:DeleteItemOfClass(guid, 1) end)
	end)
end

-- The id of the look Henry wears. 0 is his own face. Skald keeps it in the save, and nothing shows in the inventory:
-- after a load, Lua asks and Skald answers with as many answer tokens as the id.
MaleCore.current = 0

function MaleCore.Current()
	return MaleCore.current
end

-- The buff ml_mf_look tells the copies of the game's scenes that the framework ships, the same as KCD2 Female
-- Framework's, that Henry wears a look: five scenes of the prologue and of the Cumans put Henry's wounded head and his
-- wet or bandaged body on the player, and leave them off him then. After a load a scene can look before the buff
-- is back, as with a woman: each load starts with setCurrent(0), which takes it off, and puts it on again once
-- Skald says the look, before the rebuild, so each scene hears it arrive. Only on Henry: a scene of his story is never
-- on the character of another mod. buff__kcd_male_framework.xml has the same id.
MaleCore.LOOK_BUFF = "85020dc3-349b-5717-a236-adaf7e2a7001"

local function markLook(on)
	local ok, other = pcall(MaleCore.OtherCharacter)
	if ok and other then
		return
	end
	try("look mark", function()
		player.soul:RemoveAllBuffsByGuid(MaleCore.LOOK_BUFF)
		if on then
			player.soul:AddBuff(MaleCore.LOOK_BUFF)
		end
	end)
end

local function setCurrent(id)
	MaleCore.current = id
	markLook(id > 0)
end

local function count(class)
	return try("token", function() return player.inventory:GetCountOfClass(class) end) or 0
end

local function askCurrent(after)
	sendToken(MaleCore.ASK_TOKEN)
	Script.SetTimer(MaleCore.TOKEN_MS + 200, function()
		local id = count(MaleCore.ANSWER_ITEM)
		if id > 0 then
			try("token", function() player.inventory:DeleteItemOfClass(MaleCore.ANSWER_ITEM, id) end)
		end
		setCurrent(id)
		after(id)
	end)
end

local function withBarber(label, fn)
	try(label, function()
		local barber = Barber:Create(player.soul)
		fn(barber)
		barber:Commit()
		Barber:Destroy(barber)
	end)
end

-- Two beard changes, in case one is the beard in use, and back: the model rebuilds and shows the overrides. Then the
-- hair and beard of the look, if any.
local function rebuild(hair, beard, after)
	local barber = try("rebuild", function()
		local object = Barber:Create(player.soul)
		object:TryBeard(MaleCore.REBUILD_BEARD)
		return object
	end)
	Script.SetTimer(MaleCore.REBUILD_MS, function()
		try("rebuild", function() barber:TryBeard(MaleCore.REFRESH_BEARD) end)
		Script.SetTimer(MaleCore.REBUILD_MS, function()
			try("rebuild", function()
				barber:Revert()
				Barber:Destroy(barber)
			end)
			if hair then
				withBarber("look parts", function(final)
					final:TryHair(hair)
					final:TryBeard(beard)
				end)
			end
			MaleCore.Log("rebuilt")
			if after then
				after()
			end
		end)
	end)
end

-- Looks

-- MaleCore.LOOKS is a list in menu order. Each look keeps its id, shared with KCD2 Female Framework, so the ids of the
-- men are not one after another.
-- soul is the model with that look, for a mod that shows it before choosing, as the selector of KCD2 Life does.
-- characters are the characters of the game with a name of their own who wear its face, as in LOOKS.md.
local function copy(look)
	return look and { id = look.id, name = look.name, ethnicity = look.ethnicity, age = look.age, villager = look.villager, soul = look.soul,
		characters = { unpack(look.characters or {}) } }
end

local function find(key)
	for _, look in ipairs(MaleCore.LOOKS) do
		if look.name == key or tostring(look.id) == tostring(key) then
			return look
		end
	end
	return nil
end

function MaleCore.GetLook(id)
	return copy(find(id))
end

function MaleCore.ListLooks()
	local list = {}
	for _, look in ipairs(MaleCore.LOOKS) do
		list[#list + 1] = copy(look)
	end
	return list
end

function MaleCore.FindLook(name)
	return copy(find(name))
end

-- A hair and a beard instead of the look's: any hair of the game for a man (MaleCore.HAIRS), and a beard its head
-- has a mesh for (the look's beards), because a beard without one on the head has crashed the game. A name that is
-- neither is said in the log, and the look's own goes on. Returns the hair and the beard to put on.
local hairs
local function partsOf(look, hair, beard)
	if not hairs then
		hairs = {}
		for _, known in ipairs(MaleCore.HAIRS or {}) do
			hairs[known] = true
		end
	end
	if hair and not hairs[hair] then
		MaleCore.Log("no hair called", hair, "- the look's own goes on:", look.hair)
		hair = nil
	end
	if beard then
		local found = false
		for _, known in ipairs(look.beards or {}) do
			found = found or known == beard
		end
		if not found then
			MaleCore.Log("the head of", look.name, "has no beard", beard, "- the look's own goes on:", look.beard)
			beard = nil
		end
	end
	return hair or look.hair, beard or look.beard
end

-- A woman of KCD2 Female Framework goes straight to a face: that framework turns her back into Henry first, and
-- then the face goes on as after ml_ff_henry, all under one black screen. Its way back puts Henry's head and body on as
-- a look, because her head may still be his soul's own and a beard on it has crashed the game. It needs FemaleCore.API
-- 4, whose Henry says when it is done. Says whether she was a woman, and then whether the change started.
local function fromWoman(name, noScreen, hair, beard)
	local _, woman = pcall(function() return FemaleCore and FemaleCore.IsWoman and FemaleCore.IsWoman() end)
	local ok, other = pcall(MaleCore.OtherCharacter)
	if not woman or (ok and other) then
		return false
	end
	if not (name and find(name) or MaleCore.LOOKS[1]) then
		MaleCore.Log("no look called", name, "- ml_mf_looks lists them")
		return true, false
	end
	if (FemaleCore.API or 0) < 4 or type(FemaleCore.Henry) ~= "function" then
		MaleCore.Log("Henry is a woman now: ml_ff_henry first, or KCD2 Female Framework 0.3.8 or later")
		return true, false
	end
	MaleCore.Log("Henry is a woman: KCD2 Female Framework turns her back into Henry first")
	showScreen(noScreen)
	local started = try("female framework", FemaleCore.Henry, true, function() MaleCore.SetLook(name, noScreen, hair, beard) end)
	if not started then
		hideScreen()
	end
	return true, started == true
end

-- Henry takes the face of that look: a name or an id. Without one, the first look. noScreen true leaves out the black
-- screen. hair and beard, names of the game, go on instead of the look's own, if they fit.
function MaleCore.SetLook(name, noScreen, hair, beard)
	local woman, started = fromWoman(name, noScreen, hair, beard)
	if woman then
		return started
	end
	if notHenry() then
		return false
	end
	local look = name and find(name) or MaleCore.LOOKS[1]
	if not look then
		MaleCore.Log("no look called", name, "- ml_mf_looks lists them")
		return false
	end
	hair, beard = partsOf(look, hair, beard)
	MaleCore.Log("look", look.name, "id", look.id, "hair", hair, "beard", beard)
	showScreen(noScreen)
	try("barber forget", MaleCore.Barber.Forget)
	-- The beard of the head of now may not exist on the next one.
	withBarber("safe beard", function(barber) barber:TryBeard(MaleCore.SAFE_BEARD) end)
	-- After ml_ff_henry, KCD2 Female Framework keeps Henry's head and body on as a look of its own: they would cover this one.
	if FemaleCore and FemaleCore.TakeOffHenry then
		try("female framework", FemaleCore.TakeOffHenry)
	end
	sendToken(MaleCore.RESET_TOKEN)
	Script.SetTimer(MaleCore.TOKEN_MS + 200, function()
		sendToken(look.token)
		setCurrent(look.id)
		Script.SetTimer(MaleCore.TOKEN_MS + 200, function() rebuild(hair, beard, hideScreen) end)
	end)
	return true
end

-- A look at random among all but the one he wears, with its hair and beard. Returns that look, or nil.
function MaleCore.SetRandomLook(noScreen)
	local choices = {}
	for _, look in ipairs(MaleCore.LOOKS) do
		if look.id ~= MaleCore.current then
			choices[#choices + 1] = look
		end
	end
	if #choices == 0 then
		return nil
	end
	local look = choices[math.random(#choices)]
	return MaleCore.SetLook(look.id, noScreen) and copy(look) or nil
end

-- Henry gets his own face, hair and beard back.
function MaleCore.Henry(noScreen)
	if notHenry() then
		return
	end
	MaleCore.Log("back to Henry's face")
	showScreen(noScreen)
	-- Barber:Commit keeps in the soul the head it sees, so each look left its head as Henry's own. His head and body go on
	-- as one more look, and the commit with them in view gives them back to his soul. Then every look goes off.
	withBarber("safe beard", function(barber) barber:TryBeard(MaleCore.SAFE_BEARD) end)
	sendToken(MaleCore.RESET_TOKEN)
	setCurrent(0)
	Script.SetTimer(MaleCore.TOKEN_MS + 200, function()
		sendToken(MaleCore.HENRY_TOKEN)
		Script.SetTimer(MaleCore.TOKEN_MS + 200, function()
			rebuild(MaleCore.HENRY_HAIR, MaleCore.HENRY_BEARD, function()
				-- If Henry was a woman of KCD2 Female Framework, her head may still be his soul's own, and the last rebuild
				-- changes the beard: that framework puts his head and body back on first.
				if FemaleCore and FemaleCore.KeepHenry then
					try("female framework", FemaleCore.KeepHenry)
				end
				sendToken(MaleCore.RESET_TOKEN)
				Script.SetTimer(MaleCore.TOKEN_MS + 200, function()
					rebuild(nil, nil, function()
						MaleCore.Log("Henry's own face is back")
						hideScreen()
					end)
				end)
			end)
		end)
	end)
end

-- The new character of KCD2 Life, its playable soul ml_player. The commands do nothing with it,
-- and KCD2 Life calls these. Before SwitchPlayer, Henry gets the token of that character's look. KCD2 Life gives Henry
-- NEW_STARTED_TOKEN when the switch ends, and Skald turns the look on then.
function MaleCore.ChooseNewCharacter(name)
	local look = find(name)
	if not look then
		MaleCore.Log("no look called", name, "for the new character")
		return false
	end
	MaleCore.Log("new character look", look.name, "id", look.id)
	sendToken(look.new_token)
	return true
end

-- Once the new character is in use: its hair and beard, and a rebuild that shows the look. after runs at the end.
function MaleCore.ShowNewCharacter(name, after)
	local look = find(name)
	if not look then
		MaleCore.Log("no look called", name, "for the new character")
		return false
	end
	rebuild(look.hair, look.beard, after)
	return true
end

-- Whether the character in use wears a look of the framework: Henry with one, or the new character of KCD2 Life, if a
-- man. Then his barber is the talk of the framework (barber.lua), and the screen of the game is only for Henry
-- with his own face.
function MaleCore.ModelInUse()
	local _, woman = pcall(function() return FemaleCore and FemaleCore.WomanInUse and FemaleCore.WomanInUse() end)
	if woman then
		return false
	end
	if MaleCore.Current() > 0 then
		return true
	end
	local ok, other = pcall(MaleCore.OtherCharacter)
	return ok and other == true
end

-- His next haircut at a barber is free: KCD2 Life gives it before its new character starts, as it does for a woman.
function MaleCore.GiveFreeHaircut()
	sendToken(MaleCore.FREE_HAIRCUT_TOKEN)
	MaleCore.Log("next haircut free")
end

-- With Realish Economy, the game's barber asks 5 groschen instead of 50, in its price.xml, and so does this one.
-- The mod is known by one of its files, which System.IsFileExist also finds inside the paks of mods. A token for a
-- moment tells ml_mf_barber.xml, and the price stays in its state.
MaleCore.LOW_PRICE_FILE = "Libs/Tables/item/item__realisheconomy.xml"

local function sendPrice()
	local found = try("barber price", function() return System.IsFileExist(MaleCore.LOW_PRICE_FILE) end)
	local low = found == true or found == 1
	sendToken(low and MaleCore.PRICE_LOW_TOKEN or MaleCore.PRICE_GAME_TOKEN)
	MaleCore.Log("barber price:", low and "5 groschen, with Realish Economy" or "50 groschen")
end

-- The pillory in Troskowitz dresses the player in Henry's hose and boots with an outfit of its own, which goes on the
-- model without the overrides of the face. The framework ships a copy of that scene, the same as KCD2 Female
-- Framework's, that gives the player SCENE_REBUILD_TOKEN when the outfit goes on and when it comes off. This takes it
-- while the character in use is not a woman of KCD2 Female Framework, which takes it then, and rebuilds the face if a
-- look is on.
local function sceneOutfit()
	local _, woman = pcall(function() return FemaleCore and FemaleCore.WomanInUse and FemaleCore.WomanInUse() end)
	if woman then
		return
	end
	local found = count(MaleCore.SCENE_REBUILD_TOKEN)
	if found <= 0 then
		return
	end
	try("token", function() player.inventory:DeleteItemOfClass(MaleCore.SCENE_REBUILD_TOKEN, found) end)
	if MaleCore.ModelInUse() then
		MaleCore.Log("an outfit of a scene changed: rebuild")
		rebuild()
	end
end

-- Once a second, for the barber, the outfit of a scene and Henry's doubles in the cutscenes (cutscene_doubles.lua): one
-- chain per load, and the one before stops on its own.
MaleCore.TICK_MS = 1000
local tickGen = 0

local function startTick()
	tickGen = tickGen + 1
	local gen = tickGen
	local function tick()
		if gen == tickGen then
			try("barber tick", MaleCore.Barber.Update)
			if MaleCore.SCENE_REBUILD_TOKEN then
				try("scene outfit", sceneOutfit)
			end
			if MaleCore.CutsceneDoubles then
				try("cutscene doubles", MaleCore.CutsceneDoubles)
			end
			Script.SetTimer(MaleCore.TICK_MS, tick)
		end
	end
	Script.SetTimer(MaleCore.TICK_MS, tick)
end

-- Before removing the framework: Henry gets his own face back, and nothing of the framework stays in his soul.
function MaleCore.Uninstall()
	MaleCore.Log("uninstall: once Henry's face is back, save and remove the mod")
	MaleCore.Henry()
end

-- The look goes off, with no rebuild, and hair and beard stay: for KCD2 Female Framework, before Henry becomes a woman.
function MaleCore.TakeOff()
	if MaleCore.Current() > 0 then
		MaleCore.Log("look taken off")
		sendToken(MaleCore.RESET_TOKEN)
		setCurrent(0)
	end
end

-- A look chosen before the game starts: from the console of the main menu before New Game, or by another mod.
-- The game tells no new game from a load (only OnGameplayStarted), so it goes on at the next start of the game, new
-- or loaded, once the framework knows his state. START_WAIT_MS more lets the start of a new game settle.
MaleCore.START_WAIT_MS = 2000
MaleCore.startLook = nil
-- A new game begins with Godwin, in Kuttenberg, on the first day of the world; Henry's part begins on the second, in
-- Trosecko, after a cutscene (kcd.log of 2026-11-09: world day 1, then 2). The soul of the player cannot be told from
-- Lua (soul:GetId is a runtime WUID), so the day tells it, and the look waits while it is the first.
MaleCore.HENRY_FIRST_DAY = 2
-- Only Engine/Config/CVarOverrides/Cutscene.cfg sets this cvar, to 1, while a cutscene plays: the look waits for its
-- end, so it goes on once Henry is in the saddle.
MaleCore.CUTSCENE_CVAR = "e_SkipInFrustumOptimizationWH"
MaleCore.CUTSCENE_POLL_MS = 1000
local startGen = 0

-- name: a look, by name or id. nil, "" or "none" cancels it. Returns whether the look exists.
function MaleCore.StartAs(name, hair, beard)
	if name == nil or name == "" or name == "none" then
		MaleCore.startLook, MaleCore.startParts = nil, nil
		MaleCore.Log("no look waits for the next start of the game")
		return true
	end
	local look = find(name)
	if not look then
		MaleCore.Log("no look called", name, "- ml_mf_looks lists them")
		return false
	end
	-- With a hair or a beard of its own, checked now, so the log says at once if one does not fit.
	hair, beard = partsOf(look, hair, beard)
	MaleCore.startLook, MaleCore.startParts = look.name, { hair = hair, beard = beard }
	MaleCore.Log("the next game that starts or loads begins with the face of", look.name, "hair", hair, "beard", beard)
	return true
end

-- The look that waits for the next start of the game, or nil.
function MaleCore.StartLook()
	return MaleCore.startLook
end

local function inCutscene()
	local value = try("cutscene", System.GetCVar, MaleCore.CUTSCENE_CVAR)
	return tonumber(value) == 1
end

local function applyStartLook()
	local name = MaleCore.startLook
	if not name then
		return
	end
	local day = try("calendar", Calendar.GetWorldDay)
	if day and day < MaleCore.HENRY_FIRST_DAY then
		MaleCore.Log("world day", day, "- the prologue with Godwin: the look waits for Henry")
		return
	end
	local parts = MaleCore.startParts or {}
	MaleCore.startLook, MaleCore.startParts = nil, nil
	local gen, waited = startGen, false
	local function attempt()
		-- Another save loaded meanwhile: the look waits for that one.
		if gen ~= startGen then
			if not MaleCore.startLook then
				MaleCore.startLook, MaleCore.startParts = name, parts
			end
			return
		end
		if inCutscene() then
			if not waited then
				waited = true
				MaleCore.Log("a cutscene plays: the look waits for its end")
			end
			Script.SetTimer(MaleCore.CUTSCENE_POLL_MS, attempt)
			return
		end
		MaleCore.Log("look chosen before the start:", name)
		try("start look", function() MaleCore.SetLook(name, nil, parts.hair, parts.beard) end)
	end
	Script.SetTimer(MaleCore.START_WAIT_MS, attempt)
end

-- The overrides need a rebuild after every load and every map, or the model shows Henry's head again. The inventory is
-- read a moment later: right at the start of the game it may not be there yet.
MaleCore.LOAD_WAIT_MS = 3000

-- Ready once the look of the save is known and the model rebuilt with it. A command or a change of the other framework
-- in the seconds before met the look of the save before: a face went on while KCD2 Female Framework did not know
-- yet that she was a woman, and a double made during the rebuild came out with no beard.
local ready = false

function MaleCore.Ready()
	return ready
end

function MaleCore:OnGameplayStarted()
	MaleCore.Log("gameplay started")
	ready = false
	startGen = startGen + 1
	-- A load in the middle of a change.
	hideScreen()
	-- What memory has may belong to the save before.
	setCurrent(0)
	try("barber forget", MaleCore.Barber.Forget)
	startTick()
	Script.SetTimer(MaleCore.LOAD_WAIT_MS, function()
		local old = count(MaleCore.OLD_STATE_ITEM)
		if old > 0 then
			try("token", function() player.inventory:DeleteItemOfClass(MaleCore.OLD_STATE_ITEM, old) end)
		end
		sendPrice()
		askCurrent(function(current)
			MaleCore.Log("look on load", current)
			local function done()
				ready = true
				MaleCore.Log("ready")
			end
			if current > 0 then
				rebuild(nil, nil, done)
			else
				done()
			end
			applyStartLook()
		end)
	end)
end

-- Rebuilds the model with what the character wears now, for when the face does not show. KCD2 Life calls it for its own
-- character after every load and every map.
function MaleCore.Refresh()
	MaleCore.Log("refresh, look", MaleCore.Current())
	rebuild()
end

-- Console

local function words(line)
	local list = {}
	local text = tostring(line or ""):gsub('^%s*"?', ""):gsub('"?%s*$', "")
	for word in text:gmatch("%S+") do
		list[#list + 1] = word
	end
	return list
end

-- A last word true leaves out the black screen, like ml_mf_look man_czech_2 true.
local function noScreenWord(list)
	if list[#list] == "true" then
		table.remove(list)
		return true
	end
	return false
end

-- A command of the console changes the model only in the game itself, with no inventory, map or menu open: a
-- change started under them breaks. Those screens pause the game, and a timer of the game waits while it is paused
--, so the change starts once the game runs again.
MaleCore.IN_GAME_MS = 500
-- And once both frameworks know the look of the save and rebuilt with it. If that never comes, after this long
-- it starts anyway.
MaleCore.READY_WAIT_MS = 30000

local function bothReady()
	local ok, other = pcall(function() return not (FemaleCore and FemaleCore.Ready) or FemaleCore.Ready() end)
	return ready and (not ok or other == true)
end

local function inGame(label, fn)
	local asked = try("clock", System.GetCurrAsyncTime)
	MaleCore.Log(label .. ": it starts in the game, once no inventory, map or menu is open, and the look of the save is on")
	local waited, told = 0, false
	local function attempt()
		if not bothReady() and waited < MaleCore.READY_WAIT_MS then
			if not told then
				told = true
				MaleCore.Log(label, "waits for the look of the save")
			end
			waited = waited + MaleCore.IN_GAME_MS
			Script.SetTimer(MaleCore.IN_GAME_MS, attempt)
			return
		end
		-- In real time: much more than IN_GAME_MS means the game was paused.
		local now = try("clock", System.GetCurrAsyncTime)
		if asked and now then
			MaleCore.Log(label, "starts after", string.format("%.1f", now - asked), "s")
		end
		try(label, fn)
	end
	Script.SetTimer(MaleCore.IN_GAME_MS, attempt)
end

-- Each look, and after it the characters of the game who wear its face.
function MaleCore.PrintLooks()
	for _, look in ipairs(MaleCore.ListLooks()) do
		local line = string.format("%s: man, %s, %s, id %d", look.name, look.ethnicity or "named character", look.age, look.id)
		if #look.characters > 0 then
			line = line .. " - " .. table.concat(look.characters, ", ")
		end
		System.LogAlways(line)
	end
end

-- After the look, a hair and a beard of the game, by their names and in any order, as LOOKS.md gives them for each
-- character: ml_mf_look man_czech_28 m_hair_009_dark_brown m_beard_00. A word that is neither is said in the log.
local function hairAndBeard(list)
	local hair, beard
	for i = 2, #list do
		local word = list[i]
		if word:find("^m_beard_") then
			beard = word
		elseif word:find("_hair_") then
			hair = word
		else
			MaleCore.Log("not a hair or a beard of the game, left out:", word)
		end
	end
	return hair, beard
end

function MaleCore.LookCommand(line)
	local list = words(line)
	local noScreen = noScreenWord(list)
	local hair, beard = hairAndBeard(list)
	inGame("ml_mf_look", function() MaleCore.SetLook(list[1], noScreen, hair, beard) end)
end

function MaleCore.RandomCommand(line)
	local noScreen = noScreenWord(words(line))
	inGame("ml_mf_random", function() MaleCore.SetRandomLook(noScreen) end)
end

function MaleCore.HenryCommand(line)
	local noScreen = noScreenWord(words(line))
	inGame("ml_mf_henry", function() MaleCore.Henry(noScreen) end)
end

function MaleCore.RefreshCommand()
	inGame("ml_mf_refresh", MaleCore.Refresh)
end

function MaleCore.UninstallCommand()
	inGame("ml_mf_uninstall", MaleCore.Uninstall)
end

-- It only remembers the look, so it works in the main menu too. With no look, it says which one waits.
function MaleCore.StartCommand(line)
	local list = words(line)
	if not list[1] then
		MaleCore.Log("look for the next start of the game:", MaleCore.startLook or "none")
		return
	end
	MaleCore.StartAs(list[1], hairAndBeard(list))
end

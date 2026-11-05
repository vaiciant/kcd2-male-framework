-- =============================================================================
-- MaleCore: the API of KCD2 Male Framework (MODDING.md). It puts the face of a look on
-- Henry himself, and takes it away, with no other mod. Head and body are overrides of
-- ml_mf_face.xml, picked with a token given to Henry. Hair and beard go on his soul with
-- the native Barber object, as the barbers of the game do. The model only shows the
-- overrides after a rebuild, which a real beard change forces.
-- =============================================================================
MaleCore = MaleCore or {}

MaleCore.API = 1
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

local function setCurrent(id)
	MaleCore.current = id
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
local function copy(look)
	return look and { id = look.id, name = look.name, ethnicity = look.ethnicity, age = look.age, villager = look.villager, soul = look.soul }
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

-- Henry takes the face of that look: a name or an id. Without one, the first look. noScreen true leaves out the black
-- screen.
function MaleCore.SetLook(name, noScreen)
	if notHenry() then
		return false
	end
	local look = name and find(name) or MaleCore.LOOKS[1]
	if not look then
		MaleCore.Log("no look called", name, "- ml_mf_looks lists them")
		return false
	end
	MaleCore.Log("look", look.name, "id", look.id)
	showScreen(noScreen)
	try("barber forget", MaleCore.Barber.Forget)
	-- The beard of the head of now may not exist on the next one.
	withBarber("safe beard", function(barber) barber:TryBeard(MaleCore.SAFE_BEARD) end)
	sendToken(MaleCore.RESET_TOKEN)
	Script.SetTimer(MaleCore.TOKEN_MS + 200, function()
		sendToken(look.token)
		setCurrent(look.id)
		Script.SetTimer(MaleCore.TOKEN_MS + 200, function() rebuild(look.hair, look.beard, hideScreen) end)
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

-- Once a second, for the barber: one chain per load, and the one before stops on its own.
MaleCore.TICK_MS = 1000
local tickGen = 0

local function startTick()
	tickGen = tickGen + 1
	local gen = tickGen
	local function tick()
		if gen == tickGen then
			try("barber tick", MaleCore.Barber.Update)
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

-- The overrides need a rebuild after every load and every map, or the model shows Henry's head again. The inventory is
-- read a moment later: right at the start of the game it may not be there yet.
MaleCore.LOAD_WAIT_MS = 3000

function MaleCore:OnGameplayStarted()
	MaleCore.Log("gameplay started")
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
			if current > 0 then
				rebuild()
			end
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

local function inGame(label, fn)
	local asked = try("clock", System.GetCurrAsyncTime)
	MaleCore.Log(label .. ": it starts in the game, once no inventory, map or menu is open")
	Script.SetTimer(MaleCore.IN_GAME_MS, function()
		-- In real time: much more than IN_GAME_MS means the game was paused.
		local now = try("clock", System.GetCurrAsyncTime)
		if asked and now then
			MaleCore.Log(label, "starts after", string.format("%.1f", now - asked), "s")
		end
		try(label, fn)
	end)
end

function MaleCore.PrintLooks()
	for _, look in ipairs(MaleCore.ListLooks()) do
		System.LogAlways(string.format("%s: man, %s, %s, id %d", look.name, look.ethnicity or "named character", look.age, look.id))
	end
end

function MaleCore.LookCommand(line)
	local list = words(line)
	local noScreen = noScreenWord(list)
	inGame("ml_mf_look", function() MaleCore.SetLook(list[1], noScreen) end)
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

-- =============================================================================
-- A man's haircut at the barbers of the game with a look of the framework: Fiala, Adam, Betty and any NPC with the role
-- BARBER. The screen of the game shows one list to every head, and its beards, or those of other mods, may not
-- exist for the head of the look: one missing has crashed the game. So he chooses in the talk (ml_mf_barber_dialog.xml),
-- as a woman does with KCD2 Female Framework: a hair and a beard of barber.toml. Each one named tries it on his soul, so
-- it shows at once, and only Accept keeps it. With his own face, Henry goes to the screen of the game, with its list
-- whole.
-- =============================================================================
MaleCore.Barber = {}
local Shop = MaleCore.Barber

Shop.MODEL_VARIABLE = "ml_mf_model"
-- The menus hide what he has on now. 0 hides nothing: after a load, the framework does not know his hair.
Shop.HAIR_VARIABLE = "ml_mf_hair"
Shop.BEARD_VARIABLE = "ml_mf_beard"

local session
-- What he chose last, by its place in MaleCore.BARBER_HAIRS and MaleCore.BARBER_BEARDS. Memory only.
local chosen = {}
local hair
local beard

local function try(label, fn)
	local ok, result = pcall(fn)
	if not ok then
		MaleCore.Log("ERROR", label, result)
		return nil
	end
	return result
end

local function publish()
	Variables.SetGlobal(Shop.HAIR_VARIABLE, hair or 0)
	Variables.SetGlobal(Shop.BEARD_VARIABLE, beard or 0)
end

local function close(finish)
	try("barber close", function()
		finish(session)
		Barber:Destroy(session)
	end)
	session = nil
end

function Shop.Open()
	session = try("barber", function() return Barber:Create(player.soul) end)
	hair, beard = chosen.hair, chosen.beard
	publish()
end

function Shop.Hair(index)
	hair = index
	publish()
	try("barber hair", function() session:TryHair(MaleCore.BARBER_HAIRS[index]) end)
end

function Shop.Beard(index)
	beard = index
	publish()
	try("barber beard", function() session:TryBeard(MaleCore.BARBER_BEARDS[index]) end)
end

function Shop.Accept()
	close(function(barber) barber:Commit() end)
	chosen.hair, chosen.beard = hair or chosen.hair, beard or chosen.beard
	MaleCore.Log("barber", hair and MaleCore.BARBER_HAIRS[hair], beard and MaleCore.BARBER_BEARDS[beard])
end

function Shop.Cancel()
	close(function(barber) barber:Revert() end)
end

-- A new look, or a load: what he chose before is not known any more.
function Shop.Forget()
	chosen = {}
end

-- Variables are lost on a region change, so the tick sets them every second. A talk cut short must not leave the hair on
-- trial.
function Shop.Update()
	Variables.SetGlobal(Shop.MODEL_VARIABLE, MaleCore.ModelInUse() and 1 or 0)
	if session and not try("barber dialog", function() return player.human:IsInDialog() end) then
		Shop.Cancel()
	end
end

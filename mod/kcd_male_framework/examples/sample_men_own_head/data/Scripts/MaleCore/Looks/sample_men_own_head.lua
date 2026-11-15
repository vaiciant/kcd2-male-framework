-- Written by make_face_pack.py of KCD2 Male Framework from faces.toml: the faces of sample_men_own_head.
-- The framework reads every file of Scripts/MaleCore/Looks and keeps these with its own looks.
if not (MaleCore and MaleCore.RegisterLooks) then
	System.LogAlways("[sample_men_own_head] this version of KCD2 Male Framework has no RegisterLooks: these faces need a newer one")
	return
end
MaleCore.RegisterLooks("sample_men_own_head", {
	{ id = 1030, name = "sample_own_man", hair = "m_hair_009_dark_brown", beard = "m_beard_13", age = "young", token = "62c2bc66-12b1-5481-a844-f9863adff620", beards = { "m_beard_00", "m_beard_01", "m_beard_02", "m_beard_03", "m_beard_04", "m_beard_05", "m_beard_06", "m_beard_07", "m_beard_08", "m_beard_09", "m_beard_10", "m_beard_11", "m_beard_12", "m_beard_13", "m_beard_14", "m_beard_15", "m_beard_16", "m_beard_17", "m_beard_18", "m_beard_19" } },
})

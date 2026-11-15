-- Written by make_face_pack.py of KCD2 Male Framework from faces.toml: the faces of sample_men_faces.
-- The framework reads every file of Scripts/MaleCore/Looks and keeps these with its own looks.
if not (MaleCore and MaleCore.RegisterLooks) then
	System.LogAlways("[sample_men_faces] this version of KCD2 Male Framework has no RegisterLooks: these faces need a newer one")
	return
end
MaleCore.RegisterLooks("sample_men_faces", {
	{ id = 1050, name = "sample_bearded", hair = "m_hair_009_dark_brown", beard = "m_beard_04", age = "young", token = "a00fe80e-43ad-56e4-ba55-9219e423aeda", beards = { "m_beard_00", "m_beard_01", "m_beard_02", "m_beard_03", "m_beard_04", "m_beard_05", "m_beard_06", "m_beard_07", "m_beard_08", "m_beard_09", "m_beard_10", "m_beard_11", "m_beard_12", "m_beard_13", "m_beard_14", "m_beard_15", "m_beard_16", "m_beard_17", "m_beard_18", "m_beard_19" } },
	{ id = 1051, name = "sample_shaven", hair = "m_hair_002_dark_ginger", beard = "m_beard_00", age = "young", token = "30cb5d3f-e170-5524-a3e3-7ed09757ce3f", beards = { "m_beard_00", "m_beard_01", "m_beard_02", "m_beard_03", "m_beard_04", "m_beard_05", "m_beard_06", "m_beard_07", "m_beard_08", "m_beard_09", "m_beard_10", "m_beard_11", "m_beard_12", "m_beard_13", "m_beard_14", "m_beard_15", "m_beard_16", "m_beard_17", "m_beard_18", "m_beard_19" } },
})

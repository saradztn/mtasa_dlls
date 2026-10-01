GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
G4.Surfaces = {
    definitions = {
        asphalt = { traction = 1.00, brakingGrip = 1.00, rollingResistance = 0.012 },
        concrete = { traction = 0.96, brakingGrip = 0.98, rollingResistance = 0.014 },
        grass = { traction = 0.62, brakingGrip = 0.58, rollingResistance = 0.055 },
        dirt = { traction = 0.72, brakingGrip = 0.66, rollingResistance = 0.048 },
        sand = { traction = 0.56, brakingGrip = 0.49, rollingResistance = 0.090 },
        wet_asphalt = { traction = 0.72, brakingGrip = 0.63, rollingResistance = 0.018 },
        mud = { traction = 0.48, brakingGrip = 0.40, rollingResistance = 0.105 }
    },
    adhesionGroups = { road = "asphalt", hard = "concrete", loose = "dirt", sand = "sand", wet = "wet_asphalt", rubber = "asphalt" },
    fallback = "asphalt"
}
local function safeProperty(material, property)
    if type(engineGetSurfaceProperties) ~= "function" or type(material) ~= "number" then return nil end
    local ok, value = pcall(engineGetSurfaceProperties, material, property)
    return ok and value or nil
end
function G4.Surfaces.resolve(material, rainLevel)
    local group = safeProperty(material, "adhesiongroup")
    local wheelEffect = tostring(safeProperty(material, "wheeleffect") or ""):lower()
    local name = G4.Surfaces.adhesionGroups[tostring(group or ""):lower()] or G4.Surfaces.fallback
    if wheelEffect == "grass" then name = "grass"
    elseif wheelEffect == "mud" then name = "mud"
    elseif wheelEffect == "sand" then name = "sand"
    elseif wheelEffect == "gravel" or wheelEffect == "dust" then name = "dirt" end
    local result = G4.copyTable(G4.Surfaces.definitions[name] or G4.Surfaces.definitions.asphalt)
    result.name, result.material, result.adhesionGroup = name, material, group
    local nativeGrip = tonumber(safeProperty(material, "tyregrip"))
    if nativeGrip and nativeGrip > 0 then result.traction = result.traction * G4.Math.clamp(nativeGrip / 128, 0.60, 1.35) end
    local rain = G4.Math.clamp(tonumber(rainLevel) or 0, 0, 1)
    if name == "asphalt" or name == "concrete" or name == "wet_asphalt" then
        local wetGrip = tonumber(safeProperty(material, "wetgrip"))
        local wetScale = wetGrip and wetGrip > 0 and G4.Math.clamp(wetGrip / 128, 0.45, 1.05) or 0.66
        local wetness = rain * 0.72
        result.traction = result.traction * (1 - wetness + wetness * wetScale)
        result.brakingGrip = result.brakingGrip * (1 - wetness + wetness * wetScale * 0.92)
        if rain > 0.08 then result.name = "wet_asphalt" end
    end
    return result
end

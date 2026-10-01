GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
local classes = G4.VehicleClasses and G4.VehicleClasses.defaults or {}
local function clone(source) return G4.copyTable(source) end
local function applyScale(value, scale) return value * (scale or 1) end

-- Estimates only. Each row supplies model-specific multipliers/geometry; expansion
-- yields an editable, fully populated record rather than a shared class object.
local catalog = {
    {400,"Landstalker","suv",1.03,0.91,0.97,0.88,2.78,1.68,"AWD",0.59,1.03},{401,"Bravura","compact",0.94,0.88,0.93,0.86,2.46,1.49,"FWD",0.62,0.98},{402,"Buffalo","muscle",0.98,1.10,1.00,1.04,2.72,1.60,"RWD",0.53,1.02},{403,"Linerunner","truck",2.70,1.22,0.82,0.61,5.20,2.05,"RWD",0.37,1.28},{404,"Pereniel","sedan",0.98,0.92,0.97,0.89,2.63,1.51,"FWD",0.60,0.98},{405,"Sentinel","sedan",1.01,1.03,1.01,0.98,2.70,1.54,"RWD",0.55,1.00},{406,"Dumper","truck",4.90,1.50,0.72,0.38,6.10,2.44,"RWD",0.36,1.58},{407,"Firetruck","truck",3.05,1.25,0.89,0.69,4.75,2.08,"RWD",0.41,1.24},{408,"Trashmaster","truck",2.45,1.13,0.80,0.58,4.25,2.00,"RWD",0.43,1.32},{409,"Stretch","sedan",1.40,0.92,0.90,0.82,3.68,1.64,"RWD",0.53,1.08},
    {410,"Manana","compact",0.91,0.76,0.90,0.76,2.36,1.42,"RWD",0.55,1.01},{411,"Infernus","super",0.92,1.23,1.08,1.25,2.58,1.70,"RWD",0.43,0.94},{412,"Voodoo","muscle",1.05,0.89,0.86,0.83,2.86,1.60,"RWD",0.55,1.12},{413,"Pony","van",0.91,0.88,0.92,0.80,2.95,1.58,"FWD",0.62,1.10},{414,"Mule","truck",1.36,0.90,0.84,0.70,3.62,1.91,"RWD",0.43,1.25},{415,"Cheetah","super",0.87,1.18,1.06,1.19,2.55,1.68,"RWD",0.44,0.91},{416,"Ambulance","van",1.04,1.04,0.95,0.90,3.10,1.66,"RWD",0.58,1.18},{418,"Moonbeam","van",0.94,0.85,0.91,0.78,2.72,1.58,"FWD",0.60,1.09},{419,"Esperanto","coupe",1.04,0.85,0.89,0.79,2.75,1.53,"RWD",0.57,1.06},{420,"Taxi","sedan",1.00,0.96,0.97,0.91,2.72,1.55,"RWD",0.57,1.00},
    {421,"Washington","sedan",1.04,0.94,0.99,0.90,2.78,1.56,"RWD",0.58,1.02},{422,"Bobcat","offroad",1.03,0.91,0.98,0.85,2.75,1.61,"RWD",0.55,1.18},{423,"Mr Whoopee","van",0.88,0.70,0.82,0.66,2.66,1.54,"RWD",0.58,1.16},{424,"BF Injection","offroad",0.72,0.80,0.97,0.94,2.25,1.55,"RWD",0.42,1.18},{426,"Premier","sedan",0.99,0.99,1.00,0.94,2.67,1.54,"FWD",0.62,0.98},{427,"Enforcer","van",1.28,1.00,0.91,0.79,3.06,1.69,"RWD",0.56,1.16},{428,"Securicar","van",1.47,1.00,0.88,0.76,3.21,1.73,"RWD",0.57,1.23},{429,"Banshee","sports",0.91,1.12,1.02,1.12,2.58,1.64,"RWD",0.48,0.95},{431,"Bus","bus",0.93,0.86,0.89,0.70,5.72,2.06,"RWD",0.40,1.06},{433,"Barracks","truck",1.82,1.08,0.96,0.72,4.16,2.02,"AWD",0.43,1.18},
    {434,"Hotknife","muscle",0.88,0.90,0.88,0.84,2.62,1.55,"RWD",0.55,1.08},{436,"Previon","coupe",0.94,0.93,0.95,0.91,2.48,1.50,"FWD",0.62,0.97},{437,"Coach","bus",1.02,0.96,0.94,0.78,6.02,2.09,"RWD",0.41,1.08},{438,"Cabbie","sedan",1.01,0.81,0.88,0.78,2.68,1.54,"RWD",0.55,1.04},{439,"Stallion","muscle",0.95,1.02,0.96,0.98,2.66,1.59,"RWD",0.52,1.00},{440,"Rumpo","van",0.98,0.91,0.94,0.82,2.98,1.62,"RWD",0.57,1.11},{442,"Romero","sedan",1.26,0.83,0.87,0.73,3.05,1.61,"RWD",0.56,1.13},{443,"Packer","truck",2.08,1.10,0.82,0.58,4.84,2.06,"RWD",0.38,1.34},{444,"Monster","offroad",1.42,1.18,0.90,0.72,3.18,2.12,"AWD",0.49,1.36},{445,"Admiral","sedan",0.98,0.94,0.96,0.90,2.72,1.53,"RWD",0.56,1.01},
    {451,"Turismo","super",0.89,1.25,1.09,1.23,2.62,1.72,"RWD",0.44,0.92},{455,"Flatbed","truck",2.18,1.08,0.85,0.62,4.52,2.05,"RWD",0.40,1.31},{456,"Yankee","truck",1.62,0.94,0.83,0.68,3.82,1.96,"RWD",0.43,1.25},{457,"Caddy","compact",0.72,0.54,0.74,0.48,1.72,1.11,"RWD",0.49,0.88},{458,"Solair","sedan",1.02,0.91,0.94,0.86,2.76,1.54,"FWD",0.61,1.04},{459,"Topfun","van",1.08,0.93,0.90,0.79,3.04,1.68,"RWD",0.57,1.14},{461,"PCJ-600","motorcycle",0.96,1.05,1.00,1.05,1.43,0.38,"RWD",0.48,0.99},{462,"Faggio","motorcycle",0.78,0.43,0.72,0.45,1.21,0.31,"RWD",0.54,1.05},{463,"Freeway","motorcycle",1.16,0.72,0.89,0.75,1.62,0.43,"RWD",0.50,1.08},{466,"Glendale","sedan",1.02,0.82,0.89,0.80,2.71,1.53,"RWD",0.55,1.07},
    {467,"Oceanic","sedan",1.05,0.81,0.87,0.78,2.82,1.54,"RWD",0.55,1.10},{468,"Sanchez","motorcycle",0.89,0.68,0.95,0.89,1.46,0.41,"RWD",0.46,1.06},{470,"Patriot","offroad",1.23,0.96,1.02,0.80,2.94,1.74,"AWD",0.51,1.19},{471,"Quad","offroad",1.08,0.58,0.95,0.66,1.28,0.94,"AWD",0.50,1.11},{474,"Hermes","muscle",1.03,0.84,0.86,0.79,2.69,1.59,"RWD",0.55,1.08},{475,"Sabre","muscle",1.00,1.03,0.95,0.98,2.71,1.61,"RWD",0.52,1.00},{477,"ZR-350","sports",0.89,1.12,1.02,1.09,2.57,1.62,"RWD",0.47,0.96},{478,"Walton","offroad",0.91,0.78,0.94,0.74,2.63,1.52,"RWD",0.55,1.17},{479,"Regina","sedan",1.05,0.80,0.89,0.75,2.78,1.55,"RWD",0.56,1.08},{480,"Comet","sports",0.90,1.12,1.03,1.10,2.43,1.62,"RWD",0.41,0.94},
    {482,"Burrito","van",1.01,0.90,0.91,0.81,3.02,1.65,"RWD",0.57,1.12},{483,"Camper","van",1.30,0.78,0.80,0.63,3.34,1.73,"RWD",0.57,1.22},{489,"Rancher","suv",1.08,0.91,0.99,0.83,2.83,1.69,"AWD",0.55,1.10},{490,"FBI Rancher","suv",1.14,1.05,1.00,0.91,2.84,1.72,"AWD",0.54,1.14},{491,"Virgo","coupe",0.99,0.84,0.90,0.80,2.63,1.51,"RWD",0.56,1.03},{492,"Greenwood","sedan",1.06,0.81,0.88,0.76,2.77,1.55,"RWD",0.57,1.08},{494,"Hotring Racer","sports",0.83,1.24,1.06,1.20,2.61,1.69,"RWD",0.48,0.91},{495,"Sandking","offroad",1.11,1.03,1.08,0.90,2.93,1.78,"AWD",0.51,1.20},{496,"Blista Compact","compact",0.90,0.98,1.00,0.98,2.42,1.48,"FWD",0.63,0.95},{498,"Boxville","van",1.15,0.89,0.87,0.72,3.18,1.71,"RWD",0.58,1.20},
    {499,"Benson","truck",1.72,0.93,0.81,0.63,3.92,1.97,"RWD",0.43,1.29},{500,"Mesa","offroad",0.88,0.84,0.99,0.84,2.53,1.55,"AWD",0.54,1.06},{502,"Hotring Racer A","sports",0.81,1.25,1.06,1.22,2.60,1.70,"RWD",0.48,0.90},{503,"Hotring Racer B","sports",0.82,1.22,1.04,1.19,2.60,1.69,"RWD",0.48,0.91},{504,"Bloodring Banger","muscle",1.04,0.97,0.88,0.88,2.72,1.61,"RWD",0.53,1.10},{505,"Rancher Lure","offroad",1.05,0.88,0.98,0.81,2.80,1.67,"AWD",0.55,1.12},{506,"Super GT","sports",0.91,1.17,1.05,1.16,2.62,1.66,"RWD",0.47,0.94},{507,"Elegant","sedan",1.00,0.97,0.98,0.92,2.74,1.54,"RWD",0.56,1.01},{508,"Journey","van",1.35,0.65,0.76,0.51,3.40,1.76,"RWD",0.58,1.24},
    {514,"Tanker","truck",2.34,1.04,0.80,0.55,4.95,2.08,"RWD",0.39,1.40},{515,"Roadtrain","truck",2.95,1.34,0.83,0.66,5.72,2.17,"RWD",0.37,1.45},{516,"Nebula","sedan",0.98,0.92,0.96,0.87,2.66,1.52,"RWD",0.56,1.00},{517,"Majestic","coupe",0.98,0.91,0.95,0.88,2.59,1.52,"RWD",0.54,1.00},{518,"Buccaneer","muscle",1.01,0.96,0.91,0.91,2.74,1.61,"RWD",0.53,1.06},{521,"FCR-900","motorcycle",0.93,1.03,0.99,1.04,1.42,0.39,"RWD",0.47,0.97},{522,"NRG-500","motorcycle",0.87,1.31,1.05,1.30,1.40,0.39,"RWD",0.46,0.94},{523,"HPV-1000","motorcycle",1.04,0.94,0.95,0.92,1.48,0.40,"RWD",0.49,1.01},
    {524,"Cement Truck","truck",2.36,0.92,0.79,0.48,4.74,2.08,"RWD",0.42,1.44},{525,"Towtruck","truck",1.34,0.92,0.86,0.69,3.86,1.94,"RWD",0.43,1.26},{526,"Fortune","coupe",0.96,0.98,0.97,0.95,2.59,1.51,"RWD",0.52,0.99},{527,"Cadrona","compact",0.92,0.89,0.93,0.87,2.49,1.48,"FWD",0.62,0.97},{528,"FBI Truck","van",1.27,1.08,0.94,0.89,3.08,1.70,"RWD",0.55,1.17},{529,"Willard","sedan",0.97,0.89,0.93,0.85,2.63,1.51,"RWD",0.55,1.01},
    {533,"Feltzer","sports",0.93,1.01,1.01,1.00,2.64,1.60,"RWD",0.50,0.97},{534,"Remington","muscle",0.99,0.90,0.88,0.87,2.72,1.60,"RWD",0.53,1.09},{535,"Slamvan","muscle",1.12,0.96,0.90,0.83,2.90,1.65,"RWD",0.52,1.16},{536,"Blade","muscle",0.96,1.00,0.93,0.94,2.68,1.58,"RWD",0.51,1.03},{540,"Vincent","sedan",1.00,0.96,0.98,0.92,2.69,1.54,"FWD",0.61,1.01},{541,"Bullet","super",0.85,1.27,1.08,1.27,2.55,1.70,"RWD",0.43,0.90},{542,"Clover","muscle",0.91,0.91,0.88,0.86,2.63,1.56,"RWD",0.53,1.08},{543,"Sadler","offroad",0.94,0.88,0.94,0.82,2.68,1.58,"RWD",0.55,1.15},
    {545,"Hustler","muscle",1.12,0.86,0.81,0.72,2.80,1.61,"RWD",0.54,1.17},{546,"Intruder","sedan",0.99,0.89,0.94,0.87,2.68,1.52,"FWD",0.62,1.00},{547,"Primo","sedan",1.01,0.84,0.90,0.80,2.69,1.53,"FWD",0.62,1.04},{549,"Tampa","muscle",0.95,0.98,0.90,0.92,2.64,1.59,"RWD",0.52,1.02},{550,"Sunrise","sedan",0.99,0.91,0.96,0.88,2.63,1.51,"FWD",0.63,0.98},{551,"Merit","sedan",1.00,0.93,0.96,0.90,2.70,1.54,"RWD",0.56,1.00},{554,"Yosemite","offroad",1.12,0.97,0.99,0.83,2.92,1.68,"RWD",0.55,1.20},{555,"Windsor","coupe",1.04,0.97,0.96,0.93,2.76,1.55,"RWD",0.55,1.04},
    {558,"Uranus","sports",0.90,1.00,0.98,0.98,2.55,1.59,"FWD",0.61,0.97},{559,"Jester","sports",0.91,1.08,1.03,1.06,2.57,1.61,"RWD",0.48,0.96},{560,"Sultan","sports",0.98,1.13,1.06,1.07,2.67,1.62,"AWD",0.53,0.97},{561,"Stratum","sedan",1.04,0.97,0.98,0.91,2.70,1.54,"AWD",0.58,1.04},{562,"Elegy","sports",0.92,1.10,1.05,1.10,2.62,1.62,"RWD",0.48,0.95},{565,"Flash","compact",0.91,0.96,0.99,0.97,2.45,1.49,"FWD",0.63,0.95},{566,"Tahoma","sedan",1.01,0.91,0.92,0.86,2.74,1.56,"RWD",0.54,1.05},{567,"Savanna","muscle",1.01,0.93,0.91,0.89,2.77,1.59,"RWD",0.52,1.05},{568,"Bandito","offroad",0.77,0.82,0.98,0.88,2.20,1.55,"AWD",0.49,1.15},
    {575,"Broadway","muscle",1.05,0.83,0.87,0.80,2.82,1.60,"RWD",0.55,1.10},{576,"Tornado","muscle",1.02,0.86,0.88,0.83,2.72,1.58,"RWD",0.54,1.08},{579,"Huntley","suv",1.09,0.96,0.98,0.88,2.86,1.68,"AWD",0.55,1.09},{580,"Stafford","sedan",1.12,0.84,0.86,0.75,2.95,1.62,"RWD",0.56,1.10},{581,"BF-400","motorcycle",0.91,1.07,0.98,1.04,1.41,0.39,"RWD",0.47,0.98},{582,"Newsvan","van",1.04,0.91,0.90,0.80,3.04,1.66,"RWD",0.57,1.16},{584,"Petrol Tanker","truck",2.70,1.15,0.78,0.50,5.18,2.11,"RWD",0.38,1.51},{585,"Emperor","sedan",1.05,0.88,0.91,0.82,2.73,1.54,"RWD",0.56,1.05},{586,"Wayfarer","motorcycle",1.08,0.69,0.87,0.70,1.57,0.43,"RWD",0.50,1.07},{587,"Euros","sports",0.93,1.03,1.01,1.03,2.58,1.60,"RWD",0.49,0.97},{588,"Hotdog","van",1.11,0.74,0.83,0.70,3.11,1.68,"RWD",0.57,1.20},{589,"Club","compact",0.88,0.97,0.99,0.95,2.39,1.47,"FWD",0.63,0.94},
    {600,"Picador","muscle",0.97,0.88,0.89,0.83,2.72,1.60,"RWD",0.54,1.10},{601,"S.W.A.T.","truck",1.74,1.12,0.92,0.75,3.95,2.02,"AWD",0.48,1.22},{602,"Alpha","sports",0.94,1.02,1.00,1.00,2.64,1.61,"RWD",0.49,0.97},{603,"Phoenix","muscle",0.98,1.07,0.94,1.00,2.69,1.60,"RWD",0.50,0.99},{604,"Glendale Damaged","sedan",1.06,0.75,0.80,0.71,2.72,1.54,"RWD",0.55,1.12},{605,"Sadler Damaged","truck",1.06,0.78,0.78,0.65,3.12,1.82,"RWD",0.44,1.23},{609,"Boxville 2","van",1.12,0.85,0.85,0.72,3.21,1.72,"RWD",0.58,1.22}
}

local function expand(row)
    local id, name, category = row[1], row[2], row[3]
    local base = classes[category]
    if not base then return nil end
    local spec = G4.copyTable(base)
    local massScale, forceScale, gripScale, speedScale = row[4], row[5], row[6], row[7]
    local wheelbase, trackWidth, driveType, frontBias, dragScale = row[8], row[9], row[10], row[11], row[12]
    local variation = ((id * 7) % 13) * 0.004
    spec.name, spec.model, spec.class = name, id, category
    spec.mass = spec.mass * massScale
    spec.drag = spec.drag * dragScale
    spec.dimensions.wheelbase, spec.dimensions.trackWidth = wheelbase, trackWidth
    spec.dimensions.frontWeightBias = frontBias
    spec.dimensions.cgHeight = spec.dimensions.cgHeight * (0.98 + variation)
    spec.drivetrain.type = driveType
    spec.drivetrain.driveForce = spec.drivetrain.driveForce * forceScale
    spec.drivetrain.driveInertia = spec.drivetrain.driveInertia * (0.96 + variation * 2)
    spec.drivetrain.maxSpeed = spec.drivetrain.maxSpeed * speedScale
    spec.drivetrain.finalDrive = spec.drivetrain.finalDrive * (0.97 + variation * 2)
    spec.engine.peakTorqueNm = spec.engine.peakTorqueNm * forceScale * (0.99 + variation)
    spec.engine.inertia = spec.engine.inertia * (0.96 + variation * 2)
    spec.brakes.force = spec.brakes.force * massScale * (0.96 + variation)
    spec.brakes.bias = math.max(0.54, math.min(0.72, spec.brakes.bias + (frontBias - base.dimensions.frontWeightBias) * 0.12))
    spec.traction.max = spec.traction.max * gripScale * (0.985 + variation)
    spec.traction.min = spec.traction.min * gripScale * (0.975 + variation)
    spec.traction.bias = math.max(0.42, math.min(0.64, spec.traction.bias + (frontBias - base.dimensions.frontWeightBias) * 0.20))
    spec.suspension.force = spec.suspension.force * massScale * (0.96 + variation)
    spec.suspension.compression = spec.suspension.compression * massScale * (0.94 + variation)
    spec.suspension.rebound = spec.suspension.rebound * massScale * (0.98 + variation)
    spec.suspension.antiRoll = spec.suspension.antiRoll * massScale * (0.96 + variation)
    spec.suspension.bias = math.max(0.35, math.min(0.68, spec.suspension.bias + (frontBias - base.dimensions.frontWeightBias) * 0.14))
    spec.steering.lock = spec.steering.lock * (0.97 + variation * 2)
    spec.steering.inputRate = spec.steering.inputRate * (0.97 + variation)
    spec.bodyDynamics.rollDamping = spec.bodyDynamics.rollDamping * (0.96 + variation)
    spec.bodyDynamics.pitchDamping = spec.bodyDynamics.pitchDamping * (0.97 + variation)
    spec.bodyDynamics.maxRollDeg = spec.bodyDynamics.maxRollDeg * (0.97 + variation)
    spec.bodyDynamics.maxPitchDeg = spec.bodyDynamics.maxPitchDeg * (0.97 + variation)
    spec.bodyDynamics.rollRate = spec.bodyDynamics.rollRate * (0.98 + variation)
    spec.bodyDynamics.pitchRate = spec.bodyDynamics.pitchRate * (0.98 + variation)
    spec.bodyDynamics.yawGain = spec.bodyDynamics.yawGain * (0.97 + variation)
    spec.aero.dragArea = spec.aero.dragArea * dragScale
    spec.estimated = true
    spec.sourceNote = "Estimated class baseline with model-specific modifiers; no GTA IV handling.dat value is represented."
    return spec
end

G4.VehicleDatabase = { version = "0.1.0-estimated", sourceNote = "Every starting entry is an estimate, not recovered GTA IV handling.dat data.", vehicles = {}, modelNames = {} }
for _, row in ipairs(catalog) do
    local spec = expand(row)
    if spec then G4.VehicleDatabase.vehicles[spec.model] = spec; G4.VehicleDatabase.modelNames[string.lower(spec.name)] = spec.model end
end
function G4.VehicleDatabase.get(model) return G4.VehicleDatabase.vehicles[tonumber(model)] end
function G4.VehicleDatabase.count() local total = 0; for _ in pairs(G4.VehicleDatabase.vehicles) do total = total + 1 end; return total end

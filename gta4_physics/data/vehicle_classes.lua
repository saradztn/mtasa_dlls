GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics

-- Class baselines are starting points only. The model database expands them into
-- independent editable records and marks every value estimated=true.
G4.VehicleClasses = {
    definitions = {
        compact = { label = "Compact", wheelCount = 4, typicalMass = { 850, 1250 } },
        sedan = { label = "Sedan", wheelCount = 4, typicalMass = { 1150, 1900 } },
        coupe = { label = "Coupe", wheelCount = 4, typicalMass = { 1050, 1750 } },
        sports = { label = "Sports", wheelCount = 4, typicalMass = { 1150, 1750 } },
        super = { label = "Super", wheelCount = 4, typicalMass = { 1250, 1900 } },
        muscle = { label = "Muscle", wheelCount = 4, typicalMass = { 1250, 2100 } },
        suv = { label = "SUV", wheelCount = 4, typicalMass = { 1650, 2700 } },
        offroad = { label = "Off-road", wheelCount = 4, typicalMass = { 1350, 2900 } },
        van = { label = "Van", wheelCount = 4, typicalMass = { 1500, 3400 } },
        truck = { label = "Truck", wheelCount = 4, typicalMass = { 2800, 14000 } },
        bus = { label = "Bus/coach", wheelCount = 4, typicalMass = { 7500, 15000 } },
        motorcycle = { label = "Motorcycle", wheelCount = 2, typicalMass = { 150, 420 } }
    },
    defaults = {
        compact = {
            mass = 1080, drag = 0.68, centerOfMass = { 0.00, 0.02, -0.12 },
            dimensions = { wheelbase = 2.43, trackWidth = 1.47, wheelRadius = 0.30, wheelInertia = 1.05, frontWeightBias = 0.61, cgHeight = 0.49 },
            drivetrain = { type = "FWD", gears = 5, gearRatios = { 3.42, 2.05, 1.37, 1.03, 0.82 }, finalDrive = 3.62, driveForce = 4100, driveInertia = 5.8, maxSpeed = 47.0, efficiency = 0.86, frontShare = 1.00, shiftDelay = 0.20, reverseRatio = 3.05 },
            engine = { idleRPM = 820, peakRPM = 4300, redlineRPM = 6500, peakTorqueNm = 158, inertia = 0.24, throttleResponse = 5.0, engineBrakeNm = 32 },
            brakes = { force = 10500, bias = 0.63, absSlip = 0.18, absRelease = 8.5, absRecover = 2.6 },
            steering = { lock = 34, speedSensitivity = 0.72, returnRate = 5.0, counterSteer = 0.16 },
            traction = { max = 1.08, min = 0.54, lateral = 1.00, longitudinal = 1.00, springDelta = 0.17, bias = 0.52, loadSensitivity = 0.12, stiffnessLong = 9.0, stiffnessLat = 7.4 },
            suspension = { force = 24500, compression = 2350, rebound = 3250, upper = 0.18, lower = -0.15, raise = 0.00, bias = 0.55, antiRoll = 8200 },
            aero = { dragArea = 0.68, liftArea = 0.012, downforceArea = 0.010, downforceLimitG = 0.18 }, collision = { restitution = 0.12, yawDamping = 0.18 }
        },
        sedan = {
            mass = 1510, drag = 0.77, centerOfMass = { 0.00, 0.01, -0.10 },
            dimensions = { wheelbase = 2.72, trackWidth = 1.53, wheelRadius = 0.32, wheelInertia = 1.35, frontWeightBias = 0.58, cgHeight = 0.53 },
            drivetrain = { type = "RWD", gears = 5, gearRatios = { 3.20, 1.91, 1.31, 1.00, 0.78 }, finalDrive = 3.42, driveForce = 4750, driveInertia = 6.5, maxSpeed = 53.0, efficiency = 0.87, frontShare = 0.00, shiftDelay = 0.22, reverseRatio = 3.05 },
            engine = { idleRPM = 760, peakRPM = 4100, redlineRPM = 6100, peakTorqueNm = 225, inertia = 0.30, throttleResponse = 4.3, engineBrakeNm = 45 },
            brakes = { force = 14800, bias = 0.64, absSlip = 0.17, absRelease = 8.0, absRecover = 2.5 },
            steering = { lock = 33, speedSensitivity = 0.82, returnRate = 4.3, counterSteer = 0.14 },
            traction = { max = 1.06, min = 0.51, lateral = 1.00, longitudinal = 1.00, springDelta = 0.18, bias = 0.50, loadSensitivity = 0.13, stiffnessLong = 8.4, stiffnessLat = 7.1 },
            suspension = { force = 31800, compression = 3100, rebound = 4350, upper = 0.17, lower = -0.15, raise = 0.00, bias = 0.54, antiRoll = 11800 },
            aero = { dragArea = 0.78, liftArea = 0.014, downforceArea = 0.018, downforceLimitG = 0.20 }, collision = { restitution = 0.12, yawDamping = 0.20 }
        },
        coupe = {
            mass = 1320, drag = 0.70, centerOfMass = { 0.00, 0.00, -0.13 },
            dimensions = { wheelbase = 2.58, trackWidth = 1.55, wheelRadius = 0.31, wheelInertia = 1.22, frontWeightBias = 0.55, cgHeight = 0.48 },
            drivetrain = { type = "RWD", gears = 5, gearRatios = { 3.28, 1.98, 1.37, 1.00, 0.80 }, finalDrive = 3.58, driveForce = 4900, driveInertia = 6.0, maxSpeed = 57.0, efficiency = 0.88, frontShare = 0.00, shiftDelay = 0.20, reverseRatio = 3.05 },
            engine = { idleRPM = 800, peakRPM = 4550, redlineRPM = 6600, peakTorqueNm = 235, inertia = 0.25, throttleResponse = 5.2, engineBrakeNm = 39 },
            brakes = { force = 14200, bias = 0.63, absSlip = 0.17, absRelease = 8.5, absRecover = 2.8 },
            steering = { lock = 35, speedSensitivity = 0.73, returnRate = 5.2, counterSteer = 0.20 },
            traction = { max = 1.10, min = 0.50, lateral = 1.03, longitudinal = 1.00, springDelta = 0.18, bias = 0.49, loadSensitivity = 0.12, stiffnessLong = 9.2, stiffnessLat = 7.8 },
            suspension = { force = 30300, compression = 2800, rebound = 4100, upper = 0.16, lower = -0.14, raise = 0.00, bias = 0.52, antiRoll = 12800 },
            aero = { dragArea = 0.70, liftArea = 0.014, downforceArea = 0.025, downforceLimitG = 0.25 }, collision = { restitution = 0.13, yawDamping = 0.18 }
        },
        sports = {
            mass = 1390, drag = 0.66, centerOfMass = { 0.00, 0.01, -0.15 },
            dimensions = { wheelbase = 2.62, trackWidth = 1.61, wheelRadius = 0.32, wheelInertia = 1.28, frontWeightBias = 0.53, cgHeight = 0.45 },
            drivetrain = { type = "RWD", gears = 6, gearRatios = { 3.20, 2.10, 1.52, 1.18, 0.94, 0.78 }, finalDrive = 3.48, driveForce = 6100, driveInertia = 5.4, maxSpeed = 68.0, efficiency = 0.90, frontShare = 0.00, shiftDelay = 0.17, reverseRatio = 3.05 },
            engine = { idleRPM = 850, peakRPM = 5200, redlineRPM = 7100, peakTorqueNm = 320, inertia = 0.21, throttleResponse = 6.2, engineBrakeNm = 56 },
            brakes = { force = 19200, bias = 0.65, absSlip = 0.16, absRelease = 9.0, absRecover = 3.0 },
            steering = { lock = 32, speedSensitivity = 0.80, returnRate = 5.8, counterSteer = 0.22 },
            traction = { max = 1.18, min = 0.55, lateral = 1.08, longitudinal = 1.03, springDelta = 0.18, bias = 0.48, loadSensitivity = 0.12, stiffnessLong = 9.8, stiffnessLat = 8.5 },
            suspension = { force = 36800, compression = 3450, rebound = 5100, upper = 0.15, lower = -0.13, raise = 0.00, bias = 0.52, antiRoll = 17100 },
            aero = { dragArea = 0.68, liftArea = 0.008, downforceArea = 0.052, downforceLimitG = 0.38 }, collision = { restitution = 0.11, yawDamping = 0.23 }
        },
        super = {
            mass = 1510, drag = 0.62, centerOfMass = { 0.00, 0.02, -0.18 },
            dimensions = { wheelbase = 2.66, trackWidth = 1.68, wheelRadius = 0.33, wheelInertia = 1.48, frontWeightBias = 0.46, cgHeight = 0.42 },
            drivetrain = { type = "RWD", gears = 6, gearRatios = { 3.05, 2.16, 1.61, 1.26, 1.00, 0.82 }, finalDrive = 3.32, driveForce = 8250, driveInertia = 4.4, maxSpeed = 82.0, efficiency = 0.92, frontShare = 0.00, shiftDelay = 0.15, reverseRatio = 3.05 },
            engine = { idleRPM = 900, peakRPM = 5900, redlineRPM = 7600, peakTorqueNm = 470, inertia = 0.17, throttleResponse = 7.0, engineBrakeNm = 72 },
            brakes = { force = 23800, bias = 0.66, absSlip = 0.15, absRelease = 9.4, absRecover = 3.2 },
            steering = { lock = 30, speedSensitivity = 0.92, returnRate = 6.1, counterSteer = 0.24 },
            traction = { max = 1.24, min = 0.58, lateral = 1.11, longitudinal = 1.05, springDelta = 0.20, bias = 0.47, loadSensitivity = 0.11, stiffnessLong = 10.5, stiffnessLat = 9.0 },
            suspension = { force = 42500, compression = 3900, rebound = 5850, upper = 0.14, lower = -0.12, raise = 0.00, bias = 0.51, antiRoll = 20500 },
            aero = { dragArea = 0.63, liftArea = -0.015, downforceArea = 0.12, downforceLimitG = 0.52 }, collision = { restitution = 0.10, yawDamping = 0.26 }
        },
        muscle = {
            mass = 1630, drag = 0.82, centerOfMass = { 0.00, -0.02, -0.11 },
            dimensions = { wheelbase = 2.78, trackWidth = 1.58, wheelRadius = 0.34, wheelInertia = 1.55, frontWeightBias = 0.54, cgHeight = 0.55 },
            drivetrain = { type = "RWD", gears = 5, gearRatios = { 2.97, 1.95, 1.35, 1.00, 0.76 }, finalDrive = 3.73, driveForce = 6900, driveInertia = 7.4, maxSpeed = 61.0, efficiency = 0.86, frontShare = 0.00, shiftDelay = 0.25, reverseRatio = 3.05 },
            engine = { idleRPM = 720, peakRPM = 3500, redlineRPM = 5700, peakTorqueNm = 390, inertia = 0.36, throttleResponse = 4.7, engineBrakeNm = 63 },
            brakes = { force = 16600, bias = 0.62, absSlip = 0.19, absRelease = 7.8, absRecover = 2.3 },
            steering = { lock = 34, speedSensitivity = 0.90, returnRate = 4.0, counterSteer = 0.18 },
            traction = { max = 1.02, min = 0.43, lateral = 0.95, longitudinal = 1.02, springDelta = 0.22, bias = 0.50, loadSensitivity = 0.15, stiffnessLong = 8.0, stiffnessLat = 6.8 },
            suspension = { force = 32600, compression = 3000, rebound = 4200, upper = 0.18, lower = -0.16, raise = 0.00, bias = 0.53, antiRoll = 11200 },
            aero = { dragArea = 0.84, liftArea = 0.028, downforceArea = 0.014, downforceLimitG = 0.18 }, collision = { restitution = 0.14, yawDamping = 0.17 }
        },
        suv = {
            mass = 2140, drag = 1.02, centerOfMass = { 0.00, 0.00, -0.07 },
            dimensions = { wheelbase = 2.82, trackWidth = 1.67, wheelRadius = 0.37, wheelInertia = 1.90, frontWeightBias = 0.56, cgHeight = 0.78 },
            drivetrain = { type = "AWD", gears = 5, gearRatios = { 3.45, 2.12, 1.48, 1.00, 0.78 }, finalDrive = 3.88, driveForce = 7100, driveInertia = 8.5, maxSpeed = 52.0, efficiency = 0.82, frontShare = 0.46, shiftDelay = 0.25, reverseRatio = 3.05 },
            engine = { idleRPM = 700, peakRPM = 3600, redlineRPM = 5600, peakTorqueNm = 330, inertia = 0.42, throttleResponse = 3.8, engineBrakeNm = 58 },
            brakes = { force = 20500, bias = 0.65, absSlip = 0.18, absRelease = 7.6, absRecover = 2.4 },
            steering = { lock = 33, speedSensitivity = 0.95, returnRate = 3.5, counterSteer = 0.12 },
            traction = { max = 1.03, min = 0.57, lateral = 0.94, longitudinal = 1.02, springDelta = 0.23, bias = 0.52, loadSensitivity = 0.16, stiffnessLong = 7.8, stiffnessLat = 6.4 },
            suspension = { force = 42000, compression = 4200, rebound = 5850, upper = 0.24, lower = -0.20, raise = 0.04, bias = 0.57, antiRoll = 15700 },
            aero = { dragArea = 1.03, liftArea = 0.035, downforceArea = 0.012, downforceLimitG = 0.16 }, collision = { restitution = 0.10, yawDamping = 0.28 }
        },
        offroad = {
            mass = 1810, drag = 1.08, centerOfMass = { 0.00, -0.01, -0.04 },
            dimensions = { wheelbase = 2.67, trackWidth = 1.63, wheelRadius = 0.39, wheelInertia = 2.05, frontWeightBias = 0.55, cgHeight = 0.70 },
            drivetrain = { type = "AWD", gears = 5, gearRatios = { 3.62, 2.18, 1.52, 1.00, 0.77 }, finalDrive = 4.05, driveForce = 6500, driveInertia = 8.2, maxSpeed = 50.0, efficiency = 0.82, frontShare = 0.48, shiftDelay = 0.24, reverseRatio = 3.05 },
            engine = { idleRPM = 750, peakRPM = 3750, redlineRPM = 5800, peakTorqueNm = 310, inertia = 0.39, throttleResponse = 4.1, engineBrakeNm = 52 },
            brakes = { force = 18200, bias = 0.64, absSlip = 0.20, absRelease = 7.4, absRecover = 2.4 },
            steering = { lock = 35, speedSensitivity = 0.84, returnRate = 4.0, counterSteer = 0.14 },
            traction = { max = 1.08, min = 0.55, lateral = 0.96, longitudinal = 1.06, springDelta = 0.26, bias = 0.51, loadSensitivity = 0.15, stiffnessLong = 7.8, stiffnessLat = 6.7 },
            suspension = { force = 38500, compression = 3650, rebound = 5000, upper = 0.27, lower = -0.23, raise = 0.06, bias = 0.55, antiRoll = 10800 },
            aero = { dragArea = 1.10, liftArea = 0.026, downforceArea = 0.010, downforceLimitG = 0.14 }, collision = { restitution = 0.13, yawDamping = 0.22 }
        },
        van = {
            mass = 2260, drag = 1.12, centerOfMass = { 0.00, -0.03, -0.06 },
            dimensions = { wheelbase = 3.10, trackWidth = 1.62, wheelRadius = 0.36, wheelInertia = 1.95, frontWeightBias = 0.57, cgHeight = 0.72 },
            drivetrain = { type = "RWD", gears = 5, gearRatios = { 3.36, 2.12, 1.48, 1.00, 0.79 }, finalDrive = 3.96, driveForce = 6100, driveInertia = 9.1, maxSpeed = 45.0, efficiency = 0.82, frontShare = 0.00, shiftDelay = 0.28, reverseRatio = 3.05 },
            engine = { idleRPM = 700, peakRPM = 3400, redlineRPM = 5400, peakTorqueNm = 300, inertia = 0.46, throttleResponse = 3.5, engineBrakeNm = 49 },
            brakes = { force = 19800, bias = 0.66, absSlip = 0.18, absRelease = 7.2, absRecover = 2.3 },
            steering = { lock = 32, speedSensitivity = 0.98, returnRate = 3.3, counterSteer = 0.11 },
            traction = { max = 0.98, min = 0.48, lateral = 0.91, longitudinal = 1.00, springDelta = 0.21, bias = 0.52, loadSensitivity = 0.16, stiffnessLong = 7.3, stiffnessLat = 6.1 },
            suspension = { force = 39000, compression = 3900, rebound = 5450, upper = 0.20, lower = -0.18, raise = 0.02, bias = 0.56, antiRoll = 12400 },
            aero = { dragArea = 1.14, liftArea = 0.032, downforceArea = 0.006, downforceLimitG = 0.12 }, collision = { restitution = 0.09, yawDamping = 0.30 }
        },
        truck = {
            mass = 6200, drag = 1.68, centerOfMass = { 0.00, -0.08, -0.12 },
            dimensions = { wheelbase = 4.12, trackWidth = 1.93, wheelRadius = 0.48, wheelInertia = 4.20, frontWeightBias = 0.39, cgHeight = 0.88 },
            drivetrain = { type = "RWD", gears = 6, gearRatios = { 5.10, 3.42, 2.32, 1.63, 1.18, 0.86 }, finalDrive = 4.72, driveForce = 18800, driveInertia = 14.0, maxSpeed = 36.0, efficiency = 0.78, frontShare = 0.00, shiftDelay = 0.40, reverseRatio = 4.0 },
            engine = { idleRPM = 620, peakRPM = 1900, redlineRPM = 3100, peakTorqueNm = 980, inertia = 0.78, throttleResponse = 2.2, engineBrakeNm = 145 },
            brakes = { force = 52000, bias = 0.68, absSlip = 0.20, absRelease = 6.8, absRecover = 2.1 },
            steering = { lock = 27, speedSensitivity = 1.12, returnRate = 2.7, counterSteer = 0.08 },
            traction = { max = 0.88, min = 0.43, lateral = 0.80, longitudinal = 0.98, springDelta = 0.24, bias = 0.50, loadSensitivity = 0.18, stiffnessLong = 6.4, stiffnessLat = 5.4 },
            suspension = { force = 105000, compression = 11200, rebound = 15700, upper = 0.23, lower = -0.20, raise = 0.00, bias = 0.43, antiRoll = 48000 },
            aero = { dragArea = 1.75, liftArea = 0.045, downforceArea = 0.005, downforceLimitG = 0.08 }, collision = { restitution = 0.06, yawDamping = 0.38 }
        },
        bus = {
            mass = 10800, drag = 2.12, centerOfMass = { 0.00, -0.12, -0.14 },
            dimensions = { wheelbase = 5.65, trackWidth = 2.05, wheelRadius = 0.50, wheelInertia = 5.40, frontWeightBias = 0.40, cgHeight = 1.03 },
            drivetrain = { type = "RWD", gears = 6, gearRatios = { 5.40, 3.55, 2.45, 1.72, 1.25, 0.92 }, finalDrive = 4.30, driveForce = 27500, driveInertia = 18.0, maxSpeed = 30.0, efficiency = 0.77, frontShare = 0.00, shiftDelay = 0.45, reverseRatio = 4.1 },
            engine = { idleRPM = 600, peakRPM = 1750, redlineRPM = 2850, peakTorqueNm = 1500, inertia = 0.94, throttleResponse = 1.9, engineBrakeNm = 220 },
            brakes = { force = 82000, bias = 0.70, absSlip = 0.20, absRelease = 6.5, absRecover = 2.0 },
            steering = { lock = 24, speedSensitivity = 1.18, returnRate = 2.2, counterSteer = 0.06 },
            traction = { max = 0.82, min = 0.40, lateral = 0.76, longitudinal = 0.96, springDelta = 0.27, bias = 0.50, loadSensitivity = 0.19, stiffnessLong = 6.2, stiffnessLat = 5.1 },
            suspension = { force = 165000, compression = 18400, rebound = 25800, upper = 0.22, lower = -0.19, raise = 0.00, bias = 0.45, antiRoll = 71000 },
            aero = { dragArea = 2.15, liftArea = 0.050, downforceArea = 0.002, downforceLimitG = 0.06 }, collision = { restitution = 0.05, yawDamping = 0.42 }
        },
        motorcycle = {
            mass = 245, drag = 0.46, centerOfMass = { 0.00, 0.02, -0.10 },
            dimensions = { wheelbase = 1.43, trackWidth = 0.38, wheelRadius = 0.30, wheelInertia = 0.72, frontWeightBias = 0.48, cgHeight = 0.59 },
            drivetrain = { type = "RWD", gears = 5, gearRatios = { 2.75, 1.94, 1.50, 1.23, 1.05 }, finalDrive = 2.80, driveForce = 3000, driveInertia = 2.7, maxSpeed = 65.0, efficiency = 0.90, frontShare = 0.00, shiftDelay = 0.12, reverseRatio = 2.4 },
            engine = { idleRPM = 1350, peakRPM = 9000, redlineRPM = 11500, peakTorqueNm = 58, inertia = 0.12, throttleResponse = 8.5, engineBrakeNm = 13 },
            brakes = { force = 5100, bias = 0.58, absSlip = 0.16, absRelease = 8.5, absRecover = 3.0 },
            steering = { lock = 29, speedSensitivity = 0.72, returnRate = 4.8, counterSteer = 0.34 },
            traction = { max = 1.10, min = 0.50, lateral = 1.06, longitudinal = 1.00, springDelta = 0.12, bias = 0.55, loadSensitivity = 0.12, stiffnessLong = 9.0, stiffnessLat = 8.2 },
            suspension = { force = 9800, compression = 880, rebound = 1280, upper = 0.16, lower = -0.14, raise = 0.00, bias = 0.50, antiRoll = 0 },
            aero = { dragArea = 0.48, liftArea = 0.018, downforceArea = 0.006, downforceLimitG = 0.12 }, collision = { restitution = 0.08, yawDamping = 0.25 }
        }
    }
}
-- Bounded secondary body-attitude targets (degrees per g of lateral/longitudinal
-- acceleration) plus the lag rates that approach them. These intentionally stay
-- smaller than the native solver's own body motion; they add character, not an
-- overriding attitude controller.
local bodyPresets = {
    compact = { roll = 4.2, pitch = 2.4, rollRate = 6.5, pitchRate = 6.0, yawGain = 0.05 },
    sedan = { roll = 4.4, pitch = 2.2, rollRate = 6.2, pitchRate = 5.8, yawGain = 0.05 },
    coupe = { roll = 4.0, pitch = 2.2, rollRate = 6.6, pitchRate = 6.2, yawGain = 0.05 },
    sports = { roll = 3.2, pitch = 1.8, rollRate = 8.0, pitchRate = 7.5, yawGain = 0.06 },
    super = { roll = 2.8, pitch = 1.6, rollRate = 9.0, pitchRate = 8.0, yawGain = 0.07 },
    muscle = { roll = 5.4, pitch = 2.8, rollRate = 5.2, pitchRate = 5.0, yawGain = 0.05 },
    suv = { roll = 6.3, pitch = 3.0, rollRate = 4.6, pitchRate = 4.4, yawGain = 0.04 },
    offroad = { roll = 6.8, pitch = 3.2, rollRate = 4.4, pitchRate = 4.2, yawGain = 0.04 },
    van = { roll = 5.6, pitch = 2.8, rollRate = 4.2, pitchRate = 4.0, yawGain = 0.04 },
    truck = { roll = 5.0, pitch = 2.2, rollRate = 3.2, pitchRate = 3.0, yawGain = 0.03 },
    bus = { roll = 5.2, pitch = 2.0, rollRate = 3.0, pitchRate = 2.8, yawGain = 0.03 },
    motorcycle = { roll = 1.6, pitch = 1.2, rollRate = 10.0, pitchRate = 9.0, yawGain = 0.08 }
}

for className, baseline in pairs(G4.VehicleClasses.defaults) do
    local preset = bodyPresets[className] or bodyPresets.sedan
    baseline.estimated = true
    baseline.engine.upshiftRPM = math.floor(baseline.engine.redlineRPM * 0.91)
    baseline.engine.downshiftRPM = math.floor(baseline.engine.peakRPM * 0.54)
    baseline.engine.torqueCurve = { riseBase = 0.58, riseGain = 0.42, fallLinear = 0.32, fallQuadratic = 0.10, minimum = 0.52 }
    baseline.traction.magicFormula = { longitudinalShape = 1.55, longitudinalCurvature = 0.88, lateralShape = 1.38, lateralCurvature = 0.88 }
    baseline.steering.inputRate = (className == "truck" or className == "bus") and 7.0 or 9.0
    baseline.steering.speedCurve = 1.25
    baseline.steering.maxCounterSteer = className == "motorcycle" and 0.22 or 0.18
    baseline.brakes.absMinPressure = 0.22
    baseline.brakes.absActivationSpeed = 2.0
    baseline.bodyDynamics = {
        maxRollDeg = preset.roll,
        maxPitchDeg = preset.pitch,
        rollRate = preset.rollRate,
        pitchRate = preset.pitchRate,
        rollDamping = preset.rollRate * 1.1,
        pitchDamping = preset.pitchRate * 1.05,
        yawGain = preset.yawGain
    }
end

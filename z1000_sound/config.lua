-- ============================================================================
-- MTA:SA Z1000 REALISTIC MOTORCYCLE AUDIO
-- Author: AI Agent (Arena.ai)
-- Module: User Configuration
-- ============================================================================

Config = {}

-- Leave empty until the correct bike model is known.
-- Example only (do not assume this is your server's model): Config.TargetModels[581] = true
Config.TargetModels = {}

-- Optional per-vehicle opt-in. Set Enabled=true and set this synced element-data
-- value on vehicles from your server-side resource.
Config.TargetElementData = {
    Enabled = false,
    Key = "z1000Sound",
    Value = true
}

-- IMPORTANT: the files committed with this resource are short SILENCE placeholders.
-- Keep false until tools/build_audio.py has processed genuine reference recordings.
Config.AudioReady = false

-- Stock GTA/MTA engine audio is suppressed only for target vehicles and only when
-- the custom reference layers are ready. See README.txt for the MTA limitation.
Config.SuppressStockSound = true
Config.NativeEngineGroups = {}
for group = 7, 16 do
    Config.NativeEngineGroups[group] = true
end
Config.NativeEngineGroups[40] = true
Config.DebugWorldSounds = false

-- Runtime/performance limits. Sound handles are pooled per vehicle; never created
-- in the frame loop. MaxTrackedVehicles is a hard cap (including fading-out tracks).
Config.UpdateInterval = 50                 -- 20 Hz mixer update
Config.ScanInterval = 350                  -- streamed vehicles are scanned ~2.9 times/sec
Config.MaxTrackedVehicles = 3              -- max simultaneous vehicle mixes
Config.MaxAudibleDistance = 115             -- GTA world units / approximately metres
Config.DistanceHysteresis = 10              -- keep a track alive briefly beyond the radius
Config.MinSoundDistance = 4
Config.TrackFadeInSeconds = 0.18
Config.TrackFadeOutSeconds = 0.22
Config.LayerAttackSeconds = 0.11
Config.LayerReleaseSeconds = 0.20
Config.RespectVehicleEngineState = true

-- RPM is estimated from speed, handling.maxVelocity / numberOfGears, acceleration,
-- and local throttle input. Tune this to the actual bike handling on your server.
Config.RPM = {
    Idle = 1050,
    Redline = 10800,
    LimiterStart = 10900,
    Maximum = 11500,
    DefaultGears = 6,
    GearCountOverride = 0,                -- 0 uses handling.numberOfGears; set 6 to force a Z1000 6-speed model
    GearSpeedExponent = 0.78,
    UpshiftHysteresis = 1.035,
    DownshiftHysteresis = 0.88,
    ShiftCooldownMs = 420,
    ShiftDip = 0.22,
    ShiftDipSeconds = 0.22,
    LayerAnchors = {
        idle = 1200,
        low = 2350,
        mid = 4400,
        high = 7400,
        redline = 10200
    },
    OverlayAnchors = {
        accel = 4700,
        lightAccel = 3000,
        hardAccel = 7600,
        decel = 4200,
        engineBrake = 5000,
        throttleRelease = 4300,
        coast = 2600,
        limiter = 11000,
        intake = 5000,
        exhaust = 4800,
        helmet = 5000
    }
}

Config.Estimator = {
    RPMRiseSeconds = 0.16,
    RPMFallSeconds = 0.30,
    AccelerationSmoothingSeconds = 0.14,
    ThrottleRiseSeconds = 0.08,
    ThrottleFallSeconds = 0.18,
    RemoteFullAccelerationKmhPerSecond = 28,
    RemoteThrottleNoiseFloorKmhPerSecond = 1.2,
    LaunchSpeedKmh = 24,
    LaunchRevRange = 0.34,
    ThrottleLoadRange = 0.055,
    AccelerationLoadRange = 0.055,
    ThrottleReleaseThreshold = 0.24,
    ThrottleReleaseDecaySeconds = 0.34,
    EngineBrakeMinSpeedKmh = 16,
    EngineBrakeDecelKmhPerSecond = 3.0
}

-- setSoundSpeed is a restrained RPM curve, not a linear speed-to-pitch mapping.
-- Distinct RPM recordings remain the primary source of engine character.
Config.Pitch = {
    Enabled = true,
    Curve = 0.72,
    Min = 0.84,
    Max = 1.18,
    DopplerEnabled = true,
    DopplerMaxPercent = 0.025,
    SpeedOfSoundMetresPerSecond = 343
}

-- Each value is a per-layer gain; the mixer also applies the master value and
-- crossfades. Keep room for headroom; do not normalize every layer to maximum.
Config.Volume = {
    Master = 0.88,
    idle = 0.84,
    low = 0.82,
    mid = 0.80,
    high = 0.78,
    redline = 0.74,
    accel = 0.34,
    lightAccel = 0.22,
    hardAccel = 0.34,
    decel = 0.28,
    engineBrake = 0.40,
    throttleRelease = 0.24,
    coast = 0.18,
    limiter = 0.46,
    intake = 0.22,
    exhaust = 0.34,
    shift = 0.25,
    helmet = 0.52
}

-- The nine core loops are the normal mix. Extra layers are opt-in until matching
-- recordings have been supplied; this keeps the voice count and CPU bounded.
Config.LayerEnabled = {
    idle = true,
    low = true,
    mid = true,
    high = true,
    redline = true,
    accel = true,
    decel = true,
    engineBrake = true,
    limiter = true,
    lightAccel = false,
    hardAccel = false,
    throttleRelease = false,
    coast = false,
    intake = false,
    exhaust = false
}

Config.Samples = {
    idle = "audio/z1000_idle.wav",
    low = "audio/z1000_low.wav",
    mid = "audio/z1000_mid.wav",
    high = "audio/z1000_high.wav",
    redline = "audio/z1000_redline.wav",
    accel = "audio/z1000_accel.wav",
    lightAccel = "audio/z1000_light_accel.wav",
    hardAccel = "audio/z1000_hard_accel.wav",
    decel = "audio/z1000_decel.wav",
    engineBrake = "audio/z1000_enginebrake.wav",
    throttleRelease = "audio/z1000_throttle_release.wav",
    coast = "audio/z1000_coast.wav",
    limiter = "audio/z1000_limiter.wav",
    intake = "audio/z1000_intake.wav",
    exhaust = "audio/z1000_exhaust.wav",
    shift = "audio/z1000_shift.wav",
    helmet = "audio/z1000_helmet.wav"
}

-- MTA spatializes each exterior layer in 3D. Offsets are local vehicle coordinates:
-- local Y is forward and local Z is up.
Config.SourceOffsets = {
    Engine = { 0, 0, 0.28 },
    Front = { 0, 0.62, 0.30 },
    Rear = { 0, -1.08, 0.24 }
}

-- Optional 2D rider/helmet recording, heard only by the local driver. For a true
-- helmet perspective, use a separate onboard recording; no artificial EQ is used.
Config.Interior = {
    Enabled = false,
    Volume = 0.30,
    ExteriorDuck = 0.76
}

-- Short gear-change dip is always applied. The transient sample is optional and
-- only starts on an estimated shift; it is never looped or recreated per frame.
Config.ShiftTransientEnabled = false
Config.Test = {
    StartRPM = 4300,
    Throttle = 0.48,
    Gear = 3
}

-- Command-controlled overlay. Config.Debug enables it on resource start;
-- /z1000debug toggles it at runtime.
Config.Debug = false

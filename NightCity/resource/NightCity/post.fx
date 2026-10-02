// post.fx - photographic tonemapper for NightCity (ps_2_0).  Driven entirely from Lua via
//   gGain     exposure (auto set by atmo.lua per time-of-day; /ncexposure overrides it on top)
//   gTint     white balance multiplier (3 floats) -- warm at sunset, cool at night, neutral at noon
//   gSunAlt   0 (night) .. 1 (noon) -- selects between the night look and the day look
//   gHaz      added atmospheric haze colour (3 floats, 0..~0.12)
//   gBloom    strength of the bloom on neon / highlights
//   gVignette soft vignetting amount
//   gGrain    fine film grain
//   gContrast gentle S-curve contrast
//   gTime     seconds, for the grain
texture ScreenTexture;
float2 gPix = float2(0.0007, 0.0013);
float gTime = 0;
float gGain = 1.0;
float3 gTint = float3(1.0, 1.0, 1.0);
float gSunAlt = 0.0;
float3 gHaz = float3(0.0, 0.0, 0.0);
float gBloom = 0.45;
float gVignette = 0.6;
float gGrain = 0.014;
float gContrast = 1.0;

sampler S0 = sampler_state { Texture = (ScreenTexture); MinFilter = Linear; MagFilter = Linear; AddressU = Clamp; AddressV = Clamp; };

// ACES-ish filmic tonemap (Narkowicz approximation)
float3 aces(float3 x)
{
    const float a = 2.51; const float b = 0.03; const float c = 2.43; const float d = 0.59; const float e = 0.14;
    return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
}

float4 PixelShaderFunction(float2 uv : TEXCOORD0) : COLOR0
{
    float2 d0 = uv - 0.5;
    float r2 = dot(d0, d0);

    // ---- chromatic aberration (very subtle; stronger at night for a cinematic lens feel)
    float caAmt = lerp(0.004, 0.010, 1.0 - gSunAlt);
    float2 ca = d0 * r2 * caAmt;
    float3 c;
    c.r = tex2D(S0, uv + ca).r;
    c.g = tex2D(S0, uv).g;
    c.b = tex2D(S0, uv - ca).b;

    // ---- micro sharpen (fine detail)
    float2 o = gPix * 1.2;
    float3 n = tex2D(S0, uv + o).rgb + tex2D(S0, uv - o).rgb
             + tex2D(S0, uv + float2(o.x, -o.y)).rgb + tex2D(S0, uv + float2(-o.x, o.y)).rgb;
    n *= 0.25;
    c += (c - n) * 0.30;

    // ---- bloom from wider taps (neon / sun glints / lit windows)
    float2 w = gPix * 10.0;
    float3 b  = tex2D(S0, uv + float2( w.x, 0.0)).rgb + tex2D(S0, uv - float2( w.x, 0.0)).rgb
              + tex2D(S0, uv + float2(0.0,  w.y)).rgb + tex2D(S0, uv - float2(0.0,  w.y)).rgb;
    b *= 0.25;
    float2 w2 = gPix * 22.0;
    float3 b2 = tex2D(S0, uv + float2( w2.x,  w2.y)).rgb + tex2D(S0, uv - float2( w2.x,  w2.y)).rgb
              + tex2D(S0, uv + float2( w2.x, -w2.y)).rgb + tex2D(S0, uv - float2( w2.x, -w2.y)).rgb;
    b2 *= 0.25;
    float bloomMask = max(max(c.r, c.g), c.b) - 0.55;
    c += max(b - 0.45, 0.0) * gBloom * 0.9;
    c += max(b2 - 0.60, 0.0) * gBloom * 0.4;

    // ---- white balance (per time-of-day tint)
    c *= gTint;

    // ---- atmospheric haze: add toward horizon colour (gHaz) more in the corners / distance; at night fade to sky dark
    float3 haze = gHaz * 6.0;              // un-multiply since haze is added to a 0..1 buffer
    c += haze * saturate(r2 * 1.2);

    // ---- exposure + tonemap
    c *= gGain;
    c = aces(c);

    // ---- contrast (gentle S-curve controlled by gContrast)
    float cMid = 0.5 + (1.0 - gContrast) * 0.1;
    c = lerp(c, c * c * (3.0 - 2.0 * c), (gContrast - 1.0) * 0.8 + 0.25);

    // ---- day/night colour grade: desaturate nights slightly, teal shadows warm highlights at golden hour
    float l = dot(c, float3(0.299, 0.587, 0.114));
    float nightK = 1.0 - gSunAlt;
    c = lerp(c, float3(l, l, l), nightK * 0.10);
    float3 dayCast  = float3(1.02, 0.99, 0.98);
    float3 nightCast = float3(0.86, 0.92, 1.06);
    float3 cast = lerp(dayCast, nightCast, nightK);
    // warm sunset push when sun is low
    float sunset = saturate((1.0 - gSunAlt) * smoothstep(0.25, 0.05, gSunAlt));
    cast = lerp(cast, float3(1.10, 0.88, 0.78), sunset * 0.45);
    c *= cast;

    // ---- vignette (darker at the edges; stronger at night)
    float v = saturate(1.0 - r2 * (gVignette * (0.9 + 0.3 * nightK)));
    c *= v;

    // ---- fine film grain
    float g = frac(sin(dot(uv * float2(913.0, 541.0) + gTime, float2(12.9898, 78.233))) * 43758.5453) - 0.5;
    c += g * gGrain;

    return float4(saturate(c), 1.0);
}

technique tec0 { pass P0 { PixelShader = compile ps_2_0 PixelShaderFunction(); } }
technique fallback { pass P0 {} }

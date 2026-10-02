// Created by: Arena.ai Agent Mode (AI) - NightCity MTA:SA resource
// post.fx - cinematic night grade for NightCity (switched with /ncfx).  Pure pixel shader (ps_2_0, 11 texture reads):
//   chromatic aberration towards the corners, micro sharpen, strong bloom on the brightest areas (neon, lamps, screens),
//   more saturation, gentle S-curve, teal shadows / warm highlights, exposure (/ncexposure), vignette and fine film grain.
texture ScreenTexture;
float2 gPix = float2(0.0007, 0.0013);
float gTime = 0;
float gGain = 1.0;                                 // exposure (script: /ncexposure)

sampler S0 = sampler_state
{
    Texture = (ScreenTexture);
    MinFilter = Linear;
    MagFilter = Linear;
    AddressU = Clamp;
    AddressV = Clamp;
};

float4 PixelShaderFunction(float2 uv : TEXCOORD0) : COLOR0
{
    float2 d0 = uv - 0.5;
    float r2 = dot(d0, d0);
    float2 ca = d0 * r2 * 0.014;
    float3 c;
    c.r = tex2D(S0, uv + ca).r;
    c.g = tex2D(S0, uv).g;
    c.b = tex2D(S0, uv - ca).b;
    float2 o = gPix * 1.5;
    float3 n = tex2D(S0, uv + o).rgb + tex2D(S0, uv - o).rgb
             + tex2D(S0, uv + float2(o.x, -o.y)).rgb + tex2D(S0, uv + float2(-o.x, o.y)).rgb;
    n *= 0.25;
    c += (c - n) * 0.45;
    float2 w = gPix * 9.0;
    float3 b = tex2D(S0, uv + float2(w.x, 0.0)).rgb + tex2D(S0, uv - float2(w.x, 0.0)).rgb
             + tex2D(S0, uv + float2(0.0, w.y)).rgb + tex2D(S0, uv - float2(0.0, w.y)).rgb;
    b *= 0.25;
    c += max(b - 0.36, 0.0) * 0.95;
    float l = dot(c, float3(0.299, 0.587, 0.114));
    c = lerp(float3(l, l, l), c, 1.18);
    c = lerp(c, c * c * (3.0 - 2.0 * c), 0.45);
    c *= lerp(float3(0.86, 1.0, 1.12), float3(1.10, 0.98, 1.04), saturate(l * 1.6));
    c *= gGain;
    c *= saturate(1.0 - r2 * 1.25);
    float g = frac(sin(dot(uv * float2(913.0, 541.0) + gTime, float2(12.9898, 78.233))) * 43758.5453) - 0.5;
    c += g * 0.022;
    return float4(saturate(c), 1.0);
}

technique tec0
{
    pass P0
    {
        PixelShader = compile ps_2_0 PixelShaderFunction();
    }
}

technique fallback
{
    pass P0
    {
    }
}

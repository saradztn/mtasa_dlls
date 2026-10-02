// Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA resource
// post.fx - cinematic screen grade for the abandoned city (toggle: /cityfx).  Pure pixel shader (ps_2_0, 9 texture reads):
//   micro sharpen (unsharp mask), soft bloom on the brightest areas, desaturation, gentle S-curve contrast,
//   cold shadows / warm highlights, vignette and fine film grain.
texture ScreenTexture;
float2 gPix = float2(0.0007, 0.001);
float gTime = 0;

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
    float3 c = tex2D(S0, uv).rgb;
    float2 o = gPix * 1.6;
    float3 n = tex2D(S0, uv + float2(o.x, o.y)).rgb + tex2D(S0, uv + float2(-o.x, o.y)).rgb
             + tex2D(S0, uv + float2(o.x, -o.y)).rgb + tex2D(S0, uv + float2(-o.x, -o.y)).rgb;
    n *= 0.25;
    float2 w2 = gPix * 7.0;
    float3 w = tex2D(S0, uv + float2(w2.x, 0)).rgb + tex2D(S0, uv + float2(-w2.x, 0)).rgb
             + tex2D(S0, uv + float2(0, w2.y)).rgb + tex2D(S0, uv + float2(0, -w2.y)).rgb;
    w *= 0.25;
    c += (c - n) * 0.55;
    c += max(w - 0.55, 0.0) * 0.55;
    float l = dot(c, float3(0.299, 0.587, 0.114));
    c = lerp(float3(l, l, l), c, 0.82);
    c = (c - 0.5) * 1.10 + 0.5;
    c *= lerp(float3(0.90, 0.98, 1.05), float3(1.05, 1.0, 0.93), saturate(l * 1.7)) * 1.16;
    float2 d = uv - 0.5;
    c *= saturate(1.0 - dot(d, d) * 1.15);
    float g = frac(sin(dot(uv * float2(913.0, 541.0) + gTime, float2(12.9898, 78.233))) * 43758.5453) - 0.5;
    c += g * 0.028;
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

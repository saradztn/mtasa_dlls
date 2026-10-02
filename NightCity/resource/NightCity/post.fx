// Minimal cinematic grade for NightCity.
// Deliberately tiny ps_2_0 path (one texture read) so it compiles on older MTA GPUs.
// Weather, sun position and the sky gradient are driven by atmo.lua; this shader only
// applies its gentle exposure and ambient colour balance to the already-rendered frame.
texture ScreenTexture;
float gGain = 1.0;
float3 gTint = float3(1.0, 1.0, 1.0);

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
    float4 c = tex2D(S0, uv);
    return float4(saturate(c.rgb * gTint * gGain), 1.0);
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

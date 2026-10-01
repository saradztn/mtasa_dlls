// Stage 11a: 2x2 scene luminance estimate into a persistent 1x1 x8r8g8b8 target,
// followed by exponential adaptation. This is an LDR exposure estimate, not HDR.
texture SceneTexture;
texture PreviousExposure;
float PreviousValid;
float AdaptRate;

sampler SceneSampler = sampler_state
{
    Texture = (SceneTexture);
    MinFilter = Linear;
    MagFilter = Linear;
    MipFilter = None;
    AddressU = Clamp;
    AddressV = Clamp;
};
sampler ExposureSampler = sampler_state
{
    Texture = (PreviousExposure);
    MinFilter = Point;
    MagFilter = Point;
    MipFilter = None;
    AddressU = Clamp;
    AddressV = Clamp;
};

float LumaAt(float2 uv)
{
    float3 color = tex2D(SceneSampler, uv).rgb;
    return dot(color, float3(0.299, 0.587, 0.114));
}

float4 LuminancePS(float2 uv : TEXCOORD0) : COLOR0
{
    float sum = 0.0;
    sum += LumaAt(float2(0.25, 0.25));
    sum += LumaAt(float2(0.75, 0.25));
    sum += LumaAt(float2(0.25, 0.75));
    sum += LumaAt(float2(0.75, 0.75));

    float averageLuma = max(sum * 0.25, 0.035);
    float targetExposure = clamp(0.50 / averageLuma, 0.88, 1.12);
    float previous = tex2D(ExposureSampler, float2(0.5, 0.5)).r;
    float adapted = (PreviousValid > 0.5)
        ? lerp(previous, targetExposure, saturate(AdaptRate))
        : targetExposure;
    return float4(adapted, adapted, adapted, 1.0);
}

technique Main
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_2_0 LuminancePS();
    }
}

technique Fallback
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        Texture[0] = SceneTexture;
        ColorOp[0] = SelectArg1;
        ColorArg1[0] = Texture;
        AlphaOp[0] = SelectArg1;
        AlphaArg1[0] = Texture;
        ColorOp[1] = Disable;
        AlphaOp[1] = Disable;
    }
}

// Stage 11b: optional tone mapping of the LDR screen capture. GTA SA's scene
// target is not exposed as an HDR resource, so this is highlight roll-off only;
// it cannot recover highlights that the game already clipped.
texture SceneTexture;
texture ExposureTexture;
float UseAutoExposure;
float ManualExposure;
float ToneStrength;
float ToneMapMode;

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
    Texture = (ExposureTexture);
    MinFilter = Point;
    MagFilter = Point;
    MipFilter = None;
    AddressU = Clamp;
    AddressV = Clamp;
};

float3 AcesLike(float3 color)
{
    float3 numerator = color * (2.51 * color + 0.03);
    float3 denominator = color * (2.43 * color + 0.59) + 0.14;
    return saturate(numerator / max(denominator, 0.0001));
}

float4 ToneMapPS(float2 uv : TEXCOORD0) : COLOR0
{
    float4 source = tex2D(SceneSampler, uv);
    float exposure = max(ManualExposure, 0.01);
    if (UseAutoExposure > 0.5)
        exposure *= clamp(tex2D(ExposureSampler, float2(0.5, 0.5)).r, 0.88, 1.12);

    float3 exposed = max(source.rgb * exposure, 0.0);
    float3 mapped = (ToneMapMode < 0.5)
        ? exposed / (1.0 + exposed)
        : AcesLike(exposed);
    float3 result = lerp(source.rgb, mapped, saturate(ToneStrength));
    return float4(saturate(result), source.a);
}

technique Main
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_2_0 ToneMapPS();
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

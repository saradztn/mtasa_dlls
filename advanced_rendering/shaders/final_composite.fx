// Stage 12: independent color-management / final composite pass. Neutral values
// produce an identity composite; this pass is not used for temporal reconstruction.
texture SceneTexture;
float ExposureEV;
float Contrast;
float Saturation;
float Temperature;

sampler SceneSampler = sampler_state
{
    Texture = (SceneTexture);
    MinFilter = Linear;
    MagFilter = Linear;
    MipFilter = None;
    AddressU = Clamp;
    AddressV = Clamp;
};

float4 FinalCompositePS(float2 uv : TEXCOORD0) : COLOR0
{
    float4 source = tex2D(SceneSampler, uv);
    float exposure = exp2(clamp(ExposureEV, -4.0, 4.0));
    float3 color = source.rgb * exposure;
    float contrastValue = clamp(Contrast, 0.5, 1.5);
    color = (color - 0.5) * contrastValue + 0.5;

    float luma = dot(color, float3(0.299, 0.587, 0.114));
    color = lerp(luma.xxx, color, clamp(Saturation, 0.0, 2.0));

    float temperature = clamp(Temperature, -1.0, 1.0) * 0.035;
    color.r += temperature;
    color.b -= temperature;
    return float4(saturate(color), source.a);
}

technique Main
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_2_0 FinalCompositePS();
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

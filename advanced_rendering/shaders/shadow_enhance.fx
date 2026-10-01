// Stage 9: depth-guided short-range contact-occlusion approximation. It does
// not access GTA's shadow map and does not draw screen-space black gradients.
texture SceneTexture;
texture DepthTexture;
float2 TexelSize;
float ShadowStrength;
float UseDepth;

sampler SceneSampler = sampler_state
{
    Texture = (SceneTexture);
    MinFilter = Linear;
    MagFilter = Linear;
    MipFilter = None;
    AddressU = Clamp;
    AddressV = Clamp;
};
sampler DepthSampler = sampler_state
{
    Texture = (DepthTexture);
    MinFilter = Point;
    MagFilter = Point;
    MipFilter = None;
    AddressU = Clamp;
    AddressV = Clamp;
};

float DecodeDepth24(float3 encoded)
{
    return encoded.r + encoded.g / 255.0 + encoded.b / 65025.0;
}
float ContactOcclusion(float center, float2 uv)
{
    float neighbor = DecodeDepth24(tex2D(DepthSampler, saturate(uv)).rgb);
    float difference = center - neighbor;
    float localRange = 0.007 + center * 0.012;
    return saturate((difference - 0.002) / max(localRange, 0.002))
         * (1.0 - saturate((difference - localRange) * 60.0));
}

float4 ShadowEnhancePS(float2 uv : TEXCOORD0) : COLOR0
{
    float4 source = tex2D(SceneSampler, uv);
    if (UseDepth < 0.5)
        return source;

    float center = DecodeDepth24(tex2D(DepthSampler, uv).rgb);
    if (center > 0.98)
        return source;

    float occlusion = 0.0;
    occlusion += ContactOcclusion(center, uv + float2( TexelSize.x, 0.0));
    occlusion += ContactOcclusion(center, uv + float2(-TexelSize.x, 0.0));
    occlusion += ContactOcclusion(center, uv + float2(0.0,  TexelSize.y));
    occlusion += ContactOcclusion(center, uv + float2(0.0, -TexelSize.y));
    occlusion *= 0.25;

    float attenuate = saturate(occlusion * saturate(ShadowStrength));
    return float4(source.rgb * (1.0 - attenuate), source.a);
}

technique Main
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_2_0 ShadowEnhancePS();
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

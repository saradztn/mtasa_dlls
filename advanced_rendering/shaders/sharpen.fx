// Stage 10: restrained, depth-aware local detail recovery. Neighboring samples
// across a depth discontinuity are excluded to avoid bright/dark halo outlines.
// The depth-aware kernel is PS 3.0; PS 2.0 retains a restrained four-neighbor
// detail pass without claiming depth gating.
texture SceneTexture;
texture DepthTexture;
float2 TexelSize;
float UseDepth;
float SharpenStrength;

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

float4 SharpenPS(float2 uv : TEXCOORD0) : COLOR0
{
    float4 center = tex2D(SceneSampler, uv);
    float4 north = tex2D(SceneSampler, uv + float2(0.0, -TexelSize.y));
    float4 south = tex2D(SceneSampler, uv + float2(0.0,  TexelSize.y));
    float4 east = tex2D(SceneSampler, uv + float2( TexelSize.x, 0.0));
    float4 west = tex2D(SceneSampler, uv + float2(-TexelSize.x, 0.0));

    float wN = 1.0;
    float wS = 1.0;
    float wE = 1.0;
    float wW = 1.0;
    if (UseDepth > 0.5)
    {
        float centerDepth = DecodeDepth24(tex2D(DepthSampler, uv).rgb);
        float dN = DecodeDepth24(tex2D(DepthSampler, uv + float2(0.0, -TexelSize.y)).rgb);
        float dS = DecodeDepth24(tex2D(DepthSampler, uv + float2(0.0,  TexelSize.y)).rgb);
        float dE = DecodeDepth24(tex2D(DepthSampler, uv + float2( TexelSize.x, 0.0)).rgb);
        float dW = DecodeDepth24(tex2D(DepthSampler, uv + float2(-TexelSize.x, 0.0)).rgb);
        wN = saturate(1.0 - abs(dN - centerDepth) * 70.0);
        wS = saturate(1.0 - abs(dS - centerDepth) * 70.0);
        wE = saturate(1.0 - abs(dE - centerDepth) * 70.0);
        wW = saturate(1.0 - abs(dW - centerDepth) * 70.0);
    }

    float weightSum = max(wN + wS + wE + wW, 0.001);
    float3 localMean = (north.rgb * wN + south.rgb * wS + east.rgb * wE + west.rgb * wW) / weightSum;
    float3 detail = center.rgb - localMean;
    detail = clamp(detail, -0.045, 0.045) * saturate(SharpenStrength);
    return float4(saturate(center.rgb + detail), center.a);
}

float4 LowSharpenPS(float2 uv : TEXCOORD0) : COLOR0
{
    float4 center = tex2D(SceneSampler, uv);
    float3 north = tex2D(SceneSampler, uv + float2(0.0, -TexelSize.y)).rgb;
    float3 south = tex2D(SceneSampler, uv + float2(0.0,  TexelSize.y)).rgb;
    float3 east = tex2D(SceneSampler, uv + float2( TexelSize.x, 0.0)).rgb;
    float3 west = tex2D(SceneSampler, uv + float2(-TexelSize.x, 0.0)).rgb;
    float3 localMean = (north + south + east + west) * 0.25;
    float3 detail = clamp(center.rgb - localMean, -0.03, 0.03) * saturate(SharpenStrength) * 0.55;
    return float4(saturate(center.rgb + detail), center.a);
}

technique HighQuality
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_3_0 SharpenPS();
    }
}

technique Compatibility
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_2_0 LowSharpenPS();
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

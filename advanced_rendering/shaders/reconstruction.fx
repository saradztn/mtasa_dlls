// Stage 5: edge-aware local detail recovery. It reuses high-frequency contrast
// present in the captured frame; it cannot synthesize missing texture detail.
// The depth-guided 10-tap version is PS 3.0; PS 2.0 uses the lighter four-neighbor
// compatibility kernel below.
texture SceneTexture;
texture DepthTexture;
float2 TexelSize;
float UseDepth;
float DetailStrength;

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
float Luma(float3 color)
{
    return dot(color, float3(0.299, 0.587, 0.114));
}

float4 DetailReconstructPS(float2 uv : TEXCOORD0) : COLOR0
{
    float4 center = tex2D(SceneSampler, uv);
    float4 north = tex2D(SceneSampler, uv + float2(0.0, -TexelSize.y));
    float4 south = tex2D(SceneSampler, uv + float2(0.0,  TexelSize.y));
    float4 east = tex2D(SceneSampler, uv + float2( TexelSize.x, 0.0));
    float4 west = tex2D(SceneSampler, uv + float2(-TexelSize.x, 0.0));

    float centerDepth = 0.0;
    float depthN = 0.0;
    float depthS = 0.0;
    float depthE = 0.0;
    float depthW = 0.0;
    if (UseDepth > 0.5)
    {
        centerDepth = DecodeDepth24(tex2D(DepthSampler, uv).rgb);
        depthN = DecodeDepth24(tex2D(DepthSampler, uv + float2(0.0, -TexelSize.y)).rgb);
        depthS = DecodeDepth24(tex2D(DepthSampler, uv + float2(0.0,  TexelSize.y)).rgb);
        depthE = DecodeDepth24(tex2D(DepthSampler, uv + float2( TexelSize.x, 0.0)).rgb);
        depthW = DecodeDepth24(tex2D(DepthSampler, uv + float2(-TexelSize.x, 0.0)).rgb);
    }

    float wN = (UseDepth > 0.5) ? saturate(1.0 - abs(depthN - centerDepth) * 75.0) : 1.0;
    float wS = (UseDepth > 0.5) ? saturate(1.0 - abs(depthS - centerDepth) * 75.0) : 1.0;
    float wE = (UseDepth > 0.5) ? saturate(1.0 - abs(depthE - centerDepth) * 75.0) : 1.0;
    float wW = (UseDepth > 0.5) ? saturate(1.0 - abs(depthW - centerDepth) * 75.0) : 1.0;
    float weightSum = max(wN + wS + wE + wW, 0.001);
    float3 localMean = (north.rgb * wN + south.rgb * wS + east.rgb * wE + west.rgb * wW) / weightSum;

    float localContrast = max(abs(Luma(center.rgb) - Luma(north.rgb)), max(abs(Luma(center.rgb) - Luma(south.rgb)), max(abs(Luma(center.rgb) - Luma(east.rgb)), abs(Luma(center.rgb) - Luma(west.rgb)))));
    float edgeProtection = 1.0 - saturate((localContrast - 0.12) * 2.5);
    float3 detail = (center.rgb - localMean) * saturate(DetailStrength) * (0.78 + 0.22 * edgeProtection);
    detail = clamp(detail, -0.055, 0.055);
    return float4(saturate(center.rgb + detail), center.a);
}

float4 LowDetailPS(float2 uv : TEXCOORD0) : COLOR0
{
    float4 center = tex2D(SceneSampler, uv);
    float3 north = tex2D(SceneSampler, uv + float2(0.0, -TexelSize.y)).rgb;
    float3 south = tex2D(SceneSampler, uv + float2(0.0,  TexelSize.y)).rgb;
    float3 east = tex2D(SceneSampler, uv + float2( TexelSize.x, 0.0)).rgb;
    float3 west = tex2D(SceneSampler, uv + float2(-TexelSize.x, 0.0)).rgb;
    float3 meanColor = (north + south + east + west) * 0.25;
    float3 detail = clamp(center.rgb - meanColor, -0.035, 0.035) * saturate(DetailStrength) * 0.55;
    return float4(saturate(center.rgb + detail), center.a);
}

technique HighQuality
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_3_0 DetailReconstructPS();
    }
}

technique Compatibility
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_2_0 LowDetailPS();
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

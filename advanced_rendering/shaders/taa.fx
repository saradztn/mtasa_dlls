// Stage 4a: lightweight luma-edge reconstruction (SMAA/FXAA-inspired, not a
// substitute for engine MSAA). It is deliberately low strength and runs before
// temporal accumulation so the history clamp can stabilize the edge result.
texture SceneTexture;
texture DepthTexture;
float2 TexelSize;
float UseDepth;
float EdgeThreshold;
float EdgeStrength;

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

float Luma(float3 color)
{
    return dot(color, float3(0.299, 0.587, 0.114));
}
float DecodeDepth24(float3 encoded)
{
    return encoded.r + encoded.g / 255.0 + encoded.b / 65025.0;
}

float4 EdgeAAPixel(float2 uv : TEXCOORD0) : COLOR0
{
    float4 center = tex2D(SceneSampler, uv);
    float3 north = tex2D(SceneSampler, uv + float2(0.0, -TexelSize.y)).rgb;
    float3 south = tex2D(SceneSampler, uv + float2(0.0,  TexelSize.y)).rgb;
    float3 east = tex2D(SceneSampler, uv + float2( TexelSize.x, 0.0)).rgb;
    float3 west = tex2D(SceneSampler, uv + float2(-TexelSize.x, 0.0)).rgb;

    float horizontalContrast = max(abs(Luma(east) - Luma(center.rgb)), abs(Luma(west) - Luma(center.rgb)));
    float verticalContrast = max(abs(Luma(north) - Luma(center.rgb)), abs(Luma(south) - Luma(center.rgb)));
    float edge = max(horizontalContrast, verticalContrast);
    float3 edgeAverage;
    float depthDelta = 0.0;
    float centerDepth = 0.0;
    if (UseDepth > 0.5)
        centerDepth = DecodeDepth24(tex2D(DepthSampler, uv).rgb);

    if (horizontalContrast >= verticalContrast)
    {
        edgeAverage = 0.5 * (east + west);
        if (UseDepth > 0.5)
        {
            float d0 = DecodeDepth24(tex2D(DepthSampler, uv + float2( TexelSize.x, 0.0)).rgb);
            float d1 = DecodeDepth24(tex2D(DepthSampler, uv + float2(-TexelSize.x, 0.0)).rgb);
            depthDelta = max(abs(d0 - centerDepth), abs(d1 - centerDepth));
        }
    }
    else
    {
        edgeAverage = 0.5 * (north + south);
        if (UseDepth > 0.5)
        {
            float d0 = DecodeDepth24(tex2D(DepthSampler, uv + float2(0.0, -TexelSize.y)).rgb);
            float d1 = DecodeDepth24(tex2D(DepthSampler, uv + float2(0.0,  TexelSize.y)).rgb);
            depthDelta = max(abs(d0 - centerDepth), abs(d1 - centerDepth));
        }
    }

    float coverage = saturate((edge - EdgeThreshold) * 4.5) * saturate(EdgeStrength);
    if (UseDepth > 0.5)
        coverage *= 1.0 - saturate((depthDelta - 0.002) * 65.0) * 0.58;
    return float4(lerp(center.rgb, edgeAverage, coverage), 1.0);
}

// Reduced four-neighbour kernel for PS 2.0 devices. It retains edge-aware
// smoothing but omits the depth taps to stay within older instruction limits.
float4 EdgeAACompatibilityPS(float2 uv : TEXCOORD0) : COLOR0
{
    float4 center = tex2D(SceneSampler, uv);
    float3 north = tex2D(SceneSampler, uv + float2(0.0, -TexelSize.y)).rgb;
    float3 south = tex2D(SceneSampler, uv + float2(0.0,  TexelSize.y)).rgb;
    float3 east = tex2D(SceneSampler, uv + float2( TexelSize.x, 0.0)).rgb;
    float3 west = tex2D(SceneSampler, uv + float2(-TexelSize.x, 0.0)).rgb;
    float centerLuma = Luma(center.rgb);
    float horizontalContrast = max(abs(Luma(east) - centerLuma), abs(Luma(west) - centerLuma));
    float verticalContrast = max(abs(Luma(north) - centerLuma), abs(Luma(south) - centerLuma));
    float3 edgeAverage = horizontalContrast >= verticalContrast
        ? 0.5 * (east + west)
        : 0.5 * (north + south);
    float coverage = saturate((max(horizontalContrast, verticalContrast) - EdgeThreshold) * 4.5)
                   * saturate(EdgeStrength);
    return float4(lerp(center.rgb, edgeAverage, coverage), 1.0);
}

technique HighQuality
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_3_0 EdgeAAPixel();
    }
}

technique Compatibility
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_2_0 EdgeAACompatibilityPS();
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

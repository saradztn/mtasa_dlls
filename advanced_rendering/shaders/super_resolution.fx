// Stage 6: edge-aware Catmull-Rom upsampling. The 4 bilinear samples combine
// the separable four-tap cubic kernel (a compact 2x2-bilinear implementation).
// At depth boundaries the result fades toward linear sampling to limit ringing.
texture SceneTexture;
texture DepthTexture;
float2 SourceTexelSize;
float2 DepthTexelSize;
float UseDepth;
float ReconstructionEnabled;
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

float4 CatmullRomWeights(float t)
{
    float t2 = t * t;
    float t3 = t2 * t;
    return float4(
        -0.5 * t + t2 - 0.5 * t3,
        1.0 - 2.5 * t2 + 1.5 * t3,
        0.5 * t + 2.0 * t2 - 1.5 * t3,
        -0.5 * t2 + 0.5 * t3
    );
}
float DecodeDepth24(float3 encoded)
{
    return encoded.r + encoded.g / 255.0 + encoded.b / 65025.0;
}

float4 SuperResolutionPS(float2 uv : TEXCOORD0) : COLOR0
{
    float4 linearColor = tex2D(SceneSampler, uv);
    if (ReconstructionEnabled < 0.5)
        return linearColor;

    float2 pixel = uv / SourceTexelSize - 0.5;
    float2 basePixel = floor(pixel);
    float2 f = pixel - basePixel;
    float4 wx = CatmullRomWeights(f.x);
    float4 wy = CatmullRomWeights(f.y);
    float wx0 = wx.x;
    float wx1 = wx.y;
    float wx2 = wx.z;
    float wx3 = wx.w;
    float wy0 = wy.x;
    float wy1 = wy.y;
    float wy2 = wy.z;
    float wy3 = wy.w;

    float sx0 = wx0 + wx1;
    float sx1 = wx2 + wx3;
    float sy0 = wy0 + wy1;
    float sy1 = wy2 + wy3;
    float ox0 = -wx0 / max(sx0, 0.0001);
    float ox1 = 1.0 + wx3 / max(sx1, 0.0001);
    float oy0 = -wy0 / max(sy0, 0.0001);
    float oy1 = 1.0 + wy3 / max(sy1, 0.0001);
    float2 baseCenter = (basePixel + 0.5) * SourceTexelSize;

    float4 s00 = tex2D(SceneSampler, baseCenter + float2(ox0, oy0) * SourceTexelSize);
    float4 s10 = tex2D(SceneSampler, baseCenter + float2(ox1, oy0) * SourceTexelSize);
    float4 s01 = tex2D(SceneSampler, baseCenter + float2(ox0, oy1) * SourceTexelSize);
    float4 s11 = tex2D(SceneSampler, baseCenter + float2(ox1, oy1) * SourceTexelSize);
    float4 cubic = s00 * (sx0 * sy0) + s10 * (sx1 * sy0) + s01 * (sx0 * sy1) + s11 * (sx1 * sy1);

    // Limit cubic overshoot relative to the stable bilinear reference.
    float3 cubicCorrection = clamp(cubic.rgb - linearColor.rgb, -0.06, 0.06);
    float3 cubicRGB = linearColor.rgb + cubicCorrection;

    float depthEdge = 0.0;
    if (UseDepth > 0.5)
    {
        float centerDepth = DecodeDepth24(tex2D(DepthSampler, uv).rgb);
        float d0 = DecodeDepth24(tex2D(DepthSampler, uv + float2(DepthTexelSize.x, 0.0)).rgb);
        float d1 = DecodeDepth24(tex2D(DepthSampler, uv + float2(-DepthTexelSize.x, 0.0)).rgb);
        float d2 = DecodeDepth24(tex2D(DepthSampler, uv + float2(0.0, DepthTexelSize.y)).rgb);
        float d3 = DecodeDepth24(tex2D(DepthSampler, uv + float2(0.0, -DepthTexelSize.y)).rgb);
        float difference = max(max(abs(d0 - centerDepth), abs(d1 - centerDepth)), max(abs(d2 - centerDepth), abs(d3 - centerDepth)));
        depthEdge = saturate((difference - 0.0025) * 65.0);
    }
    float3 result = lerp(cubicRGB, linearColor.rgb, depthEdge * saturate(EdgeStrength));
    return float4(result, 1.0);
}

float4 LinearUpscalePS(float2 uv : TEXCOORD0) : COLOR0
{
    return tex2D(SceneSampler, uv);
}

technique HighQuality
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_3_0 SuperResolutionPS();
    }
}

// PS 2.0 fallback: still scales the image, but does not claim Catmull-Rom.
technique Compatibility
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_2_0 LinearUpscalePS();
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

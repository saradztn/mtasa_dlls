// Stage 2: read MTA's shader-readable native depth buffer and encode linear eye
// distance into RGB8. The target is x8r8g8b8, not a floating-point texture.
// MTA may expose RAWZ on some D3D9 drivers; handle the official MTA macro.
texture gDepthBuffer : DEPTHBUFFER;
matrix gProjectionMainScene : PROJECTION_MAIN_SCENE;
float FarPlane;

#ifndef IS_DEPTHBUFFER_RAWZ
#define IS_DEPTHBUFFER_RAWZ 0
#endif

sampler DepthBufferSampler = sampler_state
{
    Texture = (gDepthBuffer);
    MinFilter = Point;
    MagFilter = Point;
    MipFilter = None;
    AddressU = Clamp;
    AddressV = Clamp;
};

float ReadRawDepth(float2 uv)
{
    float4 sampleValue = tex2D(DepthBufferSampler, uv);
#if IS_DEPTHBUFFER_RAWZ
    float3 rawBytes = floor(255.0 * sampleValue.arg + 0.5);
    float3 scaler = float3(0.9960938093718177, 0.003890991442858663, 0.00001519918532366665);
    return dot(rawBytes, scaler / 255.0);
#else
    return sampleValue.r;
#endif
}

float LinearEyeDistance(float rawDepth)
{
    float denominator = rawDepth - gProjectionMainScene[2][2];
    if (abs(denominator) < 0.000001)
        denominator = (denominator < 0.0) ? -0.000001 : 0.000001;
    return abs(gProjectionMainScene[3][2] / denominator);
}

float3 EncodeDepth24(float value)
{
    value = min(saturate(value), 0.999999);
    float3 encoded = frac(value * float3(1.0, 255.0, 65025.0));
    encoded -= encoded.yzz * float3(1.0 / 255.0, 1.0 / 255.0, 0.0);
    return encoded;
}

float4 DepthExtractPS(float2 uv : TEXCOORD0) : COLOR0
{
    float rawDepth = ReadRawDepth(uv);
    float normalizedDistance = saturate(LinearEyeDistance(rawDepth) / max(FarPlane, 1.0));
    return float4(EncodeDepth24(normalizedDistance), 1.0);
}

technique DepthExtract
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_2_0 DepthExtractPS();
    }
}

// MTA will select this safe technique when the driver's readable depth format
// cannot validate. Lua checks the returned technique name and disables depth
// effects rather than pretending that a depth image exists.
technique NoDepth
{
    pass P0
    {
    }
}

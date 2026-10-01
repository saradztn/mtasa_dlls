// Stage 1: sample the native-resolution screen source and downsample it into
// the persistent internal-resolution target. This is post-process scaling only;
// MTA does not expose a way for a resource to render the GTA scene at this size.
texture SceneTexture;
float2 SourceTexelSize;
float ScaleFactor;
float2 Jitter;

sampler SceneSampler = sampler_state
{
    Texture = (SceneTexture);
    MinFilter = Linear;
    MagFilter = Linear;
    MipFilter = None;
    AddressU = Clamp;
    AddressV = Clamp;
};

float4 SceneCapturePS(float2 uv : TEXCOORD0) : COLOR0
{
    float2 jitteredUV = saturate(uv + Jitter * SourceTexelSize);
    if (ScaleFactor > 0.995)
        return tex2D(SceneSampler, jitteredUV);

    // Four-tap box reconstruction approximates the footprint of one internal
    // pixel and prevents a single bilinear sample from aliasing thin features.
    float scale = max(ScaleFactor, 0.25);
    float2 footprint = SourceTexelSize * (0.5 / scale);
    float4 c0 = tex2D(SceneSampler, saturate(jitteredUV + float2(-footprint.x, -footprint.y)));
    float4 c1 = tex2D(SceneSampler, saturate(jitteredUV + float2( footprint.x, -footprint.y)));
    float4 c2 = tex2D(SceneSampler, saturate(jitteredUV + float2(-footprint.x,  footprint.y)));
    float4 c3 = tex2D(SceneSampler, saturate(jitteredUV + float2( footprint.x,  footprint.y)));
    return (c0 + c1 + c2 + c3) * 0.25;
}

technique Main
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_2_0 SceneCapturePS();
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

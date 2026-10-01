// Stage 7: restrained depth-only screen-space ambient-occlusion approximation.
// GTA/MTA does not expose a normal buffer to a normal resource, so this estimates
// short-range occlusion from linear depth and intentionally clamps its strength.
// The eight-tap implementation uses PS 3.0; older cards select the copy fallback
// rather than compiling an instruction-overflowing PS 2.0 shader.
texture SceneTexture;
texture DepthTexture;
texture NoiseTexture;
float2 TexelSize;
float2 NoiseScale;
float AORadius;
float AOStrength;
float UseDepth;
float DebugOutput;

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
sampler NoiseSampler = sampler_state
{
    Texture = (NoiseTexture);
    MinFilter = Point;
    MagFilter = Point;
    MipFilter = None;
    AddressU = Wrap;
    AddressV = Wrap;
};

float DecodeDepth24(float3 encoded)
{
    return encoded.r + encoded.g / 255.0 + encoded.b / 65025.0;
}
float SampleOcclusion(float centerDepth, float2 uv, float2 offset)
{
    float sampleDepth = DecodeDepth24(tex2D(DepthSampler, saturate(uv + offset)).rgb);
    float delta = centerDepth - sampleDepth;
    // Ignore very large silhouette jumps; retain a short, depth-local contact term.
    float localRange = 0.012 + centerDepth * 0.025;
    return saturate((delta - 0.0018) / max(localRange, 0.002))
         * (1.0 - saturate((delta - localRange) * 55.0));
}

float4 SSAOPS(float2 uv : TEXCOORD0) : COLOR0
{
    float4 source = tex2D(SceneSampler, uv);
    if (UseDepth < 0.5)
        return source;

    float centerDepth = DecodeDepth24(tex2D(DepthSampler, uv).rgb);
    if (centerDepth > 0.985)
        return DebugOutput > 0.5 ? float4(1.0, 1.0, 1.0, 1.0) : source;

    float noise = tex2D(NoiseSampler, uv * NoiseScale).r;
    float angle = noise * 6.2831853;
    float2 rotation = float2(cos(angle), sin(angle));
    float2 axisX = float2(rotation.x, rotation.y);
    float2 axisY = float2(-rotation.y, rotation.x);
    float2 diagA = normalize(axisX + axisY);
    float2 diagB = normalize(axisX - axisY);
    float radius = max(AORadius, 0.5);

    float occlusion = 0.0;
    occlusion += SampleOcclusion(centerDepth, uv, axisX * TexelSize * radius);
    occlusion += SampleOcclusion(centerDepth, uv, -axisX * TexelSize * radius);
    occlusion += SampleOcclusion(centerDepth, uv, axisY * TexelSize * radius);
    occlusion += SampleOcclusion(centerDepth, uv, -axisY * TexelSize * radius);
    occlusion += SampleOcclusion(centerDepth, uv, diagA * TexelSize * radius * 1.35);
    occlusion += SampleOcclusion(centerDepth, uv, -diagA * TexelSize * radius * 1.35);
    occlusion += SampleOcclusion(centerDepth, uv, diagB * TexelSize * radius * 1.35);
    occlusion += SampleOcclusion(centerDepth, uv, -diagB * TexelSize * radius * 1.35);

    occlusion = saturate(occlusion * 0.125);
    float ao = saturate(occlusion * saturate(AOStrength) * 1.8);
    if (DebugOutput > 0.5)
        return float4(1.0 - ao, 1.0 - ao, 1.0 - ao, 1.0);
    return float4(source.rgb * (1.0 - ao), source.a);
}

technique Main
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_3_0 SSAOPS();
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

// Stage 8: short view-space screen-space reflection ray march. Surface normals
// are reconstructed from depth gradients (not a true normal buffer), so SSR is
// conservative, optional and disabled on unsupported/no-depth devices. The ray
// marcher uses PS 3.0; older devices select the copy fallback rather than an
// over-budget PS 2.0 shader.
texture SceneTexture;
texture DepthTexture;
texture RayNoiseTexture;
float2 TexelSize;
float2 NoiseScale;
float FarPlane;
float2 FocalScale;
float RayLength;
float Thickness;
float SSRStrength;
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
sampler RayNoiseSampler = sampler_state
{
    Texture = (RayNoiseTexture);
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
float SampleLinearDepth(float2 uv)
{
    return DecodeDepth24(tex2D(DepthSampler, saturate(uv)).rgb) * max(FarPlane, 1.0);
}
float3 ReconstructViewPosition(float2 uv, float depth)
{
    float x = (uv.x - 0.5) * depth / max(FocalScale.x, 0.05);
    float y = (0.5 - uv.y) * depth / max(FocalScale.y, 0.05);
    return float3(x, y, depth);
}
float2 ProjectViewPosition(float3 position)
{
    float z = max(position.z, 0.05);
    return float2(position.x * FocalScale.x / z + 0.5,
                  0.5 - position.y * FocalScale.y / z);
}

float TraceStep(float2 originalUV, float3 origin, float3 direction, float stepDistance, out float2 hitUV)
{
    float3 rayPosition = origin + direction * stepDistance;
    hitUV = ProjectViewPosition(rayPosition);
    if (rayPosition.z <= origin.z + 0.15 || hitUV.x <= 0.002 || hitUV.x >= 0.998 || hitUV.y <= 0.002 || hitUV.y >= 0.998)
        return 0.0;

    float sceneDepth = SampleLinearDepth(hitUV);
    float separation = rayPosition.z - sceneDepth;
    float thickness = max(Thickness, 0.5) + stepDistance * 0.015;
    float valid = step(0.0, separation) * (1.0 - step(thickness, separation));
    // Avoid immediate self-hits close to the originating depth sample.
    valid *= step(0.006, abs(hitUV.x - originalUV.x) + abs(hitUV.y - originalUV.y));
    return valid;
}

float4 SSRPS(float2 uv : TEXCOORD0) : COLOR0
{
    float4 source = tex2D(SceneSampler, uv);
    if (UseDepth < 0.5)
        return source;

    float centerDepth = SampleLinearDepth(uv);
    if (centerDepth > FarPlane * 0.985)
        return DebugOutput > 0.5 ? float4(0.0, 0.0, 0.0, 1.0) : source;

    float2 uL = uv - float2(TexelSize.x, 0.0);
    float2 uR = uv + float2(TexelSize.x, 0.0);
    float2 uU = uv - float2(0.0, TexelSize.y);
    float2 uD = uv + float2(0.0, TexelSize.y);
    float3 pL = ReconstructViewPosition(uL, SampleLinearDepth(uL));
    float3 pR = ReconstructViewPosition(uR, SampleLinearDepth(uR));
    float3 pU = ReconstructViewPosition(uU, SampleLinearDepth(uU));
    float3 pD = ReconstructViewPosition(uD, SampleLinearDepth(uD));
    float3 normal = normalize(cross(pR - pL, pD - pU));
    if (normal.z > 0.0)
        normal = -normal;

    float3 origin = ReconstructViewPosition(uv, centerDepth);
    float3 incident = normalize(origin);
    float3 rayDirection = normalize(reflect(incident, normal));
    float3 viewDirection = normalize(-origin);
    float fresnel = pow(1.0 - saturate(dot(normal, viewDirection)), 5.0);

    float2 hitUV = uv;
    float hit = 0.0;
    float2 candidateUV;
    float rayNoise = tex2D(RayNoiseSampler, uv * NoiseScale).r - 0.5;
    float stepDistance = (max(RayLength, 1.0) / 6.0) * (1.0 + rayNoise * 0.24);
    if (rayDirection.z > 0.02)
    {
        float value = TraceStep(uv, origin, rayDirection, stepDistance, candidateUV);
        if (value > 0.5) { hit = 1.0; hitUV = candidateUV; }
        value = TraceStep(uv, origin, rayDirection, stepDistance * 2.0, candidateUV);
        if (hit < 0.5 && value > 0.5) { hit = 1.0; hitUV = candidateUV; }
        value = TraceStep(uv, origin, rayDirection, stepDistance * 3.0, candidateUV);
        if (hit < 0.5 && value > 0.5) { hit = 1.0; hitUV = candidateUV; }
        value = TraceStep(uv, origin, rayDirection, stepDistance * 4.0, candidateUV);
        if (hit < 0.5 && value > 0.5) { hit = 1.0; hitUV = candidateUV; }
        value = TraceStep(uv, origin, rayDirection, stepDistance * 5.0, candidateUV);
        if (hit < 0.5 && value > 0.5) { hit = 1.0; hitUV = candidateUV; }
        value = TraceStep(uv, origin, rayDirection, stepDistance * 6.0, candidateUV);
        if (hit < 0.5 && value > 0.5) { hit = 1.0; hitUV = candidateUV; }
    }

    float edgeFade = saturate(min(min(hitUV.x, 1.0 - hitUV.x), min(hitUV.y, 1.0 - hitUV.y)) * 12.0);
    float confidence = hit * edgeFade * (0.18 + 0.82 * fresnel);
    if (DebugOutput > 0.5)
        return float4(confidence, confidence, confidence, 1.0);

    float3 reflectedColor = tex2D(SceneSampler, hitUV).rgb;
    float blend = saturate(SSRStrength) * confidence;
    return float4(lerp(source.rgb, reflectedColor, blend), source.a);
}

technique Main
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_3_0 SSRPS();
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

//=============================================================================
// NextGenPoliceDepartment - 4K Spatial Upscaler Pass 1: Edge-Adaptive Spatial
// Upsampling (AMD FSR 1.0 EASU-Style 12-Tap Anisotropic Lanczos2 Reconstruction)
// Hardware Target: AMD Radeon RX 580 2048SP (Polaris 20 XL) / DirectX 9 ps_3_0
//=============================================================================

texture gInputTex;
float2  gInputSize  = float2(1920.0, 1080.0);
float2  gInputInv   = float2(1.0 / 1920.0, 1.0 / 1080.0);
float2  gOutputSize = float2(3840.0, 2160.0);
float   gEdgeSharpness = 1.0;

// Optional Screen-Space Golden-Hour Solar Disc & Atmospheric Bloom
float3  gSunScreenPos  = float3(0.5, 0.25, 0.0); // xy = UV, z = visible weight (0..1)
float3  gSunAtmosColor = float3(1.00, 0.76, 0.46);
float   gAtmosBloom    = 0.35;

sampler2D InputSampler = sampler_state
{
    Texture = (gInputTex);
    MinFilter = Point;
    MagFilter = Linear;
    MipFilter = None;
    AddressU = Clamp;
    AddressV = Clamp;
};

float EASULuma(float3 rgb)
{
    return dot(rgb, float3(0.299, 0.587, 0.114));
}

// Fast polynomial approximation of windowed Lanczos2 kernel (as in AMD FSR 1.0 EASU)
float EASULanczos2(float d2, float lobe)
{
    d2 = min(d2, 2.5);
    float wB = (2.0 / 5.0) * d2 - 1.0;
    float wA = lobe * d2 - 1.0;
    wB *= wB;
    wA *= wA;
    return (25.0 / 16.0) * wB * wA - (25.0 / 16.0 - 1.0);
}

float4 EASUPS_High(float2 uv : TEXCOORD0) : COLOR0
{
    // Continuous texel coordinate in internal render space
    float2 pp = uv * gInputSize - 0.5;
    float2 fp = floor(pp);
    float2 f  = pp - fp; // Sub-pixel fractional offset in [0, 1)
    float2 baseUV = (fp + 0.5) * gInputInv;

    // Fetch 12-tap cross neighborhood around the 2x2 central quad:
    //        [ b ] [ c ]
    //  [ e ] [ f ] [ g ] [ h ]
    //  [ i ] [ j ] [ k ] [ l ]
    //        [ n ] [ o ]
    float3 c_b = tex2D(InputSampler, baseUV + float2( 0.0, -1.0) * gInputInv).rgb;
    float3 c_c = tex2D(InputSampler, baseUV + float2( 1.0, -1.0) * gInputInv).rgb;
    float3 c_e = tex2D(InputSampler, baseUV + float2(-1.0,  0.0) * gInputInv).rgb;
    float3 c_f = tex2D(InputSampler, baseUV + float2( 0.0,  0.0) * gInputInv).rgb;
    float3 c_g = tex2D(InputSampler, baseUV + float2( 1.0,  0.0) * gInputInv).rgb;
    float3 c_h = tex2D(InputSampler, baseUV + float2( 2.0,  0.0) * gInputInv).rgb;
    float3 c_i = tex2D(InputSampler, baseUV + float2(-1.0,  1.0) * gInputInv).rgb;
    float3 c_j = tex2D(InputSampler, baseUV + float2( 0.0,  1.0) * gInputInv).rgb;
    float3 c_k = tex2D(InputSampler, baseUV + float2( 1.0,  1.0) * gInputInv).rgb;
    float3 c_l = tex2D(InputSampler, baseUV + float2( 2.0,  1.0) * gInputInv).rgb;
    float3 c_n = tex2D(InputSampler, baseUV + float2( 0.0,  2.0) * gInputInv).rgb;
    float3 c_o = tex2D(InputSampler, baseUV + float2( 1.0,  2.0) * gInputInv).rgb;

    float l_b = EASULuma(c_b), l_c = EASULuma(c_c);
    float l_e = EASULuma(c_e), l_f = EASULuma(c_f), l_g = EASULuma(c_g), l_h = EASULuma(c_h);
    float l_i = EASULuma(c_i), l_j = EASULuma(c_j), l_k = EASULuma(c_k), l_l = EASULuma(c_l);
    float l_n = EASULuma(c_n), l_o = EASULuma(c_o);

    // Compute local bilinear-weighted edge gradient direction (dir) and anisotropy (len)
    float gradX = (l_g - l_e) * (1.0 - f.y) + (l_k - l_i) * f.y + (l_h - l_f) * (1.0 - f.y) + (l_l - l_j) * f.y;
    float gradY = (l_j - l_b) * (1.0 - f.x) + (l_k - l_c) * f.x + (l_n - l_f) * (1.0 - f.x) + (l_o - l_g) * f.x;
    float2 dir = float2(gradX, gradY);
    float dirLen2 = dot(dir, dir);
    dir = dirLen2 > 1e-5 ? (dir * rsqrt(dirLen2)) : float2(1.0, 0.0);

    // Anisotropic stretch factor along detected edge tangent
    float edgeMag = saturate(sqrt(dirLen2) * 2.2 * gEdgeSharpness);
    float2 stretch = float2(1.0 + edgeMag * 0.42, 1.0 - edgeMag * 0.26);
    float lobe = -0.50 + 0.12 * edgeMag;

    // Clamping bounding box from 2x2 inner quad to prevent Lanczos ringing/overshoot
    float3 minRGB = min(min(c_f, c_g), min(c_j, c_k));
    float3 maxRGB = max(max(c_f, c_g), max(c_j, c_k));

    float3 accum = float3(0, 0, 0);
    float  wSum  = 0.0;

    float2 offsets[12] = {
        float2( 0.0, -1.0), float2( 1.0, -1.0),
        float2(-1.0,  0.0), float2( 0.0,  0.0), float2( 1.0,  0.0), float2( 2.0,  0.0),
        float2(-1.0,  1.0), float2( 0.0,  1.0), float2( 1.0,  1.0), float2( 2.0,  1.0),
        float2( 0.0,  2.0), float2( 1.0,  2.0)
    };
    float3 taps[12] = { c_b, c_c, c_e, c_f, c_g, c_h, c_i, c_j, c_k, c_l, c_n, c_o };

    [unroll]
    for (int idx = 0; idx < 12; idx++)
    {
        float2 v = offsets[idx] - f;
        // Rotate offset into local edge coordinate frame
        float2 rotV = float2(
            v.x * dir.x + v.y * dir.y,
           -v.x * dir.y + v.y * dir.x
        ) * stretch;
        float w = EASULanczos2(dot(rotV, rotV), lobe);
        accum += taps[idx] * w;
        wSum  += w;
    }

    float3 result = clamp(accum / max(1e-4, wSum), minRGB * 0.94, maxRGB * 1.06);

    // Optional screen-space Golden-Hour Solar Disc & Mie Horizon Bloom
    if (gSunScreenPos.z > 0.01 && gAtmosBloom > 0.01)
    {
        float2 aspectDelta = (uv - gSunScreenPos.xy) * float2(gOutputSize.x / max(1.0, gOutputSize.y), 1.0);
        float sunDist = length(aspectDelta);
        float solarCore = exp(-sunDist * 26.0) * 0.72;
        float solarHalo = exp(-sunDist * 4.2) * 0.24;
        result += gSunAtmosColor * (solarCore + solarHalo) * gSunScreenPos.z * gAtmosBloom;
    }

    return float4(saturate(result), 1.0);
}

// Fast 5-tap edge-aware upscale fallback for Shader Model 2.0 hardware
float4 EASUPS_Low(float2 uv : TEXCOORD0) : COLOR0
{
    float3 c0 = tex2D(InputSampler, uv).rgb;
    float3 cN = tex2D(InputSampler, uv + float2(0.0, -gInputInv.y)).rgb;
    float3 cS = tex2D(InputSampler, uv + float2(0.0,  gInputInv.y)).rgb;
    float3 cW = tex2D(InputSampler, uv + float2(-gInputInv.x, 0.0)).rgb;
    float3 cE = tex2D(InputSampler, uv + float2( gInputInv.x, 0.0)).rgb;
    float3 avg = (cN + cS + cW + cE) * 0.25;
    float3 res = saturate(c0 + (c0 - avg) * (0.25 * gEdgeSharpness));
    return float4(res, 1.0);
}

technique ngpd_upscale_easu_high
{
    pass P0
    {
        PixelShader = compile ps_3_0 EASUPS_High();
    }
}

technique ngpd_upscale_easu_low
{
    pass P0
    {
        PixelShader = compile ps_2_0 EASUPS_Low();
    }
}

technique fallback
{
    pass P0
    {
        Texture[0] = gInputTex;
    }
}

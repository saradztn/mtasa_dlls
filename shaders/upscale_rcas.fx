//=============================================================================
// NextGenPoliceDepartment - 4K Spatial Upscaler Pass 2: Robust Contrast-
// Adaptive Sharpening (AMD FSR 1.0 RCAS 5-Tap Ringing-Free Filter)
// Hardware Target: AMD Radeon RX 580 2048SP (Polaris 20 XL) / DirectX 9 ps_3_0
//=============================================================================

texture gUpscaledTex;
float2  gTexelSize = float2(1.0 / 3840.0, 1.0 / 2160.0);
float   gSharpness = 0.72; // 0.0 = off, 1.0 = maximum contrast-adaptive sharpening
float   gFilmGrain = 0.015;
float   gTime      = 0.0;

sampler2D UpscaledSampler = sampler_state
{
    Texture = (gUpscaledTex);
    MinFilter = Linear;
    MagFilter = Linear;
    MipFilter = None;
    AddressU = Clamp;
    AddressV = Clamp;
};

float RCASLuma(float3 rgb)
{
    return dot(rgb, float3(0.299, 0.587, 0.114));
}

float4 RCASPS_High(float2 uv : TEXCOORD0) : COLOR0
{
    float3 e = tex2D(UpscaledSampler, uv).rgb;
    float3 b = tex2D(UpscaledSampler, uv + float2( 0.0, -gTexelSize.y)).rgb;
    float3 d = tex2D(UpscaledSampler, uv + float2(-gTexelSize.x,  0.0)).rgb;
    float3 f = tex2D(UpscaledSampler, uv + float2( gTexelSize.x,  0.0)).rgb;
    float3 h = tex2D(UpscaledSampler, uv + float2( 0.0,  gTexelSize.y)).rgb;

    float bL = RCASLuma(b);
    float dL = RCASLuma(d);
    float eL = RCASLuma(e);
    float fL = RCASLuma(f);
    float hL = RCASLuma(h);

    // Local 4-neighbor min and max luminance
    float min4L = min(min(bL, dL), min(fL, hL));
    float max4L = max(max(bL, dL), max(fL, hL));

    // Analytical RCAS lobe limit ensuring sharpened output stays strictly within [0, 1]
    // and never introduces bright/dark ringing halos around high-contrast edges
    float hitMin = min(min4L, eL) / max(1e-4, 4.0 * max4L);
    float hitMax = (1.0 - max(max4L, eL)) / max(1e-4, 4.0 * min4L - 4.0);
    float lobe = max(-hitMin, hitMax);
    lobe = max(-0.22, min(0.0, lobe)) * saturate(gSharpness);

    // Noise suppression on flat micro-grain regions
    float localContrast = max4L - min4L;
    float noiseSuppress = saturate(localContrast * 8.0);
    lobe *= noiseSuppress;

    float rcpWeight = 1.0 / (1.0 + 4.0 * lobe);
    float3 sharpened = (e + lobe * (b + d + f + h)) * rcpWeight;

    // Clamp to 5-tap neighborhood hull
    float3 minRGB = min(e, min(min(b, d), min(f, h)));
    float3 maxRGB = max(e, max(max(b, d), max(f, h)));
    sharpened = clamp(sharpened, minRGB, maxRGB);

    return float4(saturate(sharpened), 1.0);
}

float4 RCASPS_Low(float2 uv : TEXCOORD0) : COLOR0
{
    float3 e = tex2D(UpscaledSampler, uv).rgb;
    float3 n = (
        tex2D(UpscaledSampler, uv + float2( 0.0, -gTexelSize.y)).rgb +
        tex2D(UpscaledSampler, uv + float2(-gTexelSize.x,  0.0)).rgb +
        tex2D(UpscaledSampler, uv + float2( gTexelSize.x,  0.0)).rgb +
        tex2D(UpscaledSampler, uv + float2( 0.0,  gTexelSize.y)).rgb
    ) * 0.25;
    float3 res = saturate(e + (e - n) * (0.35 * gSharpness));
    return float4(res, 1.0);
}

technique ngpd_upscale_rcas_high
{
    pass P0
    {
        PixelShader = compile ps_3_0 RCASPS_High();
    }
}

technique ngpd_upscale_rcas_low
{
    pass P0
    {
        PixelShader = compile ps_2_0 RCASPS_Low();
    }
}

technique fallback
{
    pass P0
    {
        Texture[0] = gUpscaledTex;
    }
}

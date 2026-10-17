//=============================================================================
// asphalt.fx - NextGenPoliceDepartment
// Ultra-Realistic Wet Asphalt, Fine Cracks, Tire Wear & Standing Puddles
//=============================================================================
#include "ngpd_common.fxh"

float2 Ripple(float2 uv, float t)
{
    float2 acc = 0;
    [unroll]
    for (int k = 0; k < 4; k++)
    {
        float2 cell = floor(uv * 3.0 + k * 0.37);
        float2 rnd = frac(sin(float2(dot(cell, float2(12.9898, 78.233)), dot(cell, float2(39.35, 11.13)))) * 43758.5453);
        float2 c = (cell + rnd) / 3.0 - k * 0.37 / 3.0;
        float phase = frac(t * 0.9 + rnd.x);
        float2 d = uv - c;
        float r = length(d) + 1e-4;
        float ring = sin((r - phase * 0.3) * 60.0) * saturate(1.0 - abs(r - phase * 0.3) * 18.0) * (1.0 - phase);
        acc += d / r * ring;
    }
    // Add subtle wind-driven capillary waves across standing puddles
    float2 windWave = float2(
        sin(uv.x * 7.5 + uv.y * 2.8 + t * 2.1),
        cos(uv.y * 8.2 - uv.x * 2.3 + t * 1.8)
    ) * (0.045 * gWindStrength);
    return acc * 0.25 + windWave;
}

float4 PS_High(PSIn p) : COLOR0
{
    Surface s = NGPD_Sample(p);

    // Non-repeating world-space depression puddles + wheel-track wear variation
    float w1 = sin(p.WorldPos.x * 0.085 + cos(p.WorldPos.y * 0.072) * 1.6);
    float w2 = cos(p.WorldPos.y * 0.105 - sin(p.WorldPos.x * 0.095) * 1.4);
    float worldBasin = saturate(w1 * w2 * 0.50 + 0.45);
    s.mask = saturate(s.mask * 0.68 + worldBasin * 0.48);

    float puddle = NGPD_ApplyWet(s);
    if (puddle > 0.01)
    {
        float rippleAmt = saturate(gRain + 0.12 * gWindStrength) * puddle;
        float2 rp = Ripple(p.WorldPos.xy * 0.5, gTime) * rippleAmt;
        s.n = normalize(s.n + normalize(p.T) * rp.x + normalize(p.B) * rp.y);
    }
    float3 c = NGPD_Shade(p, s, puddle, p.Diffuse.rgb);
    return NGPD_Finish(p, c, s.alpha * p.Diffuse.a);
}

technique ngpd_asphalt_high
{
    pass P0
    {
        VertexShader = compile vs_3_0 NGPD_VS();
        PixelShader  = compile ps_3_0 PS_High();
    }
}

technique ngpd_asphalt_low
{
    pass P0
    {
        VertexShader = compile vs_2_0 NGPD_VS_Low();
        PixelShader  = compile ps_2_0 NGPD_PS_Low();
    }
}

technique fallback
{
    pass P0
    {
        Texture[0] = gTexture0;
    }
}

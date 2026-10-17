//
// asphalt.fx - NextGenPoliceDepartment
// Asphalt / road paint: puddles from the wet mask, procedural rain ripples on puddles while it rains
// (normal perturbation from expanding rings, driven by TIME), stronger sky env term on water.
//
#include "ngpd_common.fxh"

float2 Ripple(float2 uv, float t)
{
    // 4 phase-shifted ring cells -> radial normal offsets
    float2 acc = 0;
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
    return acc * 0.25;
}

float4 PS_High(PSIn p) : COLOR0
{
    Surface s = NGPD_Sample(p);
    float puddle = NGPD_ApplyWet(s);
    if (puddle > 0.01 && gRain > 0.01)
    {
        float2 rp = Ripple(p.WorldPos.xy * 0.5, gTime) * gRain * puddle;
        s.n = normalize(s.n + normalize(p.T) * rp.x + normalize(p.B) * rp.y);
    }
    float3 c = NGPD_Shade(p, s, puddle, p.Diffuse.rgb);
    return NGPD_Finish(p, c, s.alpha * p.Diffuse.a);
}

//---------------------------------------------------------------- techniques
// MTA uses the first technique that validates on the client GPU.
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

// Fixed-function fallback: texture x vertex colour (identical to the unshaded look)
technique fallback
{
    pass P0
    {
        Texture[0] = gTexture0;
    }
}

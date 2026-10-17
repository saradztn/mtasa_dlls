//
// concrete.fx - NextGenPoliceDepartment
// Concrete / masonry: porous darkening with wet-edge band, AO-weighted moisture (water lingers in
// cavities: low AO texels darken first) and roughness kept high except where puddles form.
//
#include "ngpd_common.fxh"

float4 PS_High(PSIn p) : COLOR0
{
    Surface s = NGPD_Sample(p);
    float wm = gWetness * gWetFactor * (1.0 - gInterior);
    // cavities soak first: extra darkening scaled by (1 - ao) while wetness rises
    s.albedo *= 1.0 - 0.25 * wm * (1.0 - s.ao);
    float puddle = NGPD_ApplyWet(s);
    // concrete never becomes mirror-like outside puddles
    s.rough = max(s.rough, lerp(0.30, 0.03, puddle));
    float3 c = NGPD_Shade(p, s, puddle, p.Diffuse.rgb);
    return NGPD_Finish(p, c, s.alpha * p.Diffuse.a);
}

//---------------------------------------------------------------- techniques
// MTA uses the first technique that validates on the client GPU.
technique ngpd_concrete_high
{
    pass P0
    {
        VertexShader = compile vs_3_0 NGPD_VS();
        PixelShader  = compile ps_3_0 PS_High();
    }
}

technique ngpd_concrete_low
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

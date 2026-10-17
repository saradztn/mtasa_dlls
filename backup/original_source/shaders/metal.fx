//
// metal.fx - NextGenPoliceDepartment
// Metals and painted metal: metal map / gMetallic driven F0, stronger env term with sky / ceiling
// colour, water beading (wet = lower roughness, no porosity darkening on bare metal).
//
#include "ngpd_common.fxh"

float4 PS_High(PSIn p) : COLOR0
{
    Surface s = NGPD_Sample(p);
    // bare metal does not soak: porosity darkening only on non-metallic (painted/dirty) texels
    float puddle = NGPD_ApplyWetP(s, gPorosity * (1.0 - 0.9 * s.metal));
    float3 c = NGPD_Shade(p, s, puddle, p.Diffuse.rgb);
    return NGPD_Finish(p, c, s.alpha * p.Diffuse.a);
}

//---------------------------------------------------------------- techniques
// MTA uses the first technique that validates on the client GPU.
technique ngpd_metal_high
{
    pass P0
    {
        VertexShader = compile vs_3_0 NGPD_VS();
        PixelShader  = compile ps_3_0 PS_High();
    }
}

technique ngpd_metal_low
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

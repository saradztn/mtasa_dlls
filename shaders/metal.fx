//=============================================================================
// metal.fx - NextGenPoliceDepartment
// Architectural Aluminum, Brushed Steel, Mullions & Painted Metal
//=============================================================================
#include "ngpd_common.fxh"

float4 PS_High(PSIn p) : COLOR0
{
    Surface s = NGPD_Sample(p);
    float puddle = NGPD_ApplyWetP(s, gPorosity * (1.0 - 0.9 * s.metal));
    float3 c = NGPD_Shade(p, s, puddle, p.Diffuse.rgb);
    return NGPD_Finish(p, c, s.alpha * p.Diffuse.a);
}

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

technique fallback
{
    pass P0
    {
        Texture[0] = gTexture0;
    }
}

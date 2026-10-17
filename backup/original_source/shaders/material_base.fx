//
// material_base.fx - NextGenPoliceDepartment
// Generic PBR-approximation surface: albedo (TXD) + normal + surface maps + wet model.
// Used by plaster, wood, fabric, plastic, ceiling, signage/emissive and any material without a dedicated shader.
//
#include "ngpd_common.fxh"

float4 PS_High(PSIn p) : COLOR0
{
    Surface s = NGPD_Sample(p);
    float puddle = NGPD_ApplyWet(s);
    float3 c = NGPD_Shade(p, s, puddle, p.Diffuse.rgb);
    return NGPD_Finish(p, c, s.alpha * p.Diffuse.a);
}

//---------------------------------------------------------------- techniques
// MTA uses the first technique that validates on the client GPU.
technique ngpd_material_base_high
{
    pass P0
    {
        VertexShader = compile vs_3_0 NGPD_VS();
        PixelShader  = compile ps_3_0 PS_High();
    }
}

technique ngpd_material_base_low
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

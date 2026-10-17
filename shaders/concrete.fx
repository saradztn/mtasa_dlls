//=============================================================================
// concrete.fx - NextGenPoliceDepartment
// Architectural Precast Concrete, Masonry, Sidewalks & Plaza Granite
//=============================================================================
#include "ngpd_common.fxh"

float4 PS_High(PSIn p) : COLOR0
{
    Surface s = NGPD_Sample(p);
    float wm = gWetness * gWetFactor * (1.0 - gInterior);

    // Rainwater runoff streaks on vertical facade panels & cavity moisture retention
    float vertFace = saturate(1.0 - abs(s.ng.z));
    float streak = sin(p.WorldPos.x * 4.2 + sin(p.WorldPos.y * 3.6) * 1.4) * 0.5 + 0.5;
    float dampBand = vertFace * wm * streak * 0.16;

    s.albedo *= (1.0 - 0.25 * wm * (1.0 - s.ao)) * (1.0 - dampBand);
    float wBasin = saturate(sin(p.WorldPos.x * 0.13 + 0.7) * cos(p.WorldPos.y * 0.13 - 0.4) * 0.48 + 0.44);
    s.mask = saturate(s.mask * 0.72 + wBasin * 0.40);

    float puddle = NGPD_ApplyWet(s);
    s.rough = max(s.rough - dampBand * 0.35, lerp(0.28, 0.025, puddle));
    float3 c = NGPD_Shade(p, s, puddle, p.Diffuse.rgb);
    return NGPD_Finish(p, c, s.alpha * p.Diffuse.a);
}

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

technique fallback
{
    pass P0
    {
        Texture[0] = gTexture0;
    }
}

//=============================================================================
// floor.fx - NextGenPoliceDepartment
// Polished Stone, Terrazzo, Epoxy & Interior Tile Shader
//=============================================================================
#include "ngpd_common.fxh"

float4 PS_High(PSIn p) : COLOR0
{
    Surface s = NGPD_Sample(p);
    float puddle = NGPD_ApplyWet(s);
    float3 V = normalize(gCameraPosition - p.WorldPos);
    float3 c = NGPD_Shade(p, s, puddle, p.Diffuse.rgb);
    if (gInterior > 0.5)
    {
        float g = (1.0 - s.rough);
        float3 R = reflect(-V, s.n);
        float band = pow(saturate(R.z), 24.0 * g + 2.0) * g * g;
        c += gIndoorEnv * band * gSpec * 0.65 * gReflectScale;
    }
    return NGPD_Finish(p, c, s.alpha * p.Diffuse.a);
}

technique ngpd_floor_high
{
    pass P0
    {
        VertexShader = compile vs_3_0 NGPD_VS();
        PixelShader  = compile ps_3_0 PS_High();
    }
}

technique ngpd_floor_low
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

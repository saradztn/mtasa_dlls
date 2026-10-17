//=============================================================================
// wet.fx - NextGenPoliceDepartment
// Wet Ground, Grass, Mulch, Fence & Painted Marking Shader
//=============================================================================
#include "ngpd_common.fxh"

float4 PS_High(PSIn p) : COLOR0
{
    float4 a = tex2D(SampAlbedo, p.TexCoord);
    float wm = gWetness * gWetFactor * (1.0 - gInterior);
    float3 n = normalize(p.N);
    float3 V = normalize(gCameraPosition - p.WorldPos);
    float fres = 0.02 + 0.98 * pow(1.0 - saturate(abs(dot(n, V))), 5.0);
    float3 env = NGPD_SkyEnv(reflect(-V, n), p.WorldPos, 0.25);
    float3 c = a.rgb * p.Diffuse.rgb * (1.0 - gPorosity * 0.45 * wm);
    c += env * fres * wm * 0.38 * gReflectScale * saturate(dot(p.Diffuse.rgb, 0.33) * 1.6);
    c = NGPD_ToneMapACES(c);
    return NGPD_Finish(p, c, a.a * p.Diffuse.a);
}

technique ngpd_wet_high
{
    pass P0
    {
        VertexShader = compile vs_3_0 NGPD_VS();
        PixelShader  = compile ps_3_0 PS_High();
    }
}

technique ngpd_wet_low
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

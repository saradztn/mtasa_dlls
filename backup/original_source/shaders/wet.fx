//
// wet.fx - NextGenPoliceDepartment
// Wet-only surface shader for materials without useful normal detail (grass, mulch, foliage cards,
// fence panels, paint lines): albedo x prelight with wetness darkening and a soft gloss lift.
//
#include "ngpd_common.fxh"

float4 PS_High(PSIn p) : COLOR0
{
    float4 a = tex2D(SampAlbedo, p.TexCoord);
    float wm = gWetness * gWetFactor * (1.0 - gInterior);
    float3 n = normalize(p.N);
    float3 V = normalize(gCameraPosition - p.WorldPos);
    float fres = 0.02 + 0.98 * pow(1.0 - saturate(abs(dot(n, V))), 5.0);
    float3 c = a.rgb * p.Diffuse.rgb * (1.0 - gPorosity * 0.45 * wm);
    c += gSkyColor * fres * wm * 0.35 * gReflectScale * saturate(dot(p.Diffuse.rgb, 0.33) * 1.6);
    return NGPD_Finish(p, c, a.a * p.Diffuse.a);
}

//---------------------------------------------------------------- techniques
// MTA uses the first technique that validates on the client GPU.
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

// Fixed-function fallback: texture x vertex colour (identical to the unshaded look)
technique fallback
{
    pass P0
    {
        Texture[0] = gTexture0;
    }
}

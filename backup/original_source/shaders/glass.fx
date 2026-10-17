//
// glass.fx - NextGenPoliceDepartment
// Glazing (alpha blended): tinted albedo alpha + Fresnel env reflection that also raises opacity at
// grazing angles; exterior panes get procedural rain streaks while wet.  Approximation only.
//
#include "ngpd_common.fxh"

float4 PS_High(PSIn p) : COLOR0
{
    Surface s = NGPD_Sample(p);
    float3 V = normalize(gCameraPosition - p.WorldPos);
    float3 n = s.ng * (dot(s.ng, V) < 0 ? -1.0 : 1.0);            // double-sided panes
    float wm = gWetness * gWetFactor * (1.0 - gInterior);
    float2 uv = p.TexCoord;
    float streak = 0.0;
    if (wm > 0.01)
    {
        float col = floor(uv.x * 40.0);
        float rnd = frac(sin(col * 91.7) * 43758.5);
        float y = frac(uv.y * 1.5 + gTime * (0.25 + rnd * 0.5) + rnd);
        streak = saturate(1.0 - abs(frac(uv.x * 40.0) - 0.5) * 8.0) * smoothstep(0.0, 0.08, y) * (1.0 - y) * wm;
        n = normalize(n + normalize(p.T) * streak * 0.4);
    }
    float ndv = saturate(dot(n, V));
    float fres = 0.04 + 0.96 * pow(1.0 - ndv, 5.0);
    float3 env = gInterior > 0.5 ? gIndoorEnv : gSkyColor;
    float3 refl = env * fres * gReflectScale;
    float3 L = normalize(gSunDir);
    float3 H = normalize(L + V);
    float spec = pow(saturate(dot(n, H)), 400.0) * 6.0 * gDayFactor * (1.0 - gInterior);
    float3 c = s.albedo * p.Diffuse.rgb + refl + gSunColor * spec;
    float a = saturate(s.alpha * p.Diffuse.a + fres * 0.5 + streak * 0.15);
    return NGPD_Finish(p, c, a);
}

//---------------------------------------------------------------- techniques
// MTA uses the first technique that validates on the client GPU.
technique ngpd_glass_high
{
    pass P0
    {
        VertexShader = compile vs_3_0 NGPD_VS();
        PixelShader  = compile ps_3_0 PS_High();
        AlphaBlendEnable = true;
        SrcBlend = SrcAlpha;
        DestBlend = InvSrcAlpha;
    }
}

technique ngpd_glass_low
{
    pass P0
    {
        VertexShader = compile vs_2_0 NGPD_VS_Low();
        PixelShader  = compile ps_2_0 NGPD_PS_Low();
        AlphaBlendEnable = true;
        SrcBlend = SrcAlpha;
        DestBlend = InvSrcAlpha;
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

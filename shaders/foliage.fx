//=============================================================================
// foliage.fx - NextGenPoliceDepartment
// Botanical Foliage & Bark with Wind Sway, Subsurface Scattering & Wet Sheen
//=============================================================================
#include "ngpd_common.fxh"

PSIn NGPD_VS_Foliage(VSIn v)
{
    PSIn o = (PSIn)0;
    float3 n = v.Normal;
    if (dot(n, n) < 1e-6) n = float3(0, 0, 1);
    n = normalize(n);
    float3 U, Up;
    NGPD_Frame(n, U, Up);

    float4 wp0 = mul(float4(v.Position, 1), gWorld);
    float fade = NGPD_DetailFade(wp0.xyz);

    // Subtle wind sway on elevated canopy branches & leaf tips
    float heightFactor = saturate((v.Position.z - 1.2) * 0.22) * (1.0 - gInterior * 0.85);
    float windPhase = wp0.x * 0.37 + wp0.y * 0.29 + gTime * 1.85;
    float flutterPhase = wp0.x * 2.4 - wp0.y * 2.1 + gTime * 4.5;
    float3 sway = float3(
        sin(windPhase) * 0.055 * heightFactor + cos(flutterPhase) * 0.015 * heightFactor,
        cos(windPhase * 0.85) * 0.048 * heightFactor + sin(flutterPhase * 1.1) * 0.015 * heightFactor,
        sin(flutterPhase * 0.9) * 0.012 * heightFactor
    ) * (gWindStrength * fade);

    float3 posLocal = v.Position + sway;
    float4 wp = mul(float4(posLocal, 1), gWorld);
    o.Position = mul(float4(posLocal, 1), gWorldViewProjection);
    o.WorldPos = wp.xyz;
    o.T = mul(U, (float3x3)gWorld);
    o.B = mul(Up, (float3x3)gWorld);
    o.N = mul(n, (float3x3)gWorld);
    o.TexCoord = v.TexCoord;
    o.Diffuse = NGPD_BuildingDiffuse(v.Diffuse);
    return o;
}

float4 PS_High(PSIn p) : COLOR0
{
    Surface s = NGPD_Sample(p);
    float3 V = normalize(gCameraPosition - p.WorldPos);
    if (dot(s.n, V) < 0.0)
    {
        s.n = -s.n;
        s.ng = -s.ng;
    }

    float puddle = NGPD_ApplyWet(s);
    float3 c = NGPD_Shade(p, s, puddle, p.Diffuse.rgb);

    // Golden-hour botanical subsurface scattering (warm chlorophyll glow when backlit by sunset sun)
    float3 L = normalize(gSunDir);
    float backLit = pow(saturate(dot(V, -L)), 3.0) * gDayFactor * (1.0 - gInterior);
    c += s.albedo * float3(1.15, 1.35, 0.55) * gSunColor * (backLit * 0.42);
    c = NGPD_ToneMapACES(c);
    return NGPD_Finish(p, c, s.alpha * p.Diffuse.a);
}

technique ngpd_foliage_high
{
    pass P0
    {
        VertexShader = compile vs_3_0 NGPD_VS_Foliage();
        PixelShader  = compile ps_3_0 PS_High();
    }
}

technique ngpd_foliage_low
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

//=============================================================================
// glass.fx - NextGenPoliceDepartment
// Architectural Curtain-Wall Glass with Golden-Hour Sky & Interior Room Glow
//=============================================================================
#include "ngpd_common.fxh"

float4 PS_High(PSIn p) : COLOR0
{
    Surface s = NGPD_Sample(p);
    float3 V = normalize(gCameraPosition - p.WorldPos);
    float3 n = s.ng * (dot(s.ng, V) < 0 ? -1.0 : 1.0);
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
    float fres = 0.06 + 0.94 * pow(1.0 - ndv, 4.5);
    float3 R = reflect(-V, n);
    float3 env = gInterior > 0.5 ? gIndoorEnv : NGPD_SkyEnv(R, p.WorldPos, 0.03);
    float3 refl = env * fres * gReflectScale;

    float3 L = normalize(gSunDir);
    float3 H = normalize(L + V);
    float specCore = pow(saturate(dot(n, H)), 380.0) * 5.5 * gDayFactor * (1.0 - gInterior);
    float specGlare = pow(saturate(dot(n, H)), 24.0) * 0.48 * gSunGlare * gDayFactor * (1.0 - gInterior);

    // Warm interior room glow visible through exterior glazing at sunset/dusk/night
    float duskGlow = saturate(1.15 - gDayFactor * 0.65) * (1.0 - gInterior);
    float2 cell = floor(float2((p.WorldPos.x + p.WorldPos.y) * 0.25, p.WorldPos.z * 0.30));
    float roomOn = step(0.32, NGPD_Hash21(cell));
    float3 warmRoom = float3(1.00, 0.78, 0.46) * (0.26 * duskGlow * roomOn * (1.0 - fres * 0.65));

    float3 c = NGPD_ToneMapACES(s.albedo * p.Diffuse.rgb + warmRoom + refl + gSunColor * (specCore + specGlare));
    float a = saturate(s.alpha * p.Diffuse.a + fres * 0.52 + streak * 0.15);
    return NGPD_Finish(p, c, a);
}

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

technique fallback
{
    pass P0
    {
        Texture[0] = gTexture0;
    }
}

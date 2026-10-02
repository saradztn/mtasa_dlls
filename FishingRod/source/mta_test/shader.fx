// Created by: Arena.ai Agent Mode (AI) - FishingRod MTA:SA asset pipeline
// Optional per-pixel shader for the FishingRod.  UNTESTED IN-GAME.
// Uses the shipped DXT5nm normal maps (x in alpha, y in green) and ORM maps (R=AO, G=roughness, B=metal)
// next to the diffuse from the TXD.  If this shader fails to compile the resource keeps working with the
// plain DFF/TXD (MatFX env-map on the metals), it is purely an optional upgrade.
float4x4 gWorld : WORLD;
float4x4 gWorldViewProjection : WORLDVIEWPROJECTION;
float3 gCameraPosition : CAMERAPOSITION;
texture gTexture0 < string textureState = "0,Texture"; >;
texture sNormalTex;
texture sOrmTex;
float3 sSunDir = float3(-0.45, -0.35, 0.82);   // direction towards the sun (world)

sampler S0 = sampler_state { Texture = (gTexture0); MinFilter = Anisotropic; MagFilter = Linear; MipFilter = Linear; MaxAnisotropy = 8; AddressU = Wrap; AddressV = Wrap; };
sampler SN = sampler_state { Texture = (sNormalTex); MinFilter = Anisotropic; MagFilter = Linear; MipFilter = Linear; MaxAnisotropy = 8; AddressU = Wrap; AddressV = Wrap; };
sampler SO = sampler_state { Texture = (sOrmTex);    MinFilter = Linear;      MagFilter = Linear; MipFilter = Linear; AddressU = Wrap; AddressV = Wrap; };

struct VSIn  { float4 Pos : POSITION; float3 Nrm : NORMAL0; float2 Tex : TEXCOORD0; float4 Col : COLOR0; };
struct PSIn  { float4 Pos : POSITION; float3 WPos : TEXCOORD1; float3 WNrm : TEXCOORD2; float2 Tex : TEXCOORD0; float4 Col : COLOR0; };

PSIn VS(VSIn v)
{
    PSIn o;
    o.Pos = mul(v.Pos, gWorldViewProjection);
    o.WPos = mul(v.Pos, gWorld).xyz;
    o.WNrm = normalize(mul(v.Nrm, (float3x3)gWorld));
    o.Tex = v.Tex;
    o.Col = v.Col;
    return o;
}

float3x3 cotangentFrame(float3 N, float3 p, float2 uv)
{
    float3 dp1 = ddx(p), dp2 = ddy(p);
    float2 du1 = ddx(uv), du2 = ddy(uv);
    float3 dp2perp = cross(dp2, N), dp1perp = cross(N, dp1);
    float3 T = dp2perp * du1.x + dp1perp * du2.x;
    float3 B = dp2perp * du1.y + dp1perp * du2.y;
    float invmax = rsqrt(max(dot(T, T), dot(B, B)) + 1e-12);
    return float3x3(T * invmax, B * invmax, N);
}

float4 PS(PSIn i) : COLOR0
{
    float3 albedo = tex2D(S0, i.Tex).rgb;
    float4 nt = tex2D(SN, i.Tex);
    float3 orm = tex2D(SO, i.Tex).rgb;
    float2 nxy = float2(nt.a, nt.g) * 2 - 1;
    float3 nTS = float3(nxy, sqrt(saturate(1 - dot(nxy, nxy))));
    float3 N0 = normalize(i.WNrm);
    float3 N = normalize(mul(nTS, cotangentFrame(N0, i.WPos, i.Tex)));
    float3 V = normalize(gCameraPosition - i.WPos);
    float3 L = normalize(sSunDir);
    float3 H = normalize(L + V);
    float rough = clamp(orm.g, 0.05, 1);
    float metal = orm.b;
    float a = rough * rough;
    float shin = 2.0 / (a * a + 1e-4) - 2.0;                   // Blinn-Phong exponent from roughness
    float3 F0 = lerp(0.04, albedo, metal);
    float3 F = F0 + (1 - F0) * pow(1 - saturate(dot(H, V)), 5);
    float spec = pow(saturate(dot(N, H)), min(shin, 2000)) * (shin + 8) / 25.0 * saturate(dot(N, L));
    float hemi = N.z * 0.5 + 0.5;
    float3 amb = lerp(float3(0.20, 0.19, 0.18), float3(0.34, 0.38, 0.45), hemi) * orm.r;
    float3 diff = albedo * (1 - metal) * (saturate(dot(N, L)) * 0.85 + amb);
    float3 env = lerp(float3(0.25, 0.24, 0.22), float3(0.55, 0.62, 0.72), saturate(reflect(-V, N).z * 0.5 + 0.5)) * F * (1 - rough * 0.8) * orm.r;
    float3 col = diff + F * spec * 0.6 + env + albedo * metal * amb * 0.5;
    return float4(col, 1);
}

technique tec0
{
    pass P0
    {
        VertexShader = compile vs_3_0 VS();
        PixelShader  = compile ps_3_0 PS();
    }
}
technique fallback { pass P0 { } }

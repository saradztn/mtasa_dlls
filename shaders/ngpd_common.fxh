//=============================================================================
// ngpd_common.fxh - Photorealistic Golden-Hour & Wet-Surface PBR Library
// NextGenPoliceDepartment (MTA:SA 1.6 DirectX 9 vs_3_0/ps_3_0 + vs_2_0/ps_2_0)
// Optimized for AMD Radeon RX 580 2048SP / Polaris DX9
//=============================================================================

//---------------------------------------------------------------- MTA state
float4x4 gWorld              : WORLD;
float4x4 gViewProjection     : VIEWPROJECTION;
float4x4 gWorldViewProjection: WORLDVIEWPROJECTION;
float3   gCameraPosition     : CAMERAPOSITION;
float    gTime               : TIME;
texture  gTexture0           < string textureState = "0,Texture"; >;

int    gLighting               < string renderState = "LIGHTING"; >;
float4 gGlobalAmbient          < string renderState = "AMBIENT"; >;
int    gDiffuseMaterialSource  < string renderState = "DIFFUSEMATERIALSOURCE"; >;
int    gAmbientMaterialSource  < string renderState = "AMBIENTMATERIALSOURCE"; >;
int    gEmissiveMaterialSource < string renderState = "EMISSIVEMATERIALSOURCE"; >;
float4 gMaterialAmbient        < string materialState = "Ambient"; >;
float4 gMaterialDiffuse        < string materialState = "Diffuse"; >;
float4 gMaterialEmissive       < string materialState = "Emissive"; >;

int CUSTOMFLAGS < string skipUnusedParameters = "yes"; >;

//---------------------------------------------------------------- resource parameters (set from Lua)
texture sNormalTex;                 // DXT5nm: X in alpha, Y in green
texture sSurfaceTex;                // R roughness, G AO, B wet/puddle mask (or emissive), A metal

float  gWetness        = 0.0;       // global wetness 0..1 (client wet state machine)
float  gWetFactor      = 1.0;       // material response to wetness
float  gPorosity       = 0.5;       // darkening when wet
float  gPuddles        = 0.0;       // puddle formation 0..1
float  gSpec           = 0.2;       // specular intensity
float  gMetallic       = 0.0;       // used where the metal map is 0
float  gEmissive       = 0.0;       // emissive strength (signs, screens, light panels)
float  gNormalScale    = 1.0;       // quality scaling of normal map strength
float  gInterior       = 0.0;       // 1 = interior instance (no sun/sky/wet; overhead-fixture highlight)
float  gRain           = 0.0;       // current rain intensity 0..1 (ripples / streaks)
float  gDayFactor      = 1.0;       // 0 night .. 1 day (sun contribution)
float3 gSunDir         = float3(0.45, -0.62, 0.64); // towards the sun, world space
float3 gSunColor       = float3(1.00, 0.78, 0.50);
float3 gSkyColor       = float3(0.48, 0.58, 0.74);  // env approximation colour (weather/time preset)
float3 gIndoorEnv      = float3(0.82, 0.81, 0.84);  // ceiling/fixture colour for interior env term
float  gReflectScale   = 1.0;       // quality / preset scaling of the env term
float  gFadeStart      = 35.0;      // per-pixel detail fade start (m)
float  gFadeEnd        = 60.0;      // per-pixel detail fade end (m)

// Extended Golden-Hour & Atmospheric Controls
float  gSunGlare       = 1.25;      // solar Mie aureole & sun-path reflection boost
float  gBloomIntensity = 1.05;      // filmic highlight shoulder bloom
float  gShadowContrast = 1.05;      // contact AO & directional shadow contrast
float  gPuddleScale    = 1.00;      // standing water coverage & reflection clarity
float  gWindStrength   = 1.00;      // botanical foliage wind sway & water capillary waves

sampler SampAlbedo  = sampler_state { Texture = (gTexture0);  MinFilter = Anisotropic; MagFilter = Linear; MipFilter = Linear; MaxAnisotropy = 8; AddressU = Wrap; AddressV = Wrap; };
sampler SampNormal  = sampler_state { Texture = (sNormalTex); MinFilter = Anisotropic; MagFilter = Linear; MipFilter = Linear; MaxAnisotropy = 8; AddressU = Wrap; AddressV = Wrap; };
sampler SampSurface = sampler_state { Texture = (sSurfaceTex); MinFilter = Linear;     MagFilter = Linear; MipFilter = Linear; AddressU = Wrap; AddressV = Wrap; };

//---------------------------------------------------------------- helpers
float4 NGPD_BuildingDiffuse(float4 inDiffuse)
{
    float4 outDiffuse;
    if (!gLighting)
    {
        outDiffuse = inDiffuse;
    }
    else
    {
        float4 ambient  = gAmbientMaterialSource  == 0 ? gMaterialAmbient  : inDiffuse;
        float4 diffuse  = gDiffuseMaterialSource  == 0 ? gMaterialDiffuse  : inDiffuse;
        float4 emissive = gEmissiveMaterialSource == 0 ? gMaterialEmissive : inDiffuse;
        outDiffuse = gGlobalAmbient * saturate(ambient + emissive);
        outDiffuse.a *= diffuse.a;
    }
    return outDiffuse;
}

void NGPD_Frame(float3 n, out float3 U, out float3 Up)
{
    float3 a = abs(n);
    if (a.z >= max(a.x, a.y))
    {
        U = float3(1, 0, 0);
        Up = float3(0, n.z >= 0 ? 1 : -1, 0);
    }
    else if (a.x >= a.y)
    {
        U = float3(0, n.x >= 0 ? 1 : -1, 0);
        Up = float3(0, 0, 1);
    }
    else
    {
        U = float3(n.y >= 0 ? -1 : 1, 0, 0);
        Up = float3(0, 0, 1);
    }
}

struct VSIn
{
    float3 Position : POSITION0;
    float3 Normal   : NORMAL0;
    float4 Diffuse  : COLOR0;
    float2 TexCoord : TEXCOORD0;
};

struct PSIn
{
    float4 Position : POSITION0;
    float4 Diffuse  : COLOR0;
    float2 TexCoord : TEXCOORD0;
    float3 WorldPos : TEXCOORD1;
    float3 T        : TEXCOORD2;
    float3 B        : TEXCOORD3;
    float3 N        : TEXCOORD4;
};

PSIn NGPD_VS(VSIn v)
{
    PSIn o = (PSIn)0;
    float3 n = v.Normal;
    if (dot(n, n) < 1e-6) n = float3(0, 0, 1);
    n = normalize(n);
    float3 U, Up;
    NGPD_Frame(n, U, Up);
    float4 wp = mul(float4(v.Position, 1), gWorld);
    o.Position = mul(float4(v.Position, 1), gWorldViewProjection);
    o.WorldPos = wp.xyz;
    o.T = mul(U, (float3x3)gWorld);
    o.B = mul(Up, (float3x3)gWorld);
    o.N = mul(n, (float3x3)gWorld);
    o.TexCoord = v.TexCoord;
    o.Diffuse = NGPD_BuildingDiffuse(v.Diffuse);
    return o;
}

// Low technique vertex & pixel shaders (Shader Model 2.0 compatible)
struct PSInLow
{
    float4 Position : POSITION0;
    float4 Diffuse  : COLOR0;
    float2 TexCoord : TEXCOORD0;
    float  Up       : TEXCOORD1;
};

PSInLow NGPD_VS_Low(VSIn v)
{
    PSInLow o = (PSInLow)0;
    o.Position = mul(float4(v.Position, 1), gWorldViewProjection);
    o.TexCoord = v.TexCoord;
    o.Diffuse = NGPD_BuildingDiffuse(v.Diffuse);
    o.Up = mul(v.Normal, (float3x3)gWorld).z;
    return o;
}

float4 NGPD_PS_Low(PSInLow p) : COLOR0
{
    float4 alb = tex2D(SampAlbedo, p.TexCoord);
    float wm = gWetness * gWetFactor * (1.0 - gInterior);
    float3 c = alb.rgb * p.Diffuse.rgb * (1.0 - gPorosity * 0.45 * wm);
    c += alb.rgb * gEmissive;
    return float4(c, alb.a * p.Diffuse.a);
}

//---------------------------------------------------------------- Procedural & Atmospheric Helpers
float NGPD_Hash21(float2 p)
{
    p = frac(p * float2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return frac(p.x * p.y);
}

float NGPD_ValueNoise(float2 p)
{
    float2 i = floor(p);
    float2 f = frac(p);
    float2 u = f * f * (3.0 - 2.0 * f);
    float a = NGPD_Hash21(i);
    float b = NGPD_Hash21(i + float2(1.0, 0.0));
    float c = NGPD_Hash21(i + float2(0.0, 1.0));
    float d = NGPD_Hash21(i + float2(1.0, 1.0));
    return lerp(lerp(a, b, u.x), lerp(c, d, u.x), u.y);
}

// Golden-Hour Rayleigh/Mie Sky + Sunset Cloud + Building Reflection Evaluator
float3 NGPD_SkyEnv(float3 R, float3 worldPos, float roughness)
{
    float3 L = normalize(gSunDir);
    float horizon = saturate(1.0 - abs(R.z));
    float horizonPow = pow(horizon, 2.4);

    float3 zenithCol = gSkyColor * float3(0.70, 0.80, 0.98);
    float3 horizonWarm = lerp(gSkyColor * 1.15, gSunColor * float3(1.18, 0.86, 0.56) * gDayFactor, 0.72 * gDayFactor);
    float3 sky = lerp(zenithCol, horizonWarm, horizonPow);

    // Mie forward-scattering solar halo & reflected sun disc path
    float sunAlign = saturate(dot(R, L));
    float mieHalo = pow(sunAlign, lerp(24.0, 4.5, roughness)) * (0.80 * gSunGlare * gDayFactor);
    float sunDisc = pow(sunAlign, lerp(340.0, 22.0, roughness)) * (2.40 * gSunGlare * gDayFactor * (1.0 - roughness * 0.72));
    sky += gSunColor * (mieHalo + sunDisc);

    // Illuminated sunset clouds reflected in puddles & curtain-wall glass
    if (R.z > -0.05)
    {
        float2 cloudUV = R.xy / max(0.20, abs(R.z) + 0.22) * 0.32 + float2(gTime * 0.003, 0.0);
        float c1 = NGPD_ValueNoise(cloudUV * 2.4);
        float c2 = NGPD_ValueNoise(cloudUV * 5.2 + 1.7);
        float cloudMask = smoothstep(0.42, 0.78, c1 * 0.65 + c2 * 0.35) * saturate(R.z * 2.4);
        float3 cloudLit = lerp(gSkyColor * 0.88, gSunColor * float3(1.20, 0.88, 0.62), 0.62 + 0.38 * sunAlign);
        sky = lerp(sky, cloudLit, cloudMask * (1.0 - roughness * 0.65) * gDayFactor);
    }

    return sky;
}

float3 NGPD_ToneMapACES(float3 x)
{
    float luma = dot(x, float3(0.2126, 0.7152, 0.0722));
    float bloom = max(0.0, luma - 0.76) * 0.38 * gBloomIntensity;
    x += x * bloom;
    float3 aces = saturate((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14));
    return lerp(saturate(x), aces, 0.45);
}

//---------------------------------------------------------------- Surface Model (High Technique)
struct Surface
{
    float3 albedo;
    float  alpha;
    float3 n;          // world normal (mapped)
    float3 ng;         // world geometric normal
    float  rough;
    float  ao;
    float  mask;       // wet/puddle mask or emissive mask
    float  metal;
};

Surface NGPD_Sample(PSIn p)
{
    Surface s;
    float4 a  = tex2D(SampAlbedo, p.TexCoord);
    float4 nm = tex2D(SampNormal, p.TexCoord);
    float4 sf = tex2D(SampSurface, p.TexCoord);
    s.albedo = a.rgb;
    s.alpha  = a.a;
    float2 xy = (float2(nm.a, nm.g) * 2.0 - 1.0) * gNormalScale;
    float z = sqrt(saturate(1.0 - dot(xy, xy)));
    s.ng = normalize(p.N);
    s.n  = normalize(normalize(p.T) * xy.x + normalize(p.B) * xy.y + s.ng * z);
    s.rough = sf.r;
    s.ao    = sf.g;
    s.mask  = sf.b;
    s.metal = saturate(sf.a + gMetallic * (sf.a < 0.004 ? 1.0 : 0.0));
    return s;
}

// Wet model with non-repeating world-space depression puddles & shoreline meniscus
float NGPD_ApplyWetP(inout Surface s, float porosity)
{
    float wm = gWetness * gWetFactor * (1.0 - gInterior);
    float puddle = 0.0;
    if (gPuddles > 0.0)
    {
        puddle = saturate((s.mask * gPuddleScale - (1.0 - wm * gPuddles)) * 4.2);
        puddle *= saturate((s.ng.z - 0.70) * 10.0);
    }
    s.albedo *= (1.0 - porosity * 0.46 * wm) * (1.0 - 0.28 * puddle);
    s.rough = lerp(s.rough, max(s.rough * 0.32, 0.05), wm);
    s.rough = lerp(s.rough, 0.022, puddle);
    float flatFactor = max(puddle * 0.94, 0.26 * wm);
    s.n = normalize(lerp(s.n, s.ng, flatFactor));
    return puddle;
}

float NGPD_ApplyWet(inout Surface s) { return NGPD_ApplyWetP(s, gPorosity); }

float3 NGPD_Shade(PSIn p, Surface s, float puddle, float3 vertexLight)
{
    float3 V = normalize(gCameraPosition - p.WorldPos);
    float wm = gWetness * gWetFactor * (1.0 - gInterior);
    float3 L = normalize(gSunDir);
    float3 lightCol = gSunColor * gDayFactor;
    float3 env = NGPD_SkyEnv(reflect(-V, s.n), p.WorldPos, s.rough);
    if (gInterior > 0.5)
    {
        L = float3(0, 0, 1);
        lightCol = gIndoorEnv * 0.65;
        env = gIndoorEnv;
    }

    float ndlG = saturate(dot(s.ng, L));
    float ndlN = saturate(dot(s.n, L));
    float relief = saturate(1.0 + (ndlN - ndlG) * 0.95);
    float aoTerm = pow(saturate(lerp(1.0, s.ao, 0.88)), gShadowContrast);
    float3 diffuse = s.albedo * (1.0 - s.metal) * vertexLight * relief * aoTerm;

    // Dual-lobe specular: crisp solar core + golden-hour atmospheric glare lobe
    float3 H = normalize(L + V);
    float ndh = saturate(dot(s.n, H));
    float powerCore = clamp(2.0 / (pow(max(s.rough, 0.02), 4.0) + 1e-4) - 2.0, 2.0, 2048.0);
    float powerGlare = clamp(powerCore * 0.08, 2.0, 64.0);
    float3 f0 = lerp(float3(0.04, 0.04, 0.04), s.albedo, s.metal);
    float specCore = gSpec * (powerCore + 2.0) / 8.0 * pow(ndh, powerCore) * ndlN;
    float specGlare = gSpec * 0.35 * gSunGlare * pow(ndh, powerGlare) * saturate(ndlN + 0.15);

    float ndv = saturate(dot(s.n, V));
    float fres = 0.02 + 0.98 * pow(1.0 - ndv, 5.0);
    float gloss = (1.0 - s.rough) * (1.0 - s.rough);
    float3 envD = env * gloss * (fres + puddle * 0.42 + wm * 0.08);
    float3 envM = env * f0 * (0.38 + 0.62 * gloss);
    float3 envTerm = lerp(envD, envM, s.metal) * aoTerm * gReflectScale;
    envTerm *= saturate(dot(vertexLight, float3(0.33, 0.33, 0.34)) * 1.65);

    // Standing puddles become mirror-reflective at grazing angles
    diffuse *= (1.0 - puddle * saturate(fres + 0.25) * 0.72);

    float3 c = diffuse + f0 * (specCore + specGlare) * lightCol + envTerm;
    c += s.albedo * s.mask * gEmissive;
    return NGPD_ToneMapACES(c);
}

float NGPD_DetailFade(float3 worldPos)
{
    float d = distance(gCameraPosition, worldPos);
    return 1.0 - saturate((d - gFadeStart) / max(gFadeEnd - gFadeStart, 1.0));
}

float4 NGPD_Finish(PSIn p, float3 shaded, float alpha)
{
    float4 base = tex2D(SampAlbedo, p.TexCoord);
    float f = NGPD_DetailFade(p.WorldPos);
    float3 plain = base.rgb * p.Diffuse.rgb;
    return float4(lerp(plain, shaded, f), lerp(base.a * p.Diffuse.a, alpha, f));
}

//
// ngpd_common.fxh - shared code for all NextGenPoliceDepartment surface shaders.
//
// * MTA-provided state is declared with the same semantics/annotations as MTA's
//   mta-helper.fx (WORLD, VIEWPROJECTION, CAMERAPOSITION, TIME, renderState/materialState).
// * Tangent frames are rebuilt from the object-space normal using the exact rule the asset
//   builder used to generate world-projected UVs (tools/asset_builder/meshkit.py):
//     dominant |n| axis (ties: Z, then X, then Y) -> U axis / image-up axis
//       +Z: U=+X Up=+Y   -Z: U=+X Up=-Y   +X: U=+Y Up=+Z   -X: U=-Y Up=+Z   +Y: U=-X Up=+Z   -Y: U=+X Up=+Z
//   GTA SA geometry carries no tangent stream, so this is the only consistent frame available.
// * The wet-surface model mirrors tools/material_generator/generate.py::shade_preview().
// * "Reflections" here are an environment-colour approximation (sky / ceiling colour x Fresnel
//   x gloss).  There is no screen-space reflection, cube map or ray tracing.
//

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

float  gWetness      = 0.0;         // global wetness 0..1 (client wet state machine)
float  gWetFactor    = 1.0;         // material response to wetness
float  gPorosity     = 0.5;         // darkening when wet
float  gPuddles      = 0.0;         // puddle formation 0..1
float  gSpec         = 0.2;         // specular intensity
float  gMetallic     = 0.0;         // used where the metal map is 0
float  gEmissive     = 0.0;         // emissive strength (signs, screens, light panels)
float  gNormalScale  = 1.0;         // quality scaling of normal map strength
float  gInterior     = 0.0;         // 1 = interior instance (no sun/sky/wet; overhead-fixture highlight)
float  gRain         = 0.0;         // current rain intensity 0..1 (ripples / streaks)
float  gDayFactor    = 1.0;         // 0 night .. 1 day (sun contribution)
float3 gSunDir       = float3(0.38, -0.62, 0.69);   // towards the sun, world space
float3 gSunColor     = float3(1.0, 0.95, 0.88);
float3 gSkyColor     = float3(0.55, 0.62, 0.72);    // env approximation colour (weather/time preset)
float3 gIndoorEnv    = float3(0.80, 0.80, 0.82);    // ceiling/fixture colour for interior env term
float  gReflectScale = 1.0;         // quality / preset scaling of the env term
float  gFadeStart    = 35.0;        // per-pixel detail fade (metres from the camera): full shading nearer than this
float  gFadeEnd      = 60.0;        // ... and exactly the plain prelit-texture look beyond this (no per-object switch)

sampler SampAlbedo = sampler_state { Texture = (gTexture0); MinFilter = Linear; MagFilter = Linear; MipFilter = Linear; AddressU = Wrap; AddressV = Wrap; };
sampler SampNormal = sampler_state { Texture = (sNormalTex); MinFilter = Linear; MagFilter = Linear; MipFilter = Linear; AddressU = Wrap; AddressV = Wrap; };
sampler SampSurface = sampler_state { Texture = (sSurfaceTex); MinFilter = Linear; MagFilter = Linear; MipFilter = Linear; AddressU = Wrap; AddressV = Wrap; };

//---------------------------------------------------------------- helpers
float4 NGPD_BuildingDiffuse(float4 inDiffuse)
{
    // identical to MTACalcGTABuildingDiffuse() from mta-helper.fx
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
    // same single matrix product as the fixed-function pipeline -> identical depth for shaded / unshaded
    // geometry (no depth fighting where our surfaces meet each other or GTA's)
    o.Position = mul(float4(v.Position, 1), gWorldViewProjection);
    o.WorldPos = wp.xyz;
    o.T = mul(U, (float3x3)gWorld);
    o.B = mul(Up, (float3x3)gWorld);
    o.N = mul(n, (float3x3)gWorld);
    o.TexCoord = v.TexCoord;
    o.Diffuse = NGPD_BuildingDiffuse(v.Diffuse);
    return o;
}

// Low technique vertex shader: no tangent frame, just albedo x prelight (+ wet darkening in PS)
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

//---------------------------------------------------------------- the surface model (high technique)
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
    float4 a = tex2D(SampAlbedo, p.TexCoord);
    float4 nm = tex2D(SampNormal, p.TexCoord);
    float4 sf = tex2D(SampSurface, p.TexCoord);
    s.albedo = a.rgb;
    s.alpha = a.a;
    float2 xy = (float2(nm.a, nm.g) * 2.0 - 1.0) * gNormalScale;
    float z = sqrt(saturate(1.0 - dot(xy, xy)));
    s.ng = normalize(p.N);
    s.n = normalize(normalize(p.T) * xy.x + normalize(p.B) * xy.y + s.ng * z);
    s.rough = sf.r;
    s.ao = sf.g;
    s.mask = sf.b;
    s.metal = saturate(sf.a + gMetallic * (sf.a < 0.004 ? 1.0 : 0.0));
    return s;
}

// wet model: returns puddle amount and modifies albedo / roughness / normal (mirrors generate.py)
float NGPD_ApplyWetP(inout Surface s, float porosity)
{
    float wm = gWetness * gWetFactor * (1.0 - gInterior);
    float puddle = 0.0;
    if (gPuddles > 0.0)
    {
        puddle = saturate((s.mask - (1.0 - wm * gPuddles)) * 4.0);
        puddle *= saturate((s.ng.z - 0.7) * 10.0);             // only on near-horizontal surfaces
    }
    s.albedo *= (1.0 - porosity * 0.45 * wm) * (1.0 - 0.25 * puddle);
    s.rough = lerp(s.rough, max(s.rough * 0.35, 0.06), wm);
    s.rough = lerp(s.rough, 0.03, puddle);
    float flat = max(puddle, 0.25 * wm);
    s.n = normalize(lerp(s.n, s.ng, flat));
    return puddle;
}

float NGPD_ApplyWet(inout Surface s) { return NGPD_ApplyWetP(s, gPorosity); }

float3 NGPD_Shade(PSIn p, Surface s, float puddle, float3 vertexLight)
{
    float3 V = normalize(gCameraPosition - p.WorldPos);
    float wm = gWetness * gWetFactor * (1.0 - gInterior);
    float3 L = normalize(gSunDir);
    float3 lightCol = gSunColor * gDayFactor;
    float3 env = gSkyColor;
    if (gInterior > 0.5)
    {
        L = float3(0, 0, 1);                      // overhead fixtures
        lightCol = gIndoorEnv * 0.6;
        env = gIndoorEnv;
    }
    float ndlG = saturate(dot(s.ng, L));
    float ndlN = saturate(dot(s.n, L));
    // per-pixel relief relative to the baked (per-vertex) lighting; avoids double-lighting
    float relief = saturate(1.0 + (ndlN - ndlG) * 0.9);
    float3 diffuse = s.albedo * (1.0 - s.metal) * vertexLight * relief * lerp(1.0, s.ao, 0.85);
    float3 H = normalize(L + V);
    float ndh = saturate(dot(s.n, H));
    float power = clamp(2.0 / (pow(s.rough, 4) + 1e-4) - 2.0, 2.0, 2048.0);
    float3 f0 = lerp(float3(0.04, 0.04, 0.04), s.albedo, s.metal);
    float spec = gSpec * (power + 2.0) / 8.0 * pow(ndh, power) * ndlN;
    float ndv = saturate(dot(s.n, V));
    float fres = 0.02 + 0.98 * pow(1.0 - ndv, 5.0);
    float gloss = (1.0 - s.rough) * (1.0 - s.rough);
    float3 envD = env * gloss * (fres + puddle * 0.25 + wm * 0.05);
    float3 envM = env * f0 * (0.35 + 0.65 * gloss);
    float3 envTerm = lerp(envD, envM, s.metal) * s.ao * gReflectScale;
    // keep reflections dimmer in dark prelight areas (no light to reflect)
    envTerm *= saturate(dot(vertexLight, float3(0.33, 0.33, 0.34)) * 1.6);
    float3 c = diffuse + f0 * spec * lightCol + envTerm;
    c += s.albedo * s.mask * gEmissive;
    return c / (1.0 + c * 0.15) * 1.15;
}

// Distance fade of the shading detail.  MTA's dxCreateShader maxDistance switches a shader on/off per OBJECT;
// our models are 20-90 m chunks, so a whole wing used to flip between the shaded and the plain look at once
// (the "popping" reported in-game, runs #4/#5).  The shader is now created without a distance limit and
// blends per pixel: full detail near the camera, exactly texture x prelight (the unshaded GTA look) far away.
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


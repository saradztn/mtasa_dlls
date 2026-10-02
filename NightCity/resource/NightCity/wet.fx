// wet.fx - physically-tuned wet asphalt for NightCity.
//   * darkening is modest (real wet roads are ~20-40% darker, not black)
//   * micro-film of water everywhere with a slight sheen; NO large fake puddle tiles
//   * small, faint rain ring ripples only where the surface is fully wet, radius a few cm
//   * screen-space reflection is subtle (Fresnel), blurred by surface roughness
//   * sun specular highlight (gSunDir) for a realistic wet sheen when the sun is low
//   * the covered part of the river tunnel stays dry
// Controlled entirely by Lua: gWet 0..1, gRainStr 0..1, gSheen, gSunAlt, gSunDir.
float4x4 gWorld : WORLD;
float4x4 gWorldViewProjection : WORLDVIEWPROJECTION;
float4x4 gViewProjection : VIEWPROJECTION;
float3 gCameraPosition : CAMERAPOSITION;
float gTime : TIME;

float gWet = 0.0;
float gRainStr = 0.0;
float gSheen = 0.0;
float gSunAlt = 0.0;
float3 gSunDir = float3(0.0, 0.0, 1.0);
float gReflect = 0.8;
float2 gPix = float2(0.0007, 0.0013);
float4 gTun = float4(0.0, 1.0, -1.0, 0.0);

texture gTexture0 < string textureState = "0,Texture"; >;
texture gScreen;

sampler Sampler0 = sampler_state { Texture = (gTexture0); MinFilter = Anisotropic; MagFilter = Linear; MipFilter = Linear; MaxAnisotropy = 8; };
sampler SamplerS = sampler_state { Texture = (gScreen);  MinFilter = Linear;    MagFilter = Linear; MipFilter = None;   AddressU = Clamp; AddressV = Clamp; };

struct VSInput { float3 Position : POSITION0; float3 Normal : NORMAL0; float4 Diffuse : COLOR0; float2 TexCoord : TEXCOORD0; };
struct VSOutput { float4 Position : POSITION0; float4 Diffuse : COLOR0; float2 TexCoord : TEXCOORD0; float3 WorldPos : TEXCOORD1; float3 WorldNormal : TEXCOORD2; };
struct PSInput  { float4 Diffuse : COLOR0; float2 TexCoord : TEXCOORD0; float3 WorldPos : TEXCOORD1; float3 WorldNormal : TEXCOORD2; };

VSOutput VertexShaderFunction(VSInput VS)
{
    VSOutput O = (VSOutput)0;
    O.Position = mul(float4(VS.Position, 1.0), gWorldViewProjection);
    O.WorldPos = mul(float4(VS.Position, 1.0), gWorld).xyz;
    O.WorldNormal = mul(VS.Normal, (float3x3)gWorld);
    O.Diffuse = VS.Diffuse;
    O.TexCoord = VS.TexCoord;
    return O;
}

float hash21(float2 p) { return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453); }
float vnoise(float2 p)
{
    float2 i = floor(p); float2 f = frac(p); f = f * f * (3.0 - 2.0 * f);
    float a = hash21(i); float b = hash21(i + float2(1,0));
    float c = hash21(i + float2(0,1)); float d = hash21(i + float2(1,1));
    return lerp(lerp(a,b,f.x), lerp(c,d,f.x), f.y);
}

// Tiny rain ripples: ~8-12 cm radius, gentle, low amplitude so they look like a film not a pool
float2 rainRings(float2 p, float t, float strength)
{
    if (strength < 0.01) return float2(0,0);
    float2 q = p * 2.3;                               // ~0.43 m grid -> drops ~0.4 m apart
    float2 g = floor(q);
    float2 f = frac(q) - 0.5;
    float h = hash21(g);
    float age = frac(t * 1.2 + h);
    float r = length(f);
    float k = (r - age * 0.10) * 120.0;               // tight ring (small radius), short wavelength
    float ring = exp(-k * k) * (1.0 - age) * strength;
    return (f / max(r, 0.001)) * ring * 0.18;
}

float4 PixelShaderFunction(PSInput PS) : COLOR0
{
    float4 tex = tex2D(Sampler0, PS.TexCoord);
    float3 vcol = max(PS.Diffuse.rgb, float3(0.22, 0.24, 0.30));
    float3 baseCol = tex.rgb * vcol;
    float3 N = normalize(PS.WorldNormal);
    float up = saturate(N.z);
    float2 wxy = PS.WorldPos.xy;

    // ---- wetness distribution: a nearly uniform thin film with very subtle variation, not cartoon puddles.
    //      Variation is tiny, high frequency; adds realism without drawing circles on the road.
    float micro = vnoise(wxy * 0.60) * 0.5 + vnoise(wxy * 2.2 + 7.3) * 0.3 + vnoise(wxy * 9.0 + 3.1) * 0.2;
    float film = saturate(gWet * (0.85 + 0.15 * (micro - 0.5) * 2.0)) * up;
    float deep = saturate(gWet * (micro * 0.25 + 0.05)) * up;              // sparse darker spots (0..0.3)

    // tunnel stays dry
    float inTun = step(abs(PS.WorldPos.x - gTun.x), 9.0) * step(gTun.y, PS.WorldPos.y) * step(PS.WorldPos.y, gTun.z) * step(PS.WorldPos.z, gTun.w);
    film *= lerp(1.0, 0.0, inTun * 0.92);
    deep *= lerp(1.0, 0.0, inTun);

    // ---- darkening: natural wet asphalt darkens ~15-30%, never full black.
    float darken = 0.20 * film + 0.15 * deep;
    baseCol *= 1.0 - darken;

    // ---- surface perturbation: tiny ripples only where the rain is falling and the film is present
    float2 slope = rainRings(wxy, gTime, film * gRainStr);
    float3 Nw = normalize(float3(N.x + slope.x, N.y + slope.y, max(N.z, 0.25)));

    // ---- Fresnel reflection (screen space) - subtle; sheen adds extra for "after rain" look
    float3 V = normalize(PS.WorldPos - gCameraPosition);
    float3 R = reflect(V, Nw);
    float3 refPoint = PS.WorldPos + R * 45.0;
    float4 cp = mul(float4(refPoint, 1.0), gViewProjection);
    float2 uv = cp.xy / max(cp.w, 0.001) * float2(0.5, -0.5) + 0.5;
    float2 edge = saturate(min(uv, 1.0 - uv) * 8.0);
    float vis = edge.x * edge.y * step(0.5, cp.w);
    float dist = length(PS.WorldPos - gCameraPosition);
    vis *= saturate(1.0 - dist / 130.0);

    float blur = 32.0 - 12.0 * film;                 // rough film -> heavily blurred (no mirror)
    float2 o = gPix * blur;
    float3 refl = tex2D(SamplerS, uv).rgb * 0.35
                + tex2D(SamplerS, uv + float2(o.x, 0)).rgb * 0.1625
                + tex2D(SamplerS, uv - float2(o.x, 0)).rgb * 0.1625
                + tex2D(SamplerS, uv + float2(0, o.y)).rgb * 0.1625
                + tex2D(SamplerS, uv - float2(0, o.y)).rgb * 0.1625;

    float ndv = saturate(dot(-V, Nw));
    float fres = 0.02 + 0.6 * pow(1.0 - ndv, 5.0);
    float strength = film * (0.08 + fres * (0.4 + 0.6 * deep)) * gReflect * (0.6 + 0.6 * gSheen);

    // ---- sun specular (tiny elongated glint on wet roads at low sun -- the classic "newly wet road" look)
    if (gSunAlt > 0.02) {
        float3 L = normalize(float3(gSunDir.x, gSunDir.y, max(gSunDir.z, 0.05)));
        float3 H = normalize(L - V);
        float spec = pow(saturate(dot(Nw, H)), 120.0) * gSunAlt;
        float3 sunSpec = float3(1.0, 0.95, 0.82) * spec * film * 0.45;
        baseCol += sunSpec;
    }

    float3 col = baseCol + refl * strength * vis;
    return float4(saturate(col), 1.0);
}

technique tec0 { pass P0 { VertexShader = compile vs_3_0 VertexShaderFunction(); PixelShader = compile ps_3_0 PixelShaderFunction(); } }
technique fallback { pass P0 {} }

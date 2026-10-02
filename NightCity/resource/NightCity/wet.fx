// wet.fx - natural thin water film on NightCity roads.  Applied to road/pavement/plaza textures;
// driven entirely by atmo.lua (gWet, gRainStr, gSheen, gSunAlt, gSunDir).
//   * modest darkening (15-30%)
//   * small rain rings (~10 cm) only, no giant cartoon puddles
//   * subtle Fresnel screen-space reflection
//   * tiny sun specular glitter (sheen) on wet roads when sun is low
//   * tunnel kept dry
float4x4 gWorld : WORLD;
float4x4 gWorldViewProjection : WORLDVIEWPROJECTION;
float4x4 gViewProjection : VIEWPROJECTION;
float3 gCameraPosition : CAMERAPOSITION;
float gTime : TIME;

float gWet = 0.0;
float gRainStr = 0.0;
float gSheen = 0.0;
float gSunAlt = 0.0;
float3 gSunDir = float3(0,0,1);
float gReflect = 0.6;
float2 gPix = float2(0.0007,0.0013);
float4 gTun = float4(0,1,-1,0);

texture gTexture0 < string textureState = "0,Texture"; >;
texture gScreen;
sampler S0 = sampler_state { Texture=(gTexture0); MinFilter=Linear; MagFilter=Linear; MipFilter=Linear; };
sampler SS = sampler_state { Texture=(gScreen); MinFilter=Linear; MagFilter=Linear; MipFilter=None; AddressU=Clamp; AddressV=Clamp; };

struct VSIn  { float3 P:POSITION0; float3 N:NORMAL0; float4 D:COLOR0; float2 T:TEXCOORD0; };
struct VSOut { float4 P:POSITION0; float4 D:COLOR0; float2 T:TEXCOORD0; float3 W:TEXCOORD1; float3 N:TEXCOORD2; };
struct PSIn  { float4 D:COLOR0; float2 T:TEXCOORD0; float3 W:TEXCOORD1; float3 N:TEXCOORD2; };

VSOut VS(VSIn v)
{
    VSOut o;
    o.P = mul(float4(v.P,1), gWorldViewProjection);
    o.W = mul(float4(v.P,1), gWorld).xyz;
    o.N = mul(v.N, (float3x3)gWorld);
    o.D = v.D;
    o.T = v.T;
    return o;
}

float h21(float2 p) { return frac(sin(dot(p,float2(127.1,311.7)))*43758.5); }
float vn(float2 p)
{
    float2 i=floor(p), f=frac(p); f=f*f*(3-2*f);
    float a=h21(i), b=h21(i+float2(1,0)), c=h21(i+float2(0,1)), d=h21(i+float2(1,1));
    return lerp(lerp(a,b,f.x), lerp(c,d,f.x), f.y);
}

float2 rings(float2 p, float t, float s)
{
    if (s < 0.01) return float2(0,0);
    float2 q = p*2.3, g=floor(q), f=frac(q)-0.5;
    float h = h21(g);
    float age = frac(t*1.2+h);
    float r = length(f);
    float k = (r - age*0.10)*120.0;
    float ring = exp(-k*k)*(1.0-age)*s;
    return (f/max(r,0.001))*ring*0.15;
}

float4 PS(PSIn i) : COLOR0
{
    float4 tx = tex2D(S0, i.T);
    float3 vcol = max(i.D.rgb, float3(0.22,0.24,0.30));
    float3 col = tx.rgb * vcol;
    float3 Nn = normalize(i.N);
    float up = saturate(Nn.z);
    float2 xy = i.W.xy;
    // thin film with subtle high-freq variation (no puddle tiles)
    float m = vn(xy*0.6)*0.5 + vn(xy*2.2+7.3)*0.3 + vn(xy*9+3.1)*0.2;
    float film = saturate(gWet*(0.85+0.15*(m-0.5)*2.0))*up;
    float inTun = step(abs(i.W.x - gTun.x),9.0)*step(gTun.y,i.W.y)*step(i.W.y,gTun.z)*step(i.W.z,gTun.w);
    film *= lerp(1.0, 0.0, inTun*0.92);
    // darkening
    col *= 1.0 - (0.20*film);
    // ripples perturb normal
    float2 sl = rings(xy, gTime, film*gRainStr);
    float3 Nw = normalize(float3(Nn.x+sl.x, Nn.y+sl.y, max(Nn.z,0.25)));
    // Fresnel reflection
    float3 V = normalize(i.W - gCameraPosition);
    float3 R = reflect(V, Nw);
    float3 rp = i.W + R*30.0;
    float4 cp = mul(float4(rp,1), gViewProjection);
    float2 uv = cp.xy/max(cp.w,0.001)*float2(0.5,-0.5)+0.5;
    float2 e = saturate(min(uv,1.0-uv)*8.0);
    float vis = e.x*e.y*step(0.5,cp.w);
    float dist = length(i.W - gCameraPosition);
    vis *= saturate(1.0 - dist/100.0);
    float2 o = gPix*22.0;
    float3 refl = tex2D(SS, uv).rgb*0.4
                + tex2D(SS, uv+float2(o.x,0)).rgb*0.15
                + tex2D(SS, uv-float2(o.x,0)).rgb*0.15
                + tex2D(SS, uv+float2(0,o.y)).rgb*0.15
                + tex2D(SS, uv-float2(0,o.y)).rgb*0.15;
    float ndv = saturate(dot(-V,Nw));
    float fres = 0.02 + 0.5*pow(1.0-ndv, 5);
    float str = film*(0.06 + fres*(0.3+0.5*gSheen))*gReflect;
    col += refl*str*vis;
    // sun glint
    if (gSunAlt > 0.02)
    {
        float3 L = normalize(float3(gSunDir.x, gSunDir.y, max(gSunDir.z,0.05)));
        float3 H = normalize(L - V);
        float sp = pow(saturate(dot(Nw,H)), 80.0)*gSunAlt;
        col += float3(1.0,0.95,0.82)*sp*film*0.35;
    }
    return float4(saturate(col), 1);
}

technique tec0 { pass P0 { VertexShader=compile vs_2_0 VS(); PixelShader=compile ps_2_0 PS(); } }
technique fallback { pass P0 {} }

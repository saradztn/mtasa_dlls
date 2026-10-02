// post.fx - compact cinematic tonemap for NightCity (ps_2_0, fits 64 instruction slots).
//   Driven by atmo.lua: gGain (exposure), gTint (white balance), gSunAlt (0 night .. 1 noon),
//   gHaz (atmospheric haze colour), gBloom, gVignette, gGrain, gContrast, gTime.
texture ScreenTexture;
float2 gPix = float2(0.0007, 0.0013);
float gTime, gGain, gSunAlt, gBloom, gVignette, gGrain, gContrast;
float3 gTint = float3(1,1,1);
float3 gHaz = float3(0,0,0);
sampler S0 = sampler_state { Texture=(ScreenTexture); MinFilter=Linear; MagFilter=Linear; AddressU=Clamp; AddressV=Clamp; };

float3 aces(float3 x)
{
    return (x * (2.51*x + 0.03)) / (x * (2.43*x + 0.59) + 0.14);
}

float4 P(float2 uv : TEXCOORD0) : COLOR0
{
    float2 d0 = uv - 0.5;
    float r2 = dot(d0,d0);
    // chromatic aberration
    float ca = 0.003 + 0.005*(1.0 - gSunAlt);
    float3 c;
    c.r = tex2D(S0, uv + d0*r2*ca).r;
    c.g = tex2D(S0, uv).g;
    c.b = tex2D(S0, uv - d0*r2*ca).b;
    // one small bloom tap (cheap ps_2_0)
    float2 w = gPix * 8.0;
    float3 b = (tex2D(S0, uv+float2(w.x,0)).rgb + tex2D(S0, uv-float2(w.x,0)).rgb
              + tex2D(S0, uv+float2(0,w.y)).rgb + tex2D(S0, uv-float2(0,w.y)).rgb) * 0.25;
    c += max(b - 0.55, 0.0) * gBloom;
    // white balance + exposure
    c *= gTint * gGain;
    // filmic tonemap
    c = saturate(aces(c));
    // gentle contrast curve
    c = lerp(c, c*c*(3.0-2.0*c), 0.25*gContrast);
    // day/night colour cast
    float l = dot(c, float3(0.3,0.59,0.11));
    c = lerp(c, float3(l,l,l), (1.0 - gSunAlt)*0.08);
    // warm sunset push (when sun is low gSunAlt~0.1..0.3)
    float sunset = saturate((1.0 - gSunAlt) * smoothstep(0.35,0.05,gSunAlt));
    c *= lerp(float3(1,0.98,0.97), float3(1.08,0.88,0.78), sunset*0.3);
    // vignette + haze
    c *= saturate(1.0 - r2 * (gVignette * (0.9 + 0.3*(1.0 - gSunAlt))));
    c += gHaz * 6.0 * saturate(r2*1.2);
    // grain
    float g = frac(sin(dot(uv*float2(913,541)+gTime, float2(12.99,78.23)))*43758.5) - 0.5;
    c += g * gGrain;
    return float4(saturate(c), 1);
}

technique tec0 { pass P0 { PixelShader = compile ps_2_0 P(); } }
technique fallback { pass P0 {} }

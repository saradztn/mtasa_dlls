// Low-cost wet asphalt pass for NightCity.
// No screen-space reflection or procedural rain rings: those paths produced large
// projected quads on older ps_2_0 hardware. A thin dark film and a restrained gloss
// keep the road readable and natural while remaining within the 64-slot limit.
float4x4 gWorldViewProjection : WORLDVIEWPROJECTION;
float gWet = 0.0;
float gSheen = 0.0;
float gSunAlt = 1.0;

texture gTexture0 < string textureState = "0,Texture"; >;
sampler S0 = sampler_state
{
    Texture = (gTexture0);
    MinFilter = Linear;
    MagFilter = Linear;
    MipFilter = Linear;
};

struct VSInput
{
    float3 Position : POSITION0;
    float4 Diffuse : COLOR0;
    float2 TexCoord : TEXCOORD0;
};

struct PSInput
{
    float4 Position : POSITION0;
    float4 Diffuse : COLOR0;
    float2 TexCoord : TEXCOORD0;
};

PSInput VertexShaderFunction(VSInput v)
{
    PSInput o;
    o.Position = mul(float4(v.Position, 1.0), gWorldViewProjection);
    o.Diffuse = v.Diffuse;
    o.TexCoord = v.TexCoord;
    return o;
}

float4 PixelShaderFunction(PSInput i) : COLOR0
{
    float4 texel = tex2D(S0, i.TexCoord);
    float3 vertexLight = max(i.Diffuse.rgb, float3(0.25, 0.25, 0.25));
    float3 colour = texel.rgb * vertexLight;
    float wet = saturate(gWet);
    colour *= 1.0 - 0.16 * wet;
    float gloss = wet * gSheen * (0.015 + 0.025 * saturate(gSunAlt));
    colour += float3(1.0, 0.96, 0.88) * gloss;
    return float4(saturate(colour), texel.a * i.Diffuse.a);
}

technique tec0
{
    pass P0
    {
        VertexShader = compile vs_2_0 VertexShaderFunction();
        PixelShader = compile ps_2_0 PixelShaderFunction();
    }
}

technique fallback
{
    pass P0
    {
    }
}

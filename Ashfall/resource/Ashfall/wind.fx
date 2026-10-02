// Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA resource
// wind.fx - optional leaf sway (vertex shader) for the city foliage, toggled with /parkwind (default OFF).
// Vertices move horizontally with a travelling sine wave; the amplitude grows with the height above the object origin,
// so trunks and ground stay still.
float4x4 gWorld : WORLD;
float4x4 gWorldViewProjection : WORLDVIEWPROJECTION;
float gTime : TIME;
float gStrength = 0.07;

texture gTexture0 < string textureState = "0,Texture"; >;
sampler Sampler0 = sampler_state
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

PSInput VertexShaderFunction(VSInput VS)
{
    PSInput PS = (PSInput)0;
    float3 wp = mul(float4(VS.Position, 1.0), gWorld).xyz;
    float h = saturate((VS.Position.z - 1.2) / 6.0);
    float ph = gTime * 1.9 + wp.x * 0.23 + wp.y * 0.17;
    float3 p = VS.Position;
    p.x += (sin(ph) + 0.5 * sin(ph * 2.3 + 1.7)) * gStrength * h;
    p.y += (cos(ph * 0.9) + 0.5 * sin(ph * 1.9)) * gStrength * h;
    p.z += sin(ph * 1.3) * gStrength * 0.35 * h;
    PS.Position = mul(float4(p, 1.0), gWorldViewProjection);
    PS.Diffuse = VS.Diffuse;
    PS.TexCoord = VS.TexCoord;
    return PS;
}

float4 PixelShaderFunction(PSInput PS) : COLOR0
{
    float4 c = tex2D(Sampler0, PS.TexCoord);
    return c * PS.Diffuse;
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

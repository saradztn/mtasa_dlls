// Optional world-texture material response. Applied only to configured texture
// name patterns. This is a small grazing-angle accent over GTA's existing
// lighting; material identification is texture-name driven, not a screen buffer.
#include "mta-helper.fx"

sampler BaseSampler = sampler_state
{
    Texture = (gTexture0);
    MinFilter = Linear;
    MagFilter = Linear;
    MipFilter = Linear;
    AddressU = Wrap;
    AddressV = Wrap;
};

float MaterialResponse;
float MaterialRoughness;
float3 MaterialTint;

struct MaterialVSInput
{
    float3 Position : POSITION0;
    float3 Normal : NORMAL0;
    float4 Diffuse : COLOR0;
    float2 TexCoord : TEXCOORD0;
};
struct MaterialPSInput
{
    float4 Position : POSITION0;
    float4 Diffuse : COLOR0;
    float2 TexCoord : TEXCOORD0;
    float3 WorldNormal : TEXCOORD1;
    float3 WorldPosition : TEXCOORD2;
};

MaterialPSInput MaterialVS(MaterialVSInput input)
{
    MaterialPSInput output = (MaterialPSInput)0;
    output.Position = MTACalcScreenPosition(input.Position);
    output.Diffuse = MTACalcGTABuildingDiffuse(input.Diffuse);
    output.TexCoord = input.TexCoord;
    output.WorldNormal = normalize(MTACalcWorldNormal(input.Normal));
    output.WorldPosition = MTACalcWorldPosition(input.Position);
    return output;
}

float4 MaterialPS(MaterialPSInput input) : COLOR0
{
    float4 texel = tex2D(BaseSampler, input.TexCoord);
    float3 baseColor = texel.rgb * input.Diffuse.rgb * MaterialTint;
    float3 normal = normalize(input.WorldNormal);
    float3 viewDirection = normalize(gCameraPosition - input.WorldPosition);
    float facing = saturate(dot(normal, viewDirection));
    float exponent = lerp(72.0, 12.0, saturate(MaterialRoughness));
    float grazing = pow(1.0 - facing, exponent);
    float response = saturate(MaterialResponse) * grazing * saturate(dot(baseColor, float3(0.299, 0.587, 0.114)) + 0.18);
    float3 result = baseColor + response * float3(0.82, 0.88, 0.95);
    return float4(saturate(result), texel.a * input.Diffuse.a);
}

technique Main
{
    pass P0
    {
        VertexShader = compile vs_2_0 MaterialVS();
        PixelShader = compile ps_2_0 MaterialPS();
    }
}

technique Fallback
{
    pass P0
    {
        Texture[0] = gTexture0;
        ColorOp[0] = SelectArg1;
        ColorArg1[0] = Texture;
        AlphaOp[0] = SelectArg1;
        AlphaArg1[0] = Texture;
        ColorOp[1] = Disable;
        AlphaOp[1] = Disable;
    }
}

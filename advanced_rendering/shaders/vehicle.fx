// Optional local-vehicle material pass. It preserves the source texture and GTA
// vehicle lighting, adding only a low-amplitude Fresnel/specular accent. A true
// dynamic cubemap reflection, per-material glass mask and paint-layer mask are
// not available from a generic post-process resource.
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

float VehicleResponse;
float VehicleRoughness;
float3 VehicleTint;

struct VehicleVSInput
{
    float3 Position : POSITION0;
    float3 Normal : NORMAL0;
    float4 Diffuse : COLOR0;
    float2 TexCoord : TEXCOORD0;
};
struct VehiclePSInput
{
    float4 Position : POSITION0;
    float4 Diffuse : COLOR0;
    float2 TexCoord : TEXCOORD0;
    float3 WorldNormal : TEXCOORD1;
    float3 WorldPosition : TEXCOORD2;
};

VehiclePSInput VehicleVS(VehicleVSInput input)
{
    VehiclePSInput output = (VehiclePSInput)0;
    output.Position = MTACalcScreenPosition(input.Position);
    output.TexCoord = input.TexCoord;
    output.WorldNormal = normalize(MTACalcWorldNormal(input.Normal));
    output.WorldPosition = MTACalcWorldPosition(input.Position);
    output.Diffuse = MTACalcGTAVehicleDiffuse(output.WorldNormal, input.Diffuse);
    return output;
}

float4 VehiclePS(VehiclePSInput input) : COLOR0
{
    float4 texel = tex2D(BaseSampler, input.TexCoord);
    float3 baseColor = texel.rgb * input.Diffuse.rgb * VehicleTint;
    float3 normal = normalize(input.WorldNormal);
    float3 viewDirection = normalize(gCameraPosition - input.WorldPosition);
    float facing = saturate(dot(normal, viewDirection));
    float fresnel = pow(1.0 - facing, 5.0);
    float exponent = lerp(18.0, 64.0, 1.0 - saturate(VehicleRoughness));
    float softSpecular = pow(saturate(facing), exponent) * (1.0 - saturate(VehicleRoughness));
    float amplitude = saturate(VehicleResponse) * (0.24 * fresnel + 0.08 * softSpecular);
    float3 paintAccent = float3(0.82, 0.88, 0.96) * amplitude;
    return float4(saturate(baseColor + paintAccent), texel.a * input.Diffuse.a);
}

technique Main
{
    pass P0
    {
        VertexShader = compile vs_2_0 VehicleVS();
        PixelShader = compile ps_2_0 VehiclePS();
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

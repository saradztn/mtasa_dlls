// Royal Fortress - wet floor reflection shader (remake)
// Apply to marble/cobble/stone floor textures for a glossy wet look.
// MTA: engineApplyShaderToWorldTexture(shader, "rf_marble*") etc.

texture tex0 : TEX0;
float4 gColor = float4(1,1,1,1);
float gWetness = 0.65;
float gSpecPower = 48.0;
float gReflectStrength = 0.35;

sampler2D Samp0 = sampler_state
{
    Texture = (tex0);
    MinFilter = Linear;
    MagFilter = Linear;
    MipFilter = Linear;
    AddressU = Wrap;
    AddressV = Wrap;
};

// City-native vertex pipeline (no compiled vertex shader) keeps MTA's default transform.
technique CityNativePixels
{
    pass P0
    {
        Texture[0] = (tex0);
        textureState[0] = "0,Texture";

        PixelShader = compile ps_2_0 PSMain();
    }
}

float4 PSMain(float2 uv : TEXCOORD0) : COLOR0
{
    float4 base = tex2D(Samp0, uv) * gColor;

    // Darken and saturate to simulate wet surface
    float3 wet = base.rgb * (1.0 - gWetness * 0.35);
    wet = lerp(wet, wet * wet, 0.15);

    // Specular highlight band (fake reflection of light)
    float2 center = uv - 0.5;
    float spec = pow(saturate(1.0 - length(center) * 1.6), gSpecPower);
    wet += spec * gReflectStrength;

    // Subtle blue tint for wetness
    wet = lerp(wet, wet + float3(0.02, 0.05, 0.08), gWetness * 0.4);

    return float4(saturate(wet), base.a);
}

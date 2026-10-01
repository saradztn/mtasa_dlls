// Minimal, resource-local subset of MTA's standard mta-helper.fx interface.
// Keeping the required world/lighting semantics here makes the resource
// self-contained instead of depending on another resource's private include.

float4x4 gWorld : WORLD;
float4x4 gView : VIEW;
float4x4 gProjection : PROJECTION;
float3 gCameraPosition : CAMERAPOSITION;

texture gTexture0 < string textureState = "0,Texture"; >;

int gLighting < string renderState = "LIGHTING"; >;
float4 gGlobalAmbient < string renderState = "AMBIENT"; >;
int gDiffuseMaterialSource < string renderState = "DIFFUSEMATERIALSOURCE"; >;
int gAmbientMaterialSource < string renderState = "AMBIENTMATERIALSOURCE"; >;
int gEmissiveMaterialSource < string renderState = "EMISSIVEMATERIALSOURCE"; >;
float4 gMaterialAmbient < string materialState = "Ambient"; >;
float4 gMaterialDiffuse < string materialState = "Diffuse"; >;
float4 gMaterialEmissive < string materialState = "Emissive"; >;
float4 gLightAmbient : LIGHTAMBIENT;
float3 gLightDirection : LIGHTDIRECTION;

float4 MTACalcScreenPosition(float3 position)
{
    float4 worldPosition = mul(float4(position, 1.0), gWorld);
    float4 viewPosition = mul(worldPosition, gView);
    return mul(viewPosition, gProjection);
}

float3 MTACalcWorldPosition(float3 position)
{
    return mul(float4(position, 1.0), gWorld).xyz;
}

float3 MTACalcWorldNormal(float3 normal)
{
    return mul(normal, (float3x3)gWorld);
}

float4 MTACalcGTABuildingDiffuse(float4 inputDiffuse)
{
    if (!gLighting)
        return inputDiffuse;

    float4 ambient = gAmbientMaterialSource == 0 ? gMaterialAmbient : inputDiffuse;
    float4 diffuse = gDiffuseMaterialSource == 0 ? gMaterialDiffuse : inputDiffuse;
    float4 emissive = gEmissiveMaterialSource == 0 ? gMaterialEmissive : inputDiffuse;
    float4 outputDiffuse = gGlobalAmbient * saturate(ambient + emissive);
    outputDiffuse.a *= diffuse.a;
    return outputDiffuse;
}

float4 MTACalcGTAVehicleDiffuse(float3 worldNormal, float4 inputDiffuse)
{
    float4 ambient = gAmbientMaterialSource == 0 ? gMaterialAmbient : inputDiffuse;
    float4 diffuse = gDiffuseMaterialSource == 0 ? gMaterialDiffuse : inputDiffuse;
    float4 emissive = gEmissiveMaterialSource == 0 ? gMaterialEmissive : inputDiffuse;
    float4 totalAmbient = ambient * (gGlobalAmbient + gLightAmbient);
    float directionFactor = max(0.2, dot(worldNormal, -gLightDirection));
    float4 totalDiffuse = diffuse * directionFactor;
    float4 outputDiffuse = saturate(totalDiffuse + totalAmbient + emissive);
    outputDiffuse.a *= diffuse.a;
    return outputDiffuse;
}

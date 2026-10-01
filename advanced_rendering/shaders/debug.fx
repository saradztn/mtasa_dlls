// Developer visualizer for the buffers the resource actually owns. 'Motion' is
// camera-only estimated flow, not engine-provided object vectors. AO/SSR inputs
// can be precomputed into their debug-only RT by pipeline.lua.
texture SceneTexture;
texture HistoryTexture;
texture CurrentDepth;
texture PreviousDepth;
texture MotionTexture;
float2 TexelSize;
float DebugMode;
float UseDepth;
float HistoryValid;
float MotionEnabled;

sampler SceneSampler = sampler_state
{
    Texture = (SceneTexture);
    MinFilter = Linear;
    MagFilter = Linear;
    MipFilter = None;
    AddressU = Clamp;
    AddressV = Clamp;
};
sampler HistorySampler = sampler_state
{
    Texture = (HistoryTexture);
    MinFilter = Linear;
    MagFilter = Linear;
    MipFilter = None;
    AddressU = Clamp;
    AddressV = Clamp;
};
sampler CurrentDepthSampler = sampler_state
{
    Texture = (CurrentDepth);
    MinFilter = Point;
    MagFilter = Point;
    MipFilter = None;
    AddressU = Clamp;
    AddressV = Clamp;
};
sampler PreviousDepthSampler = sampler_state
{
    Texture = (PreviousDepth);
    MinFilter = Point;
    MagFilter = Point;
    MipFilter = None;
    AddressU = Clamp;
    AddressV = Clamp;
};
sampler MotionSampler = sampler_state
{
    Texture = (MotionTexture);
    MinFilter = Point;
    MagFilter = Point;
    MipFilter = None;
    AddressU = Clamp;
    AddressV = Clamp;
};

float DecodeDepth24(float3 encoded)
{
    return encoded.r + encoded.g / 255.0 + encoded.b / 65025.0;
}
float Luma(float3 color)
{
    return dot(color, float3(0.299, 0.587, 0.114));
}

float4 DebugPS(float2 uv : TEXCOORD0) : COLOR0
{
    float4 scene = tex2D(SceneSampler, uv);
    if (DebugMode < 0.5)
        return scene;

    if (DebugMode < 1.5)
    {
        if (UseDepth < 0.5)
            return float4(0.35, 0.0, 0.0, 1.0);
        float depth = DecodeDepth24(tex2D(CurrentDepthSampler, uv).rgb);
        float displayDepth = pow(saturate(depth), 0.45);
        return float4(displayDepth, displayDepth, displayDepth, 1.0);
    }

    if (DebugMode < 2.5)
    {
        if (MotionEnabled < 0.5)
            return float4(0.15, 0.15, 0.15, 1.0);
        float4 motion = tex2D(MotionSampler, uv);
        float2 velocity = (motion.rg - 0.5) * 0.25;
        float red = saturate(0.5 + velocity.x * 20.0);
        float green = saturate(0.5 + velocity.y * 20.0);
        return float4(red, green, motion.b, 1.0);
    }

    if (DebugMode < 3.5)
    {
        if (HistoryValid < 0.5)
            return float4(scene.rgb * 0.45, 1.0);
        return tex2D(HistorySampler, uv);
    }

    if (DebugMode < 4.5)
    {
        if (HistoryValid < 0.5)
            return float4(0.0, 0.0, 0.0, 1.0);
        float2 velocity = float2(0.0, 0.0);
        float reactive = 0.0;
        if (MotionEnabled > 0.5)
        {
            float4 motion = tex2D(MotionSampler, uv);
            velocity = (motion.rg - 0.5) * 0.25;
            reactive = motion.b;
        }
        float2 previousUV = saturate(uv + velocity);
        float currentLuma = Luma(scene.rgb);
        float historyLuma = Luma(tex2D(HistorySampler, previousUV).rgb);
        float luminanceReject = saturate(abs(currentLuma - historyLuma) * 3.0);
        float depthReject = 0.0;
        if (UseDepth > 0.5)
        {
            float currentDepth = DecodeDepth24(tex2D(CurrentDepthSampler, uv).rgb);
            float previousDepth = DecodeDepth24(tex2D(PreviousDepthSampler, previousUV).rgb);
            depthReject = saturate(abs(currentDepth - previousDepth) * 80.0);
        }
        return float4(depthReject, luminanceReject, reactive, 1.0);
    }

    if (DebugMode < 5.5 || DebugMode < 6.5)
        return scene;
    if (DebugMode > 7.5)
        return scene;

    // Render-resolution diagnostic: show the active internal-pixel grid over
    // the reconstructed source. The numerical sizes/FPS are printed by Lua.
    float2 pixel = uv / TexelSize;
    float2 edge = min(frac(pixel), 1.0 - frac(pixel));
    float line = 1.0 - step(0.055, min(edge.x, edge.y));
    return float4(lerp(scene.rgb, float3(0.08, 0.78, 1.0), line * 0.65), 1.0);
}

technique Main
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_2_0 DebugPS();
    }
}

technique Fallback
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        Texture[0] = SceneTexture;
        ColorOp[0] = SelectArg1;
        ColorArg1[0] = Texture;
        AlphaOp[0] = SelectArg1;
        AlphaArg1[0] = Texture;
        ColorOp[1] = Disable;
        AlphaOp[1] = Disable;
    }
}

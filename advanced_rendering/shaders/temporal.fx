// Stage 4: temporal accumulation with camera-only reprojection, RGB neighborhood
// clamp, depth disocclusion rejection, luminance/reactive rejection and an
// explicit history-validity guard. No object motion vectors are available here.
texture CurrentTexture;
texture HistoryTexture;
texture CurrentDepth;
texture PreviousDepth;
texture MotionTexture;
float2 TexelSize;
float UseDepth;
float HistoryValid;
float MotionEnabled;
float4 GlobalMotion;
float HistoryWeight;
float DepthThreshold;
float LumaThreshold;

sampler CurrentSampler = sampler_state
{
    Texture = (CurrentTexture);
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

float Luminance(float3 color)
{
    return dot(color, float3(0.299, 0.587, 0.114));
}

float4 TemporalResolvePS(float2 uv : TEXCOORD0) : COLOR0
{
    float4 current = tex2D(CurrentSampler, uv);
    if (HistoryValid < 0.5)
        return float4(current.rgb, 1.0);

    float2 velocity = GlobalMotion.xy;
    float reactive = 0.0;
    if (MotionEnabled > 0.5)
    {
        float4 motion = tex2D(MotionSampler, uv);
        velocity = (motion.rg - 0.5) * 0.25;
        reactive = motion.b;
    }

    float2 previousUV = uv + velocity;
    float insideHistory = step(0.0, previousUV.x) * step(previousUV.x, 1.0)
                        * step(0.0, previousUV.y) * step(previousUV.y, 1.0);
    float4 history = tex2D(HistorySampler, saturate(previousUV));

    // A 4-neighbour current-frame box bounds history color to avoid long trails.
    float3 north = tex2D(CurrentSampler, uv + float2(0.0, -TexelSize.y)).rgb;
    float3 south = tex2D(CurrentSampler, uv + float2(0.0,  TexelSize.y)).rgb;
    float3 east  = tex2D(CurrentSampler, uv + float2( TexelSize.x, 0.0)).rgb;
    float3 west  = tex2D(CurrentSampler, uv + float2(-TexelSize.x, 0.0)).rgb;
    float3 lowColor = min(current.rgb, min(min(north, south), min(east, west)));
    float3 highColor = max(current.rgb, max(max(north, south), max(east, west)));
    float3 clampedHistory = clamp(history.rgb, lowColor - 0.025, highColor + 0.025);
    float clampError = max(abs(history.r - clampedHistory.r), max(abs(history.g - clampedHistory.g), abs(history.b - clampedHistory.b)));

    float disocclusion = 0.0;
    if (UseDepth > 0.5)
    {
        float currentDepth = DecodeDepth24(tex2D(CurrentDepthSampler, uv).rgb);
        float previousDepth = DecodeDepth24(tex2D(PreviousDepthSampler, saturate(previousUV)).rgb);
        float relativeDifference = abs(currentDepth - previousDepth) / max(currentDepth, 0.025);
        disocclusion = saturate((relativeDifference - DepthThreshold) * 18.0);
    }

    float currentLuma = Luminance(current.rgb);
    float historyLuma = Luminance(history.rgb);
    float luminanceReject = saturate((abs(currentLuma - historyLuma) - LumaThreshold) * 5.0);
    float clampReject = saturate(clampError * 4.0);
    float fastMotionReject = saturate(max(abs(velocity.x), abs(velocity.y)) * 8.0);
    float weight = saturate(HistoryWeight) * insideHistory;
    weight *= (1.0 - disocclusion);
    weight *= (1.0 - luminanceReject * 0.88);
    weight *= (1.0 - clampReject * 0.72);
    weight *= (1.0 - reactive * 0.88);
    weight *= (1.0 - fastMotionReject * 0.48);
    weight = min(weight, 0.92);

    return float4(lerp(current.rgb, clampedHistory, weight), 1.0);
}

// Lower-instruction PS 2.0 kernel for older drivers. It retains the
// neighborhood clamp, camera reprojection and optional depth rejection while
// dropping the extra luminance/clamp-error terms that can exceed older limits.
float4 TemporalResolveCompatibilityPS(float2 uv : TEXCOORD0) : COLOR0
{
    float4 current = tex2D(CurrentSampler, uv);
    if (HistoryValid < 0.5)
        return float4(current.rgb, 1.0);

    float2 velocity = GlobalMotion.xy;
    float reactive = 0.0;
    if (MotionEnabled > 0.5)
    {
        float4 motion = tex2D(MotionSampler, uv);
        velocity = (motion.rg - 0.5) * 0.25;
        reactive = motion.b;
    }

    float2 previousUV = uv + velocity;
    float insideHistory = step(0.0, previousUV.x) * step(previousUV.x, 1.0)
                        * step(0.0, previousUV.y) * step(previousUV.y, 1.0);
    float3 history = tex2D(HistorySampler, saturate(previousUV)).rgb;
    float3 north = tex2D(CurrentSampler, uv + float2(0.0, -TexelSize.y)).rgb;
    float3 south = tex2D(CurrentSampler, uv + float2(0.0,  TexelSize.y)).rgb;
    float3 east  = tex2D(CurrentSampler, uv + float2( TexelSize.x, 0.0)).rgb;
    float3 west  = tex2D(CurrentSampler, uv + float2(-TexelSize.x, 0.0)).rgb;
    float3 lowColor = min(current.rgb, min(min(north, south), min(east, west)));
    float3 highColor = max(current.rgb, max(max(north, south), max(east, west)));
    history = clamp(history, lowColor - 0.025, highColor + 0.025);

    float rejection = 0.0;
    if (UseDepth > 0.5)
    {
        float currentDepth = DecodeDepth24(tex2D(CurrentDepthSampler, uv).rgb);
        float previousDepth = DecodeDepth24(tex2D(PreviousDepthSampler, saturate(previousUV)).rgb);
        float relativeDifference = abs(currentDepth - previousDepth) / max(currentDepth, 0.025);
        rejection = saturate((relativeDifference - DepthThreshold) * 18.0);
    }

    float motionReject = saturate(max(abs(velocity.x), abs(velocity.y)) * 8.0);
    float weight = saturate(HistoryWeight) * insideHistory;
    weight *= (1.0 - rejection);
    weight *= (1.0 - reactive * 0.88);
    weight *= (1.0 - motionReject * 0.48);
    weight = min(weight, 0.88);
    return float4(lerp(current.rgb, history, weight), 1.0);
}

technique HighQuality
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_3_0 TemporalResolvePS();
    }
}

technique Compatibility
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        AlphaBlendEnable = FALSE;
        PixelShader = compile ps_2_0 TemporalResolveCompatibilityPS();
    }
}

technique Fallback
{
    pass P0
    {
        ZEnable = FALSE;
        ZWriteEnable = FALSE;
        Texture[0] = CurrentTexture;
        ColorOp[0] = SelectArg1;
        ColorArg1[0] = Texture;
        AlphaOp[0] = SelectArg1;
        AlphaArg1[0] = Texture;
        ColorOp[1] = Disable;
        AlphaOp[1] = Disable;
    }
}

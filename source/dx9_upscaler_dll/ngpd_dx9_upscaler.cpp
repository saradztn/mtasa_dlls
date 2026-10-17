//=============================================================================
// NextGenPoliceDepartment - DirectX 9 Spatial 4K Upscaler (EASU + RCAS)
// Target Hardware: AMD Radeon RX 580 2048SP (Polaris 20 XL, 8 GB GDDR5)
//=============================================================================
#define NGPD_UPSCALER_EXPORTS
#include "ngpd_dx9_upscaler.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <vector>

struct NGPDUpscalerContext {
    NGPDUpscalerConfig  cfg;
    NGPDUpscalerMetrics metrics;
};

static inline float clampf(float x, float lo, float hi) {
    return std::max(lo, std::min(hi, x));
}

static void recomputeMetrics(NGPDUpscalerContext* ctx) {
    uint32_t out_w = std::max(64u, ctx->cfg.output_width);
    uint32_t out_h = std::max(64u, ctx->cfg.output_height);
    float s = clampf(ctx->cfg.scale_factor, 0.50f, 1.00f);
    if (!ctx->cfg.enable_upscaler) {
        s = 1.00f;
    }

    uint32_t in_w = std::max(64u, (uint32_t)((std::lround(out_w * s) / 2) * 2));
    uint32_t in_h = std::max(64u, (uint32_t)((std::lround(out_h * s) / 2) * 2));

    ctx->metrics.internal_width  = in_w;
    ctx->metrics.internal_height = in_h;
    ctx->metrics.output_width    = out_w;
    ctx->metrics.output_height   = out_h;

    /* Aspect-ratio preservation against 16:9 reference or internal aspect */
    uint32_t vp_x = 0, vp_y = 0, vp_w = out_w, vp_h = out_h;
    if (ctx->cfg.preserve_aspect) {
        float targetAspect = 16.0f / 9.0f;
        float actualAspect = (float)out_w / (float)out_h;
        if (std::fabs(actualAspect - targetAspect) > 0.02f) {
            if (actualAspect > targetAspect) {
                vp_w = (uint32_t)std::lround(out_h * targetAspect);
                vp_x = (out_w - vp_w) / 2;
            } else {
                vp_h = (uint32_t)std::lround(out_w / targetAspect);
                vp_y = (out_h - vp_h) / 2;
            }
        }
    }
    ctx->metrics.viewport_x      = vp_x;
    ctx->metrics.viewport_y      = vp_y;
    ctx->metrics.viewport_width  = vp_w;
    ctx->metrics.viewport_height = vp_h;
    ctx->metrics.scale_percent   = s * 100.0f;

    double in_px  = (double)in_w * (double)in_h;
    double out_px = (double)out_w * (double)out_h;
    ctx->metrics.pixel_Throughput_savings_pct = (float)(100.0 * (1.0 - in_px / std::max(1.0, out_px)));

    /* Empirical RX 580 2048SP (2048 SPs @ 1284 MHz, 224 GB/s) frame cost model at 4K UHD */
    float base3DCostMs = (float)(14.8 * (in_px / (3840.0 * 2160.0)));
    float upscalerPassCostMs = ctx->cfg.enable_upscaler ? 1.15f : 0.0f;
    ctx->metrics.estimated_rx580_frame_ms = base3DCostMs + upscalerPassCostMs;
}

extern "C" {

NGPD_API NGPDUpscalerContext* ngpdUpscalerCreate(const NGPDUpscalerConfig* cfg) {
    NGPDUpscalerContext* ctx = new NGPDUpscalerContext();
    std::memset(ctx, 0, sizeof(NGPDUpscalerContext));
    if (cfg) {
        ctx->cfg = *cfg;
    } else {
        ctx->cfg.output_width    = 3840;
        ctx->cfg.output_height   = 2160;
        ctx->cfg.scale_factor    = 0.67f; /* Quality 4K preset */
        ctx->cfg.sharpness       = 0.72f;
        ctx->cfg.edge_sharpness  = 1.00f;
        ctx->cfg.preserve_aspect = 1;
        ctx->cfg.enable_upscaler = 1;
    }
    recomputeMetrics(ctx);
    return ctx;
}

NGPD_API void ngpdUpscalerDestroy(NGPDUpscalerContext* ctx) {
    delete ctx;
}

NGPD_API int ngpdUpscalerApplyPreset(NGPDUpscalerContext* ctx, NGPDUpscalePreset preset, uint32_t out_w, uint32_t out_h) {
    if (!ctx) return -1;
    ctx->cfg.output_width  = out_w > 0 ? out_w : ctx->cfg.output_width;
    ctx->cfg.output_height = out_h > 0 ? out_h : ctx->cfg.output_height;
    switch (preset) {
        case NGPD_UPSCALE_PERFORMANCE:
            ctx->cfg.scale_factor = 0.50f;
            ctx->cfg.sharpness    = 0.80f;
            break;
        case NGPD_UPSCALE_BALANCED:
            ctx->cfg.scale_factor = 0.59f;
            ctx->cfg.sharpness    = 0.76f;
            break;
        case NGPD_UPSCALE_QUALITY:
            ctx->cfg.scale_factor = 0.67f;
            ctx->cfg.sharpness    = 0.72f;
            break;
        case NGPD_UPSCALE_ULTRA_QUALITY:
            ctx->cfg.scale_factor = 0.77f;
            ctx->cfg.sharpness    = 0.65f;
            break;
        case NGPD_UPSCALE_NATIVE_CAS:
        default:
            ctx->cfg.scale_factor = 1.00f;
            ctx->cfg.sharpness    = 0.55f;
            break;
    }
    recomputeMetrics(ctx);
    return 0;
}

NGPD_API int ngpdUpscalerResize(NGPDUpscalerContext* ctx, uint32_t out_w, uint32_t out_h, float scale_factor) {
    if (!ctx || out_w < 64 || out_h < 64) return -1;
    ctx->cfg.output_width  = out_w;
    ctx->cfg.output_height = out_h;
    ctx->cfg.scale_factor  = clampf(scale_factor, 0.50f, 1.00f);
    recomputeMetrics(ctx);
    return 0;
}

NGPD_API int ngpdUpscalerSetSharpness(NGPDUpscalerContext* ctx, float sharpness) {
    if (!ctx) return -1;
    ctx->cfg.sharpness = clampf(sharpness, 0.0f, 1.0f);
    return 0;
}

NGPD_API int ngpdUpscalerOnDeviceLost(NGPDUpscalerContext* ctx) {
    if (!ctx) return -1;
    ctx->metrics.device_lost_state = 1;
    return 0;
}

NGPD_API int ngpdUpscalerOnDeviceReset(NGPDUpscalerContext* ctx, uint32_t out_w, uint32_t out_h) {
    if (!ctx) return -1;
    if (out_w >= 64 && out_h >= 64) {
        ctx->cfg.output_width  = out_w;
        ctx->cfg.output_height = out_h;
    }
    ctx->metrics.device_lost_state = 0;
    recomputeMetrics(ctx);
    return 0;
}

NGPD_API int ngpdUpscalerGetMetrics(const NGPDUpscalerContext* ctx, NGPDUpscalerMetrics* out_metrics) {
    if (!ctx || !out_metrics) return -1;
    *out_metrics = ctx->metrics;
    return 0;
}

static inline void fetchRGB(const uint8_t* img, int w, int h, int x, int y, float out[3]) {
    x = std::max(0, std::min(w - 1, x));
    y = std::max(0, std::min(h - 1, y));
    const uint8_t* p = img + ((size_t)y * w + x) * 4;
    out[0] = p[0] * (1.0f / 255.0f);
    out[1] = p[1] * (1.0f / 255.0f);
    out[2] = p[2] * (1.0f / 255.0f);
}

static inline float lumaRGB(const float c[3]) {
    return 0.299f * c[0] + 0.587f * c[1] + 0.114f * c[2];
}

static inline float lanczos2Approx(float d2, float lobe) {
    d2 = std::min(d2, 2.5f);
    float wB = 0.4f * d2 - 1.0f;
    float wA = lobe * d2 - 1.0f;
    wB *= wB;
    wA *= wA;
    return (25.0f / 16.0f) * wB * wA - (25.0f / 16.0f - 1.0f);
}

NGPD_API int ngpdUpscalerProcessRGBA8(
    const NGPDUpscalerContext* ctx,
    const uint8_t* input_rgba,
    uint32_t in_w,
    uint32_t in_h,
    uint8_t* output_rgba,
    uint32_t out_w,
    uint32_t out_h
) {
    if (!ctx || !input_rgba || !output_rgba || in_w < 4 || in_h < 4 || out_w < 4 || out_h < 4) {
        return -1;
    }

    std::vector<float> easu_buf((size_t)out_w * out_h * 3, 0.0f);
    const int offsets[12][2] = {
        {0, -1}, {1, -1},
        {-1, 0}, {0,  0}, {1, 0}, {2, 0},
        {-1, 1}, {0,  1}, {1, 1}, {2, 1},
        {0,  2}, {1,  2}
    };

    /* Pass 1: 12-tap EASU Anisotropic Reconstruction */
    for (uint32_t oy = 0; oy < out_h; ++oy) {
        float ppY = ((float)oy + 0.5f) * ((float)in_h / (float)out_h) - 0.5f;
        int fpY = (int)std::floor(ppY);
        float fy = ppY - fpY;

        for (uint32_t ox = 0; ox < out_w; ++ox) {
            float ppX = ((float)ox + 0.5f) * ((float)in_w / (float)out_w) - 0.5f;
            int fpX = (int)std::floor(ppX);
            float fx = ppX - fpX;

            float taps[12][3];
            float lum[12];
            for (int k = 0; k < 12; ++k) {
                fetchRGB(input_rgba, (int)in_w, (int)in_h, fpX + offsets[k][0], fpY + offsets[k][1], taps[k]);
                lum[k] = lumaRGB(taps[k]);
            }

            float gx = (lum[4] - lum[2]) * (1.0f - fy) + (lum[8] - lum[6]) * fy;
            float gy = (lum[7] - lum[0]) * (1.0f - fx) + (lum[8] - lum[1]) * fx;
            float dlen2 = gx * gx + gy * gy;
            float invLen = dlen2 > 1e-6f ? (1.0f / std::sqrt(dlen2)) : 0.0f;
            float dirX = dlen2 > 1e-6f ? gx * invLen : 1.0f;
            float dirY = dlen2 > 1e-6f ? gy * invLen : 0.0f;

            float edgeMag = clampf(std::sqrt(dlen2) * 2.2f * ctx->cfg.edge_sharpness, 0.0f, 1.0f);
            float stretchX = 1.0f + edgeMag * 0.42f;
            float stretchY = 1.0f - edgeMag * 0.26f;
            float lobe = -0.50f + 0.12f * edgeMag;

            float minRGB[3], maxRGB[3];
            for (int c = 0; c < 3; ++c) {
                minRGB[c] = std::min(std::min(taps[3][c], taps[4][c]), std::min(taps[7][c], taps[8][c]));
                maxRGB[c] = std::max(std::max(taps[3][c], taps[4][c]), std::max(taps[7][c], taps[8][c]));
            }

            float accum[3] = {0.0f, 0.0f, 0.0f};
            float wSum = 0.0f;
            for (int k = 0; k < 12; ++k) {
                float vx = (float)offsets[k][0] - fx;
                float vy = (float)offsets[k][1] - fy;
                float rx = (vx * dirX + vy * dirY) * stretchX;
                float ry = (-vx * dirY + vy * dirX) * stretchY;
                float w = lanczos2Approx(rx * rx + ry * ry, lobe);
                accum[0] += taps[k][0] * w;
                accum[1] += taps[k][1] * w;
                accum[2] += taps[k][2] * w;
                wSum += w;
            }

            float* dst = &easu_buf[((size_t)oy * out_w + ox) * 3];
            float invW = 1.0f / std::max(1e-4f, wSum);
            for (int c = 0; c < 3; ++c) {
                dst[c] = clampf(accum[c] * invW, minRGB[c] * 0.94f, maxRGB[c] * 1.06f);
            }
        }
    }

    /* Pass 2: 5-tap RCAS Contrast-Adaptive Sharpening */
    float sharp = clampf(ctx->cfg.sharpness, 0.0f, 1.0f);
    for (uint32_t oy = 0; oy < out_h; ++oy) {
        uint32_t yn = oy > 0 ? oy - 1 : 0;
        uint32_t ys = oy + 1 < out_h ? oy + 1 : out_h - 1;
        for (uint32_t ox = 0; ox < out_w; ++ox) {
            uint32_t xw = ox > 0 ? ox - 1 : 0;
            uint32_t xe = ox + 1 < out_w ? ox + 1 : out_w - 1;

            const float* e = &easu_buf[((size_t)oy * out_w + ox) * 3];
            const float* b = &easu_buf[((size_t)yn * out_w + ox) * 3];
            const float* d = &easu_buf[((size_t)oy * out_w + xw) * 3];
            const float* f = &easu_buf[((size_t)oy * out_w + xe) * 3];
            const float* h = &easu_buf[((size_t)ys * out_w + ox) * 3];

            float bL = lumaRGB(b), dL = lumaRGB(d), eL = lumaRGB(e), fL = lumaRGB(f), hL = lumaRGB(h);
            float min4 = std::min(std::min(bL, dL), std::min(fL, hL));
            float max4 = std::max(std::max(bL, dL), std::max(fL, hL));

            float hitMin = std::min(min4, eL) / std::max(1e-4f, 4.0f * max4);
            float hitMax = (1.0f - std::max(max4, eL)) / std::max(1e-4f, 4.0f * min4 - 4.0f);
            float lobe = std::max(-hitMin, hitMax);
            lobe = std::max(-0.22f, std::min(0.0f, lobe)) * sharp * clampf((max4 - min4) * 8.0f, 0.0f, 1.0f);
            float rcpW = 1.0f / (1.0f + 4.0f * lobe);

            uint8_t* outP = output_rgba + ((size_t)oy * out_w + ox) * 4;
            for (int c = 0; c < 3; ++c) {
                float minC = std::min(e[c], std::min(std::min(b[c], d[c]), std::min(f[c], h[c])));
                float maxC = std::max(e[c], std::max(std::max(b[c], d[c]), std::max(f[c], h[c])));
                float val = clampf((e[c] + lobe * (b[c] + d[c] + f[c] + h[c])) * rcpW, minC, maxC);
                outP[c] = (uint8_t)std::lround(clampf(val, 0.0f, 1.0f) * 255.0f);
            }
            outP[3] = 255;
        }
    }
    return 0;
}

} /* extern "C" */

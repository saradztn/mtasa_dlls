#ifndef NGPD_DX9_UPSCALER_H
#define NGPD_DX9_UPSCALER_H

#include <stdint.h>
#include <stddef.h>

#ifdef _WIN32
  #ifdef NGPD_UPSCALER_EXPORTS
    #define NGPD_API __declspec(dllexport)
  #else
    #define NGPD_API __declspec(dllimport)
  #endif
#else
  #define NGPD_API __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

typedef enum NGPDUpscalePreset {
    NGPD_UPSCALE_PERFORMANCE   = 0, /* 50% internal scale (1920x1080 -> 3840x2160) */
    NGPD_UPSCALE_BALANCED      = 1, /* 59% internal scale (2266x1274 -> 3840x2160) */
    NGPD_UPSCALE_QUALITY       = 2, /* 67% internal scale (2572x1448 -> 3840x2160) */
    NGPD_UPSCALE_ULTRA_QUALITY = 3, /* 77% internal scale (2956x1664 -> 3840x2160) */
    NGPD_UPSCALE_NATIVE_CAS    = 4  /* 100% internal scale (RCAS sharpening only)  */
} NGPDUpscalePreset;

typedef struct NGPDUpscalerConfig {
    uint32_t output_width;       /* Target display/output width, e.g., 3840 */
    uint32_t output_height;      /* Target display/output height, e.g., 2160 */
    float    scale_factor;       /* Internal resolution scale in [0.50, 1.00] */
    float    sharpness;          /* RCAS sharpness in [0.00, 1.00] (0.72 recommended for RX 580) */
    float    edge_sharpness;     /* EASU directional edge strength in [0.50, 1.50] */
    int      preserve_aspect;    /* 1 = preserve aspect ratio with letterbox/pillarbox */
    int      enable_upscaler;    /* 1 = active, 0 = bypass */
} NGPDUpscalerConfig;

typedef struct NGPDUpscalerMetrics {
    uint32_t internal_width;
    uint32_t internal_height;
    uint32_t output_width;
    uint32_t output_height;
    uint32_t viewport_x;
    uint32_t viewport_y;
    uint32_t viewport_width;
    uint32_t viewport_height;
    float    scale_percent;
    float    pixel_Throughput_savings_pct;
    float    estimated_rx580_frame_ms;
    int      device_lost_state;
} NGPDUpscalerMetrics;

typedef struct NGPDUpscalerContext NGPDUpscalerContext;

NGPD_API NGPDUpscalerContext* ngpdUpscalerCreate(const NGPDUpscalerConfig* cfg);
NGPD_API void                 ngpdUpscalerDestroy(NGPDUpscalerContext* ctx);
NGPD_API int                  ngpdUpscalerApplyPreset(NGPDUpscalerContext* ctx, NGPDUpscalePreset preset, uint32_t out_w, uint32_t out_h);
NGPD_API int                  ngpdUpscalerResize(NGPDUpscalerContext* ctx, uint32_t out_w, uint32_t out_h, float scale_factor);
NGPD_API int                  ngpdUpscalerSetSharpness(NGPDUpscalerContext* ctx, float sharpness);
NGPD_API int                  ngpdUpscalerOnDeviceLost(NGPDUpscalerContext* ctx);
NGPD_API int                  ngpdUpscalerOnDeviceReset(NGPDUpscalerContext* ctx, uint32_t out_w, uint32_t out_h);
NGPD_API int                  ngpdUpscalerGetMetrics(const NGPDUpscalerContext* ctx, NGPDUpscalerMetrics* out_metrics);

/* Executes two-pass EASU + RCAS spatial upscaling on RGBA8 buffer (used for offline verification & CPU fallback) */
NGPD_API int                  ngpdUpscalerProcessRGBA8(
    const NGPDUpscalerContext* ctx,
    const uint8_t* input_rgba,
    uint32_t in_w,
    uint32_t in_h,
    uint8_t* output_rgba,
    uint32_t out_w,
    uint32_t out_h
);

#ifdef __cplusplus
}
#endif

#endif /* NGPD_DX9_UPSCALER_H */

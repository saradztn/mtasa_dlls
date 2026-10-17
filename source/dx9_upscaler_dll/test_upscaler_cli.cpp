#include "ngpd_dx9_upscaler.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <vector>

int main() {
    NGPDUpscalerContext* ctx = ngpdUpscalerCreate(nullptr);
    assert(ctx != nullptr);

    NGPDUpscalerMetrics m{};
    assert(ngpdUpscalerGetMetrics(ctx, &m) == 0);
    assert(m.output_width == 3840 && m.output_height == 2160);
    assert(m.internal_width == 2572 && m.internal_height == 1446);

    const char* presetNames[5] = {"Performance", "Balanced", "Quality", "UltraQuality", "NativeCAS"};
    for (int p = 0; p < 5; ++p) {
        assert(ngpdUpscalerApplyPreset(ctx, (NGPDUpscalePreset)p, 3840, 2160) == 0);
        assert(ngpdUpscalerGetMetrics(ctx, &m) == 0);
        std::printf("[Preset %-12s] Internal: %4ux%4u -> Output: %4ux%4u | Scale: %5.1f%% | Pixel Savings: %5.1f%% | Est RX 580 2048SP: %.2f ms\n",
            presetNames[p], m.internal_width, m.internal_height, m.output_width, m.output_height,
            m.scale_percent, m.pixel_Throughput_savings_pct, m.estimated_rx580_frame_ms);
    }

    /* Verify ultrawide 3440x1440 aspect-ratio preservation */
    assert(ngpdUpscalerResize(ctx, 3440, 1440, 0.67f) == 0);
    assert(ngpdUpscalerGetMetrics(ctx, &m) == 0);
    assert(m.viewport_width == 2560 && m.viewport_height == 1440 && m.viewport_x == 440);

    /* Verify Device Lost / Reset recovery */
    assert(ngpdUpscalerOnDeviceLost(ctx) == 0);
    assert(ngpdUpscalerGetMetrics(ctx, &m) == 0 && m.device_lost_state == 1);
    assert(ngpdUpscalerOnDeviceReset(ctx, 3840, 2160) == 0);
    assert(ngpdUpscalerGetMetrics(ctx, &m) == 0 && m.device_lost_state == 0);

    /* Verify two-pass EASU + RCAS RGBA8 image reconstruction */
    uint32_t inW = 64, inH = 36, outW = 128, outH = 72;
    std::vector<uint8_t> src(inW * inH * 4, 0);
    std::vector<uint8_t> dst(outW * outH * 4, 0);
    for (uint32_t y = 0; y < inH; ++y) {
        for (uint32_t x = 0; x < inW; ++x) {
            bool diag = (x * 9 > y * 16);
            uint8_t* p = &src[(y * inW + x) * 4];
            p[0] = diag ? 235 : 28;
            p[1] = diag ? 185 : 34;
            p[2] = diag ? 110 : 48;
            p[3] = 255;
        }
    }
    assert(ngpdUpscalerProcessRGBA8(ctx, src.data(), inW, inH, dst.data(), outW, outH) == 0);
    assert(dst[3] == 255);

    ngpdUpscalerDestroy(ctx);
    std::printf("ALL C++ DX9 UPSCALER TESTS PASSED.\n");
    return 0;
}

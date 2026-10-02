/* Created by: Arena.ai Agent Mode (AI) - Castle MTA:SA asset pipeline
 * render2.c - tiny game-like software rasteriser used for previews / QA only (not a game asset).
 * Mimics the San Andreas pipeline: final colour = texture * baked vertex colour (modulate),
 * alpha textures drawn after the opaque pass (alpha blended), emissive = already fullbright in the vertex colours. */
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef struct { float x, y, z; } V3;
static V3 v3(float x, float y, float z) { V3 r = {x, y, z}; return r; }
static V3 sub(V3 a, V3 b) { return v3(a.x - b.x, a.y - b.y, a.z - b.z); }
static float dot(V3 a, V3 b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
static V3 cross(V3 a, V3 b) { return v3(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x); }
static V3 norm(V3 a) { float l = sqrtf(dot(a, a)); if (l < 1e-12f) l = 1; return v3(a.x / l, a.y / l, a.z / l); }

#define MAXLEV 12
/* texinfo per material: [nlev, (w,h,offset)*MAXLEV] ; data: RGBA uint8 */
static void sample(const int *ti, const uint8_t *data, float u, float v, float lod, float *o) {
    int nl = ti[0];
    int l0 = (int)floorf(lod); if (l0 < 0) l0 = 0; if (l0 > nl - 1) l0 = nl - 1;
    int w = ti[1 + 3 * l0], h = ti[2 + 3 * l0], off = ti[3 + 3 * l0];
    u = u - floorf(u); v = v - floorf(v);
    float fx = u * w - 0.5f, fy = v * h - 0.5f;
    int x0 = (int)floorf(fx), y0 = (int)floorf(fy);
    float ax = fx - x0, ay = fy - y0;
    for (int c = 0; c < 4; c++) o[c] = 0;
    for (int j = 0; j < 2; j++) for (int i = 0; i < 2; i++) {
        int xx = ((x0 + i) % w + w) % w, yy = ((y0 + j) % h + h) % h;
        float wgt = (i ? ax : 1 - ax) * (j ? ay : 1 - ay);
        const uint8_t *p = data + (size_t)off + ((size_t)yy * w + xx) * 4;
        for (int c = 0; c < 4; c++) o[c] += wgt * p[c] / 255.0f;
    }
}

int render2(int W, int H, int nv, const float *pos, const float *uv, const float *vcol, int nt, const int *tris, const int *tmat,
            int nmat, const int *texinfo, const uint8_t *texdata, const int *alpha_mat, const float *cam, float gamma, float *out,
            int ncut, const float *cuts, const float *bg) {
    V3 eye = v3(cam[0], cam[1], cam[2]), tgt = v3(cam[3], cam[4], cam[5]), up = v3(cam[6], cam[7], cam[8]);
    float fov = cam[9];
    V3 f = norm(sub(tgt, eye)), r = norm(cross(f, up)), u = cross(r, f);
    float th = tanf(fov * 0.5f * 3.14159265f / 180.0f), asp = (float)W / H;
    float *zb = (float *)malloc(sizeof(float) * W * H);
    for (int i = 0; i < W * H; i++) { zb[i] = 1e30f; out[3 * i] = bg[0]; out[3 * i + 1] = bg[1]; out[3 * i + 2] = bg[2]; }
    float *sx = (float *)malloc(sizeof(float) * nv * 3);
    for (int i = 0; i < nv; i++) {
        V3 p = sub(v3(pos[3 * i], pos[3 * i + 1], pos[3 * i + 2]), eye);
        float cz = dot(p, f), cx = dot(p, r), cy = dot(p, u);
        sx[3 * i + 2] = cz;
        if (cz > 0.05f) { sx[3 * i] = (cx / (cz * th * asp) * 0.5f + 0.5f) * W; sx[3 * i + 1] = (0.5f - cy / (cz * th) * 0.5f) * H; }
        else { sx[3 * i] = sx[3 * i + 1] = 0; }
    }
    for (int pass = 0; pass < 2; pass++) {
        for (int t = 0; t < nt; t++) {
            int m = tmat[t];
            int isa = alpha_mat[m];
            if (isa != pass) continue;
            int i0 = tris[3 * t], i1 = tris[3 * t + 1], i2 = tris[3 * t + 2];
            if (sx[3 * i0 + 2] < 0.05f || sx[3 * i1 + 2] < 0.05f || sx[3 * i2 + 2] < 0.05f) continue;
            V3 P0 = v3(pos[3 * i0], pos[3 * i0 + 1], pos[3 * i0 + 2]), P1 = v3(pos[3 * i1], pos[3 * i1 + 1], pos[3 * i1 + 2]), P2 = v3(pos[3 * i2], pos[3 * i2 + 1], pos[3 * i2 + 2]);
            int cut = 0;
            V3 cen = v3((P0.x + P1.x + P2.x) / 3, (P0.y + P1.y + P2.y) / 3, (P0.z + P1.z + P2.z) / 3);
            for (int k = 0; k < ncut; k++) { if (cen.x * cuts[4 * k] + cen.y * cuts[4 * k + 1] + cen.z * cuts[4 * k + 2] > cuts[4 * k + 3]) cut = 1; }
            if (cut) continue;
            /* back face culling like SA (CCW front) */
            V3 nf = cross(sub(P1, P0), sub(P2, P0));
            if (dot(nf, sub(eye, P0)) <= 0) continue;
            float x0 = sx[3 * i0], y0 = sx[3 * i0 + 1], x1 = sx[3 * i1], y1 = sx[3 * i1 + 1], x2 = sx[3 * i2], y2 = sx[3 * i2 + 1];
            float area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0);
            if (fabsf(area) < 1e-9f) continue;
            float minx = fminf(x0, fminf(x1, x2)), maxx = fmaxf(x0, fmaxf(x1, x2)), miny = fminf(y0, fminf(y1, y2)), maxy = fmaxf(y0, fmaxf(y1, y2));
            int ix0 = (int)fmaxf(0, floorf(minx)), ix1 = (int)fminf(W - 1, ceilf(maxx)), iy0 = (int)fmaxf(0, floorf(miny)), iy1 = (int)fminf(H - 1, ceilf(maxy));
            if (ix0 > ix1 || iy0 > iy1) continue;
            float iz0 = 1.0f / sx[3 * i0 + 2], iz1 = 1.0f / sx[3 * i1 + 2], iz2 = 1.0f / sx[3 * i2 + 2];
            float u0 = uv[2 * i0], v0 = uv[2 * i0 + 1], u1 = uv[2 * i1], v1 = uv[2 * i1 + 1], u2 = uv[2 * i2], v2 = uv[2 * i2 + 1];
            const int *ti = texinfo + m * (1 + 3 * MAXLEV);
            float tw = (float)ti[1], thh = (float)ti[2];
            float uvarea = fabsf((u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)) * tw * thh;
            float lod = 0.5f * log2f(fmaxf(uvarea, 1e-9f) / fmaxf(fabsf(area), 1e-3f));
            lod = fmaxf(0.0f, lod - 0.35f);
            for (int y = iy0; y <= iy1; y++) for (int x = ix0; x <= ix1; x++) {
                float px = x + 0.5f, py = y + 0.5f;
                float w0 = ((x1 - px) * (y2 - py) - (x2 - px) * (y1 - py)) / area;
                float w1 = ((x2 - px) * (y0 - py) - (x0 - px) * (y2 - py)) / area;
                float w2 = 1 - w0 - w1;
                if (w0 < -1e-5f || w1 < -1e-5f || w2 < -1e-5f) continue;
                float iz = w0 * iz0 + w1 * iz1 + w2 * iz2;
                float z = 1.0f / iz;
                int idx = y * W + x;
                if (z >= zb[idx]) continue;
                float pu = (w0 * u0 * iz0 + w1 * u1 * iz1 + w2 * u2 * iz2) / iz;
                float pv = (w0 * v0 * iz0 + w1 * v1 * iz1 + w2 * v2 * iz2) / iz;
                float c[4];
                sample(ti, texdata, pu, pv, lod, c);
                float cr = (w0 * vcol[3 * i0] * iz0 + w1 * vcol[3 * i1] * iz1 + w2 * vcol[3 * i2] * iz2) / iz;
                float cg = (w0 * vcol[3 * i0 + 1] * iz0 + w1 * vcol[3 * i1 + 1] * iz1 + w2 * vcol[3 * i2 + 1] * iz2) / iz;
                float cb = (w0 * vcol[3 * i0 + 2] * iz0 + w1 * vcol[3 * i1 + 2] * iz1 + w2 * vcol[3 * i2 + 2] * iz2) / iz;
                float rr = c[0] * cr, gg = c[1] * cg, bb = c[2] * cb;
                if (!isa) {
                    zb[idx] = z;
                    out[3 * idx] = rr; out[3 * idx + 1] = gg; out[3 * idx + 2] = bb;
                } else {
                    float a = c[3];
                    if (a < 0.02f) continue;
                    out[3 * idx] = out[3 * idx] * (1 - a) + rr * a;
                    out[3 * idx + 1] = out[3 * idx + 1] * (1 - a) + gg * a;
                    out[3 * idx + 2] = out[3 * idx + 2] * (1 - a) + bb * a;
                }
            }
        }
    }
    free(zb); free(sx);
    return 0;
}

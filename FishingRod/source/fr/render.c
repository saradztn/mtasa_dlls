/* Created by: Arena.ai Agent Mode (AI) - FishingRod MTA:SA asset pipeline
 *
 * render.c - tiny deferred software rasteriser used ONLY to produce the preview
 * PNGs and to visually QA the exported DFF/TXD data.  It is NOT part of the
 * game assets.  It samples the decoded TXD diffuse textures (with mip-maps) and
 * the PBR companion maps (normal / ORM) with a studio-lit GGX shading model,
 * which is what the optional MTA shader (FishingRod.fx) reproduces in-game.
 *
 * Build: gcc -O3 -fopenmp -shared -fPIC render.c -o librender.so -lm
 */
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef struct { float x, y, z; } V3;
static inline V3 v3(float x, float y, float z) { V3 r = {x, y, z}; return r; }
static inline V3 add(V3 a, V3 b) { return v3(a.x + b.x, a.y + b.y, a.z + b.z); }
static inline V3 sub(V3 a, V3 b) { return v3(a.x - b.x, a.y - b.y, a.z - b.z); }
static inline V3 mul(V3 a, float s) { return v3(a.x * s, a.y * s, a.z * s); }
static inline float dot(V3 a, V3 b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
static inline V3 cross(V3 a, V3 b) { return v3(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x); }
static inline V3 normv(V3 a) { float l = sqrtf(dot(a, a)); return l > 1e-20f ? mul(a, 1.0f / l) : a; }
static inline float clampf(float x, float a, float b) { return x < a ? a : (x > b ? b : x); }
static inline float smooth(float a, float b, float x) { float t = clampf((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); }

#define MAXLEV 12
/* texture info layout (ints): [nlev, (w,h,off)*MAXLEV]  -> 1+3*MAXLEV ints */
#define TI (1 + 3 * MAXLEV)

static void samp(const int *ti, const uint8_t *data, float u, float v, float lod, float out[3]) {
    int nl = ti[0];
    if (nl <= 0) { out[0] = out[1] = out[2] = 0.5f; return; }
    if (lod < 0) lod = 0;
    if (lod > nl - 1) lod = (float)(nl - 1);
    int l0 = (int)lod;
    int l1 = l0 + 1 < nl ? l0 + 1 : l0;
    float f = lod - l0;
    float acc[2][3];
    int lv[2] = {l0, l1};
    for (int k = 0; k < 2; k++) {
        int w = ti[1 + 3 * lv[k]], h = ti[2 + 3 * lv[k]], off = ti[3 + 3 * lv[k]];
        float x = u * w - 0.5f, y = v * h - 0.5f;
        float fx = floorf(x), fy = floorf(y);
        int x0 = (int)fx, y0 = (int)fy;
        float ax = x - fx, ay = y - fy;
        int xs[2] = {x0, x0 + 1}, ys[2] = {y0, y0 + 1};
        for (int c = 0; c < 3; c++) acc[k][c] = 0;
        for (int j = 0; j < 2; j++) for (int i = 0; i < 2; i++) {
            int xx = ((xs[i] % w) + w) % w, yy = ((ys[j] % h) + h) % h;
            float wgt = (i ? ax : 1 - ax) * (j ? ay : 1 - ay);
            const uint8_t *p = data + off + 3 * (yy * w + xx);
            for (int c = 0; c < 3; c++) acc[k][c] += wgt * p[c];
        }
    }
    for (int c = 0; c < 3; c++) out[c] = ((1 - f) * acc[0][c] + f * acc[1][c]) / 255.0f;
}

/* procedural studio environment: soft boxes + gradient.  rough in 0..1 blurs it */
static V3 env(V3 d, float rough) {
    float t = d.z * 0.5f + 0.5f;
    float blur = clampf(rough * rough * 1.6f, 0, 1);
    /* base gradient: bright overhead, mid horizon, darker floor */
    float g = 0.10f + 0.55f * smooth(0.0f, 1.0f, t) + 0.20f * smooth(0.45f, 0.55f, t);
    V3 base = v3(g * 0.95f, g * 0.97f, g * 1.0f);
    /* key softbox (front-left, high), strip light (right), rim strip (back) */
    V3 kd = normv(v3(-0.55f, -0.65f, 0.55f));
    V3 sd = normv(v3(0.85f, 0.15f, 0.25f));
    V3 rd = normv(v3(0.1f, 0.95f, 0.30f));
    float w0 = 0.10f + 0.9f * blur;
    float k = smooth(1.0f - 0.20f * (w0 + 0.2f), 1.0f, dot(d, kd));
    float s = smooth(1.0f - 0.07f * (w0 + 0.25f), 1.0f, dot(d, sd));
    float r = smooth(1.0f - 0.06f * (w0 + 0.25f), 1.0f, dot(d, rd));
    V3 col = base;
    float kk = 5.0f * k * (1.0f - 0.55f * blur), ss = 3.6f * s * (1.0f - 0.5f * blur), rr = 2.6f * r * (1.0f - 0.5f * blur);
    col = add(col, v3(kk * 1.00f, kk * 0.97f, kk * 0.92f));
    col = add(col, v3(ss * 0.85f, ss * 0.92f, ss * 1.0f));
    col = add(col, v3(rr * 1.0f, rr * 1.0f, rr * 1.0f));
    /* average for very rough surfaces */
    V3 avg = v3(0.55f, 0.56f, 0.58f);
    float m = smooth(0.55f, 1.0f, rough);
    return add(mul(col, 1 - m), mul(avg, m));
}

static float ggx(float nh, float a) {
    float a2 = a * a;
    float d = nh * nh * (a2 - 1) + 1;
    return a2 / (3.14159265f * d * d + 1e-7f);
}

typedef struct {
    float sx[3], sy[3], iz[3];
} dummy_t;

int render(int W, int H, int nv, const float *pos, const float *nrm, const float *uv,
           int nt, const int *tris, const int *tmat, int nmat,
           const int *texinfo, const uint8_t *texdata,   /* nmat*3 textures: albedo, normal, orm */
           const float *matparam,                         /* nmat*8: fallback rgb, rough, metal, unused.. */
           const float *cam,                              /* eye3, target3, up3, fovdeg, ortho(0/1), orthoh */
           const float *opts,                             /* bg gamma ... */
           float *outrgb)
{
    V3 eye = v3(cam[0], cam[1], cam[2]), tgt = v3(cam[3], cam[4], cam[5]), upv = v3(cam[6], cam[7], cam[8]);
    float fov = cam[9];
    int ortho = (int)cam[10];
    float orthoh = cam[11];
    V3 f = normv(sub(tgt, eye));
    V3 r = normv(cross(f, upv));
    V3 u = cross(r, f);
    float aspect = (float)W / (float)H;
    float tanh_ = tanf(fov * 0.5f * 3.14159265f / 180.0f);

    float *sx = (float *)malloc(sizeof(float) * nv);
    float *sy = (float *)malloc(sizeof(float) * nv);
    float *iz = (float *)malloc(sizeof(float) * nv);
    for (int i = 0; i < nv; i++) {
        V3 p = v3(pos[3 * i], pos[3 * i + 1], pos[3 * i + 2]);
        V3 d = sub(p, eye);
        float z = dot(d, f);
        float x = dot(d, r), y = dot(d, u);
        float nx, ny;
        if (ortho) { nx = x / (orthoh * aspect); ny = y / orthoh; iz[i] = 1.0f / (z > 1e-4f ? z : 1e-4f); }
        else { float zz = z > 1e-4f ? z : 1e-4f; nx = x / (zz * tanh_ * aspect); ny = y / (zz * tanh_); iz[i] = 1.0f / zz; }
        sx[i] = (nx * 0.5f + 0.5f) * W;
        sy[i] = (1.0f - (ny * 0.5f + 0.5f)) * H;
    }
    float *zbuf = (float *)malloc(sizeof(float) * W * H);
    int *tid = (int *)malloc(sizeof(int) * W * H);
    float *bb1 = (float *)malloc(sizeof(float) * W * H);
    float *bb2 = (float *)malloc(sizeof(float) * W * H);
    for (int i = 0; i < W * H; i++) { zbuf[i] = 1e30f; tid[i] = -1; }
    float *tlod = (float *)malloc(sizeof(float) * nt);

    for (int t = 0; t < nt; t++) {
        int i0 = tris[3 * t], i1 = tris[3 * t + 1], i2 = tris[3 * t + 2];
        V3 p0 = v3(pos[3 * i0], pos[3 * i0 + 1], pos[3 * i0 + 2]);
        V3 p1 = v3(pos[3 * i1], pos[3 * i1 + 1], pos[3 * i1 + 2]);
        V3 p2 = v3(pos[3 * i2], pos[3 * i2 + 1], pos[3 * i2 + 2]);
        V3 fn = cross(sub(p1, p0), sub(p2, p0));
        V3 vd = ortho ? mul(f, -1.0f) : sub(eye, p0);
        if (dot(fn, vd) <= 0) { tlod[t] = 0; continue; }          /* backface cull (CCW front) */
        if (iz[i0] > 1e3f || iz[i1] > 1e3f || iz[i2] > 1e3f) { tlod[t] = 0; continue; }
        float x0 = sx[i0], y0 = sy[i0], x1 = sx[i1], y1 = sy[i1], x2 = sx[i2], y2 = sy[i2];
        float area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0);
        tlod[t] = 0;
        if (fabsf(area) < 1e-12f) continue;
        /* texel/pixel footprint for lod */
        float ua = uv[2 * i1] - uv[2 * i0], va = uv[2 * i1 + 1] - uv[2 * i0 + 1];
        float ub = uv[2 * i2] - uv[2 * i0], vb = uv[2 * i2 + 1] - uv[2 * i0 + 1];
        float uvarea = fabsf(ua * vb - ub * va);
        int m = tmat[t];
        const int *ti = texinfo + (m * 3) * TI;
        float tw = ti[1] > 0 ? (float)ti[1] : 256.0f, th = ti[2] > 0 ? (float)ti[2] : 256.0f;
        float ratio = uvarea * tw * th / (fabsf(area) * 0.5f + 1e-9f);
        tlod[t] = 0.5f * log2f(ratio > 1e-9f ? ratio : 1e-9f);
        int minx = (int)floorf(fminf(x0, fminf(x1, x2))), maxx = (int)ceilf(fmaxf(x0, fmaxf(x1, x2)));
        int miny = (int)floorf(fminf(y0, fminf(y1, y2))), maxy = (int)ceilf(fmaxf(y0, fmaxf(y1, y2)));
        if (maxx < 0 || maxy < 0 || minx >= W || miny >= H) continue;
        if (minx < 0) minx = 0; if (miny < 0) miny = 0; if (maxx >= W) maxx = W - 1; if (maxy >= H) maxy = H - 1;
        float inv = 1.0f / area;
        for (int y = miny; y <= maxy; y++) for (int x = minx; x <= maxx; x++) {
            float px = x + 0.5f, py = y + 0.5f;
            float w0 = ((x1 - px) * (y2 - py) - (x2 - px) * (y1 - py)) * inv;
            float w1 = ((x2 - px) * (y0 - py) - (x0 - px) * (y2 - py)) * inv;
            float w2 = 1.0f - w0 - w1;
            const float e = -1e-5f;
            if (w0 < e || w1 < e || w2 < e) continue;
            float iw = w0 * iz[i0] + w1 * iz[i1] + w2 * iz[i2];
            float z = 1.0f / iw;
            int k = y * W + x;
            if (z < zbuf[k]) {
                zbuf[k] = z; tid[k] = t;
                bb1[k] = w1 * iz[i1] * z;   /* perspective-correct barycentrics of v1,v2 */
                bb2[k] = w2 * iz[i2] * z;
            }
        }
    }

    float gamma = opts[0];
    float exposure = opts[1];
    V3 lk = normv(v3(-0.45f, -0.60f, 0.66f));   /* key  */
    V3 lf = normv(v3(0.75f, -0.35f, 0.25f));    /* fill */
    V3 lr = normv(v3(0.20f, 0.85f, 0.45f));     /* rim  */

#pragma omp parallel for schedule(dynamic, 8)
    for (int y = 0; y < H; y++) {
        for (int x = 0; x < W; x++) {
            int k = y * W + x;
            float *o = outrgb + 3 * k;
            int t = tid[k];
            /* background: soft studio sweep */
            float vy = (float)y / H;
            float bgv = 0.86f - 0.22f * vy * vy;
            V3 col = v3(bgv, bgv, bgv * 1.02f);
            if (t >= 0) {
                int i0 = tris[3 * t], i1 = tris[3 * t + 1], i2 = tris[3 * t + 2];
                float b1 = bb1[k], b2 = bb2[k], b0 = 1.0f - b1 - b2;
                V3 P = add(add(mul(v3(pos[3 * i0], pos[3 * i0 + 1], pos[3 * i0 + 2]), b0),
                               mul(v3(pos[3 * i1], pos[3 * i1 + 1], pos[3 * i1 + 2]), b1)),
                           mul(v3(pos[3 * i2], pos[3 * i2 + 1], pos[3 * i2 + 2]), b2));
                V3 N = normv(add(add(mul(v3(nrm[3 * i0], nrm[3 * i0 + 1], nrm[3 * i0 + 2]), b0),
                                     mul(v3(nrm[3 * i1], nrm[3 * i1 + 1], nrm[3 * i1 + 2]), b1)),
                                 mul(v3(nrm[3 * i2], nrm[3 * i2 + 1], nrm[3 * i2 + 2]), b2)));
                float U = uv[2 * i0] * b0 + uv[2 * i1] * b1 + uv[2 * i2] * b2;
                float Vv = uv[2 * i0 + 1] * b0 + uv[2 * i1 + 1] * b1 + uv[2 * i2 + 1] * b2;
                int m = tmat[t];
                const int *tia = texinfo + (m * 3 + 0) * TI;
                const int *tin = texinfo + (m * 3 + 1) * TI;
                const int *tio = texinfo + (m * 3 + 2) * TI;
                float lod = tlod[t];
                float alb[3], nm[3], orm[3];
                if (tia[0] > 0) samp(tia, texdata, U, Vv, lod, alb);
                else { alb[0] = matparam[m * 8]; alb[1] = matparam[m * 8 + 1]; alb[2] = matparam[m * 8 + 2]; alb[0] = powf(alb[0], 1 / 2.2f); alb[1] = powf(alb[1], 1 / 2.2f); alb[2] = powf(alb[2], 1 / 2.2f); }
                if (tio[0] > 0) samp(tio, texdata, U, Vv, lod, orm);
                else { orm[0] = 1; orm[1] = matparam[m * 8 + 3]; orm[2] = matparam[m * 8 + 4]; }
                V3 A = v3(powf(alb[0], 2.2f), powf(alb[1], 2.2f), powf(alb[2], 2.2f));
                float ao = orm[0], rough = clampf(orm[1], 0.04f, 1.0f), metal = orm[2];
                /* tangent frame from triangle uv derivatives */
                if (tin[0] > 0) {
                    V3 p0 = v3(pos[3 * i0], pos[3 * i0 + 1], pos[3 * i0 + 2]);
                    V3 p1 = v3(pos[3 * i1], pos[3 * i1 + 1], pos[3 * i1 + 2]);
                    V3 p2 = v3(pos[3 * i2], pos[3 * i2 + 1], pos[3 * i2 + 2]);
                    V3 e1 = sub(p1, p0), e2 = sub(p2, p0);
                    float du1 = uv[2 * i1] - uv[2 * i0], dv1 = uv[2 * i1 + 1] - uv[2 * i0 + 1];
                    float du2 = uv[2 * i2] - uv[2 * i0], dv2 = uv[2 * i2 + 1] - uv[2 * i0 + 1];
                    float det = du1 * dv2 - du2 * dv1;
                    if (fabsf(det) > 1e-14f) {
                        float rd = 1.0f / det;
                        V3 Tt = mul(sub(mul(e1, dv2), mul(e2, dv1)), rd);   /* dP/du */
                        V3 Bb = mul(sub(mul(e2, du1), mul(e1, du2)), rd);   /* dP/dv */
                        Tt = normv(sub(Tt, mul(N, dot(N, Tt))));
                        Bb = normv(sub(Bb, mul(N, dot(N, Bb))));
                        float nmv[3];
                        samp(tin, texdata, U, Vv, lod, nmv);
                        /* DXT5nm style: x in alpha(stored in R by decoder), y in G */
                        float nx = nmv[0] * 2 - 1, ny = nmv[1] * 2 - 1;
                        float nz = sqrtf(fmaxf(0, 1 - nx * nx - ny * ny));
                        /* texture v grows downward => ny (up) maps to -dP/dv */
                        V3 Nn = normv(add(add(mul(Tt, nx), mul(Bb, -ny)), mul(N, nz)));
                        N = Nn;
                    }
                }
                V3 Vd = ortho ? mul(f, -1.0f) : normv(sub(eye, P));
                float nv_ = fmaxf(dot(N, Vd), 1e-3f);
                V3 F0 = v3(0.04f + (A.x - 0.04f) * metal, 0.04f + (A.y - 0.04f) * metal, 0.04f + (A.z - 0.04f) * metal);
                V3 Dc = mul(A, 1.0f - metal);
                float a = rough * rough;
                V3 lights[3] = {lk, lf, lr};
                V3 lcol[3] = {v3(3.2f, 3.1f, 2.9f), v3(0.9f, 1.0f, 1.2f), v3(1.6f, 1.6f, 1.7f)};
                V3 Lo = v3(0, 0, 0);
                for (int li = 0; li < 3; li++) {
                    V3 L = lights[li];
                    float nl = fmaxf(dot(N, L), 0);
                    V3 H_ = normv(add(L, Vd));
                    float nh = fmaxf(dot(N, H_), 0), vh = fmaxf(dot(Vd, H_), 0);
                    float Fs = powf(1 - vh, 5);
                    V3 F = v3(F0.x + (1 - F0.x) * Fs, F0.y + (1 - F0.y) * Fs, F0.z + (1 - F0.z) * Fs);
                    float D = ggx(nh, fmaxf(a, 0.045f));
                    float k_ = (rough + 1) * (rough + 1) / 8;
                    float G = (nl / (nl * (1 - k_) + k_ + 1e-6f)) * (nv_ / (nv_ * (1 - k_) + k_ + 1e-6f));
                    float spec = D * G / (4 * nl * nv_ + 1e-4f);
                    V3 diff = mul(Dc, 1.0f / 3.14159265f);
                    V3 sp = mul(F, spec);
                    Lo = add(Lo, v3((diff.x + sp.x) * lcol[li].x * nl, (diff.y + sp.y) * lcol[li].y * nl, (diff.z + sp.z) * lcol[li].z * nl));
                }
                /* ambient + env reflection */
                V3 R_ = sub(mul(N, 2 * dot(N, Vd)), Vd);
                V3 amb = env(N, 1.0f);
                V3 refl = env(R_, rough);
                float Fe = powf(1 - nv_, 5);
                float rf = 1.0f - rough * 0.6f;
                V3 Fenv = v3((F0.x + (fmaxf(rf, F0.x) - F0.x) * Fe), (F0.y + (fmaxf(rf, F0.y) - F0.y) * Fe), (F0.z + (fmaxf(rf, F0.z) - F0.z) * Fe));
                float horizon = clampf(1.0f + 0.6f * dot(R_, N), 0.0f, 1.0f);
                Lo = add(Lo, v3(Dc.x * amb.x * 0.9f * ao, Dc.y * amb.y * 0.9f * ao, Dc.z * amb.z * 0.9f * ao));
                Lo = add(Lo, v3(Fenv.x * refl.x * ao * horizon, Fenv.y * refl.y * ao * horizon, Fenv.z * refl.z * ao * horizon));
                col = Lo;
                col = mul(col, exposure);
                /* filmic-ish tone map */
                col.x = col.x / (1 + col.x * 0.55f) * 1.55f; col.y = col.y / (1 + col.y * 0.55f) * 1.55f; col.z = col.z / (1 + col.z * 0.55f) * 1.55f;
                col.x = powf(clampf(col.x, 0, 1), 1 / gamma); col.y = powf(clampf(col.y, 0, 1), 1 / gamma); col.z = powf(clampf(col.z, 0, 1), 1 / gamma);
            }
            o[0] = col.x; o[1] = col.y; o[2] = col.z;
        }
    }
    free(sx); free(sy); free(iz); free(zbuf); free(tid); free(bb1); free(bb2); free(tlod);
    return 0;
}

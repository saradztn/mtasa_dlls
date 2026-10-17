"""Royal Fortress geometry kernel: meshes, primitives, baked prelight and genuine
RenderWare DFF / COL3 export through the vendored DragonFF gtaLib (GPL-3.0+).
Project code: MIT. No rendering happens here.

Lessons carried over from Titan City 1.0.1 (real client defects):
  * every exported model gets a COL whose bounding box/sphere covers the visual mesh
    (GTA culls objects with the COL bounds; tiny bounds made models vanish);
  * no LIGHT geometry flag: lighting is baked in the prelit vertex colours;
  * coplanar overlaps are avoided by construction (offsets >= 3 cm).
"""
from __future__ import annotations
import math, sys
from pathlib import Path
import numpy as np
VENDOR = Path(__file__).parent / 'vendor' / 'DragonFF'
sys.path.insert(0, str(VENDOR))
from gtaLib import dff, col  # noqa: E402
RW_VERSION = 0x36003

# GTA:SA surface IDs used for COL (stone/wood/metal/grass/gravel/carpet...).
SURF = {'stone': 1, 'concrete': 4, 'paving': 6, 'gravel': 9, 'grass': 10, 'dirt': 19,
        'wood': 42, 'metal': 63, 'carpet': 145, 'glass': 45, 'sand': 21, 'rock': 34,
        'marble': 155, 'plaster': 4, 'water': 39}


class Mesh:
    """Unshared-vertex triangle mesh: every face owns its vertices, so per-vertex
    normals equal face normals and prelight can be baked per face."""
    def __init__(self, textures=()):
        self.textures = list(textures); self.v = []; self.uv = []; self.f = []; self.c = []

    def mat(self, name):
        if name not in self.textures:
            self.textures.append(name)
        return self.textures.index(name)

    def vert(self, p, uv=(0, 0), c=(255, 255, 255, 255)):
        self.v.append((float(p[0]), float(p[1]), float(p[2]))); self.uv.append((float(uv[0]), float(uv[1])))
        self.c.append(tuple(int(max(0, min(255, x))) for x in c)); return len(self.v) - 1

    def tri(self, a, b, c, m):
        if a != b and b != c and a != c:
            self.f.append((a, b, c, m))

    def poly(self, pts, tex, uvs=None, two_sided=False, shade=1.0):
        """Convex planar polygon, counter-clockwise seen from the front."""
        m = self.mat(tex)
        if uvs is None:
            uvs = planar_uv(pts)
        s = int(255 * shade)
        idx = [self.vert(p, t, (s, s, s, 255)) for p, t in zip(pts, uvs)]
        for k in range(1, len(idx) - 1):
            self.tri(idx[0], idx[k], idx[k + 1], m)
        if two_sided:
            idx2 = [self.vert(p, t, (s, s, s, 255)) for p, t in zip(pts, uvs)]
            for k in range(1, len(idx2) - 1):
                self.tri(idx2[0], idx2[k + 1], idx2[k], m)

    def quad(self, a, b, c, d, tex, uvs=None, two_sided=False, shade=1.0):
        self.poly([a, b, c, d], tex, uvs, two_sided, shade)

    def grid_quad(self, origin, du, dv, tex, step=2.0, uvscale=(2.0, 2.0), uv0=(0, 0), shade=1.0):
        """Subdivided rectangle origin + s*du + t*dv (s,t in [0,1]); front = du x dv.
        Subdivision gives baked light pools enough vertices. UV in world metres/scale."""
        origin = np.asarray(origin, float); du = np.asarray(du, float); dv = np.asarray(dv, float)
        lu = float(np.linalg.norm(du)); lv = float(np.linalg.norm(dv))
        if lu < 1e-4 or lv < 1e-4:
            return
        nu = max(1, int(math.ceil(lu / step))); nv = max(1, int(math.ceil(lv / step)))
        m = self.mat(tex); s = int(255 * shade); base = len(self.v)
        for j in range(nv + 1):
            for i in range(nu + 1):
                p = origin + du * (i / nu) + dv * (j / nv)
                self.vert(p, (uv0[0] + lu * i / nu / uvscale[0], uv0[1] + lv * j / nv / uvscale[1]), (s, s, s, 255))
        for j in range(nv):
            for i in range(nu):
                a = base + j * (nu + 1) + i; b = a + 1; c = a + nu + 2; d = a + nu + 1
                self.tri(a, b, c, m); self.tri(a, c, d, m)

    def box(self, lo, hi, tex, uvscale=2.0, faces='xXyYzZ', shade=1.0, tex_top=None):
        """Axis-aligned box; faces string chooses -x,+x,-y,+y,-z,+z sides."""
        x0, y0, z0 = lo; x1, y1, z1 = hi
        if x1 - x0 < 1e-4 or y1 - y0 < 1e-4 or z1 - z0 < 1e-4:
            return
        u = uvscale
        def uvq(w, h, o=(0, 0)):
            return [(o[0] / u, o[1] / u), ((o[0] + w) / u, o[1] / u), ((o[0] + w) / u, (o[1] + h) / u), (o[0] / u, (o[1] + h) / u)]
        if 'x' in faces: self.quad((x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1), tex, uvq(y1 - y0, z1 - z0, (y0, z0)), shade=shade * .9)
        if 'X' in faces: self.quad((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1), tex, uvq(y1 - y0, z1 - z0, (y0, z0)), shade=shade * .9)
        if 'y' in faces: self.quad((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1), tex, uvq(x1 - x0, z1 - z0, (x0, z0)), shade=shade * .95)
        if 'Y' in faces: self.quad((x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1), tex, uvq(x1 - x0, z1 - z0, (x0, z0)), shade=shade * .95)
        if 'z' in faces: self.quad((x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0), tex, uvq(x1 - x0, y1 - y0, (x0, y0)), shade=shade * .7)
        if 'Z' in faces: self.quad((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), tex_top or tex, uvq(x1 - x0, y1 - y0, (x0, y0)), shade=shade)

    def cyl(self, c, r, h, tex, sides=12, caps=True, r2=None, uvscale=2.0, top_tex=None, a0=0.0, a1=2 * math.pi, inside=False):
        """Frustum along +z from c (bottom centre). r2 = top radius."""
        r2 = r if r2 is None else r2; cx, cy, cz = c; m = self.mat(tex)
        full = abs(a1 - a0 - 2 * math.pi) < 1e-6
        n = sides; circ = max(r, r2) * (a1 - a0)
        for k in range(n):
            t0 = a0 + (a1 - a0) * k / n; t1 = a0 + (a1 - a0) * (k + 1) / n
            p = [(cx + r * math.cos(t0), cy + r * math.sin(t0), cz), (cx + r * math.cos(t1), cy + r * math.sin(t1), cz),
                 (cx + r2 * math.cos(t1), cy + r2 * math.sin(t1), cz + h), (cx + r2 * math.cos(t0), cy + r2 * math.sin(t0), cz + h)]
            uu0 = circ * k / n / uvscale; uu1 = circ * (k + 1) / n / uvscale
            uvs = [(uu0, 0), (uu1, 0), (uu1, h / uvscale), (uu0, h / uvscale)]
            if inside:
                p = [p[1], p[0], p[3], p[2]]; uvs = [uvs[1], uvs[0], uvs[3], uvs[2]]
            if r2 < 1e-4:
                self.poly([p[0], p[1], p[2]], tex, [uvs[0], uvs[1], ((uu0 + uu1) / 2, h / uvscale)])
            else:
                self.quad(*p, tex, uvs)
        if caps and full:
            tt = top_tex or tex
            if r2 > 1e-4:
                self.poly([(cx + r2 * math.cos(2 * math.pi * k / n), cy + r2 * math.sin(2 * math.pi * k / n), cz + h) for k in range(n)], tt)
            self.poly([(cx + r * math.cos(-2 * math.pi * k / n), cy + r * math.sin(-2 * math.pi * k / n), cz) for k in range(n)], tex, shade=.7)

    def sphere(self, c, r, tex, seg=10, rings=6, sz=1.0, uvscale=1.0):
        cx, cy, cz = c
        for j in range(rings):
            p0 = math.pi * j / rings - math.pi / 2; p1 = math.pi * (j + 1) / rings - math.pi / 2
            for k in range(seg):
                t0 = 2 * math.pi * k / seg; t1 = 2 * math.pi * (k + 1) / seg
                def P(t, p):
                    return (cx + r * math.cos(p) * math.cos(t), cy + r * math.cos(p) * math.sin(t), cz + r * sz * math.sin(p))
                pts = [P(t0, p0), P(t1, p0), P(t1, p1), P(t0, p1)]
                uvs = [(k / seg * uvscale, j / rings), ((k + 1) / seg * uvscale, j / rings), ((k + 1) / seg * uvscale, (j + 1) / rings), (k / seg * uvscale, (j + 1) / rings)]
                if j == 0: self.poly([pts[0], pts[2], pts[3]], tex, [uvs[0], uvs[2], uvs[3]])
                elif j == rings - 1: self.poly([pts[0], pts[1], pts[2]], tex, uvs[:3])
                else: self.quad(*pts, tex, uvs)

    def merge(self, other, offset=(0, 0, 0), angle=0.0, scale=1.0):
        a = math.radians(angle); co = math.cos(a); si = math.sin(a); base = len(self.v)
        for p, t, c in zip(other.v, other.uv, other.c):
            x, y, z = p[0] * scale, p[1] * scale, p[2] * scale
            self.vert((x * co - y * si + offset[0], x * si + y * co + offset[1], z + offset[2]), t, c)
        mapping = [self.mat(t) for t in other.textures]
        self.f.extend((a_ + base, b + base, c + base, mapping[m]) for a_, b, c, m in other.f)

    def bounds(self):
        v = np.asarray(self.v, float); return v.min(axis=0), v.max(axis=0)


def planar_uv(pts, scale=2.0):
    p = np.asarray(pts, float)
    n = np.cross(p[1] - p[0], p[2] - p[0]); n = n / max(1e-9, np.linalg.norm(n))
    ax = int(np.argmax(np.abs(n)))
    if ax == 2: return [(q[0] / scale, q[1] / scale) for q in p]
    if ax == 1: return [(q[0] / scale, q[2] / scale) for q in p]
    return [(q[1] / scale, q[2] / scale) for q in p]


def face_normals_per_vertex(mesh):
    v = np.asarray(mesh.v, float); n = np.zeros_like(v)
    for a, b, c, _ in mesh.f:
        fn = np.cross(v[b] - v[a], v[c] - v[a]); n[a] += fn; n[b] += fn; n[c] += fn
    ln = np.linalg.norm(n, axis=1); z = ln < 1e-12; ln[z] = 1; n /= ln[:, None]; n[z] = (0, 0, 1)
    return n


def bake(mesh, ambient, lights, sun=None, clamp=(28, 255)):
    """Bake prelit colours: ambient RGB (0..1) + point lights {pos,color,radius,power}
    with Lambert term and smooth falloff + optional directional sun. Multiplies
    the existing per-vertex shade (stored in c as 0..255 grey)."""
    if not mesh.v:
        return
    v = np.asarray(mesh.v, float); n = face_normals_per_vertex(mesh)
    shade = np.asarray(mesh.c, float)[:, 0] / 255.0
    col_ = np.tile(np.asarray(ambient, float), (len(v), 1))
    if sun is not None:
        d = np.asarray(sun['dir'], float); d /= np.linalg.norm(d)
        lam = np.clip(n @ (-d), 0, 1)[:, None]
        col_ += lam * np.asarray(sun['color'], float)[None, :]
        col_ += np.clip(n[:, 2:3], 0, 1) * np.asarray(sun.get('sky', (0, 0, 0)), float)[None, :]
    for L in lights:
        p = np.asarray(L['pos'], float); dv = p[None, :] - v; dist = np.linalg.norm(dv, axis=1) + 1e-6
        lam = np.clip((n * dv).sum(axis=1) / dist, 0, 1) * .75 + .25
        fall = np.clip(1 - dist / L['radius'], 0, 1) ** 2
        col_ += (lam * fall * L.get('power', 1.0))[:, None] * np.asarray(L['color'], float)[None, :]
    rgb = np.clip(col_ * shade[:, None] * 255, clamp[0], clamp[1])
    mesh.c = [(int(r), int(g), int(b), 255) for r, g, b in rgb]


def export_dff(mesh, path, name=None):
    vv = np.asarray(mesh.v, float); ff = np.asarray([f[:3] for f in mesh.f], int)
    area = np.linalg.norm(np.cross(vv[ff[:, 1]] - vv[ff[:, 0]], vv[ff[:, 2]] - vv[ff[:, 0]]), axis=1)
    mesh.f = [f for f, ok in zip(mesh.f, area > 1e-9) if ok]
    used = sorted({f[3] for f in mesh.f}); remap = {o: i for i, o in enumerate(used)}
    textures = [mesh.textures[i] for i in used]
    mesh.f = [(a, b, c, remap[m]) for a, b, c, m in mesh.f]; mesh.textures = textures
    assert 0 < len(mesh.v) < 65535, (path, len(mesh.v))
    assert 0 < len(mesh.f) < 65535, (path, len(mesh.f))
    model = dff.dff(); clump = dff.Clump(); model.clumps.append(clump)
    frame = dff.Frame(); frame.name = (name or Path(path).stem)[:23]
    frame.rotation_matrix = dff.Matrix(dff.Vector(1, 0, 0), dff.Vector(0, 1, 0), dff.Vector(0, 0, 1))
    frame.position = dff.Vector(0, 0, 0); clump.frame_list.append(frame)
    g = dff.Geometry(); g.export_flags["light"] = False; clump.geometry_list.append(g)
    g.vertices = [dff.Vector(*p) for p in mesh.v]
    nn = face_normals_per_vertex(mesh)
    g.normals = [dff.Vector(*p) for p in nn]
    g.uv_layers = [[dff.TexCoords(*uv) for uv in mesh.uv]]
    g.prelit_colors = [dff.RGBA(*c) for c in mesh.c]
    g.triangles = [dff.Triangle(b, a, m, c) for a, b, c, m in mesh.f]
    lo = vv.min(axis=0); hi = vv.max(axis=0); center = (lo + hi) / 2
    radius = float(np.linalg.norm(vv - center, axis=1).max())
    g.bounding_sphere = dff.Sphere(*center, radius)
    g.surface_properties = dff.GeomSurfPro(.65, 0, .7)
    for tname in mesh.textures:
        mat = dff.Material(); mat.color = dff.RGBA(255, 255, 255, 255)
        mat.surface_properties = dff.GeomSurfPro(.65, 0, .7)
        tex = dff.Texture(); tex.name = tname; tex.filters = 6; tex.uv_addressing = 0x11
        mat.textures = [tex]; g.materials.append(mat)
    atomic = dff.Atomic(); atomic.flags = 4; clump.atomic_list.append(atomic)
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    model.write_file(str(path), RW_VERSION)
    return {'vertices': len(mesh.v), 'triangles': len(mesh.f), 'bounds': [lo.tolist(), hi.tolist()],
            'sphere': [center.tolist(), radius], 'textures': list(mesh.textures)}


class Collision:
    """COL3 builder: axis-aligned boxes plus triangle faces (ramps, terrain, round parts)."""
    def __init__(self):
        self.boxes = []; self.verts = []; self.faces = []

    def box(self, lo, hi, surf='stone'):
        lo = [float(x) for x in lo]; hi = [float(x) for x in hi]
        if all(h - l > 0.01 for l, h in zip(lo, hi)):
            self.boxes.append((lo, hi, SURF.get(surf, surf) if isinstance(surf, str) else surf))

    def tri(self, a, b, c, surf='stone'):
        s = SURF.get(surf, surf) if isinstance(surf, str) else surf
        base = len(self.verts); self.verts += [tuple(map(float, a)), tuple(map(float, b)), tuple(map(float, c))]
        self.faces.append((base, base + 1, base + 2, s))

    def quad(self, a, b, c, d, surf='stone'):
        self.tri(a, b, c, surf); self.tri(a, c, d, surf)

    def mesh(self, m, surf='stone'):
        s = SURF.get(surf, surf) if isinstance(surf, str) else surf
        base = len(self.verts); self.verts += [tuple(p) for p in m.v]
        self.faces += [(a + base, b + base, c + base, s) for a, b, c, _ in m.f]

    def transformed(self, offset, angle=0.0):
        """Copy rotated about z by a multiple of 90 deg (boxes stay axis-aligned)."""
        q = int(round(angle / 90.0)) % 4; out = Collision()
        def R(p):
            x, y, z = p
            for _ in range(q): x, y = -y, x
            return (x + offset[0], y + offset[1], z + offset[2])
        for lo, hi, s in self.boxes:
            a = R(lo); b = R(hi)
            out.boxes.append(([min(a[i], b[i]) for i in range(3)], [max(a[i], b[i]) for i in range(3)], s))
        base = 0; out.verts = [R(p) for p in self.verts]; out.faces = list(self.faces)
        return out

    def merge(self, other):
        base = len(self.verts); self.verts += other.verts
        self.faces += [(a + base, b + base, c + base, s) for a, b, c, s in other.faces]
        self.boxes += other.boxes

    def empty(self):
        return not self.boxes and not self.faces


def export_col(c, path, name, visual_bounds=None):
    """COL3 with box primitives + welded mesh faces. The model bounds are the union
    of collision and visual bounds so GTA never culls the visual mesh early."""
    col.Sections.init_sections(3)
    model = col.ColModel(); model.version = 3; model.model_name = name[:21]
    pts = []
    for lo, hi, s in c.boxes:
        model.boxes.append(col.TBox(tuple(lo), tuple(hi), col.TSurface(s, 0, 0xAA, 0))); pts += [lo, hi]
    if c.faces:
        vv = np.asarray(c.verts, float)
        assert np.max(np.abs(vv)) < 255.9, (path, float(np.max(np.abs(vv))))
        q = np.rint(vv * 128).astype(np.int32)
        uniq, inv = np.unique(q, axis=0, return_inverse=True); inv = inv.reshape(-1)
        faces = []
        for a, b, cc, s in c.faces:
            a, b, cc = int(inv[a]), int(inv[b]), int(inv[cc])
            if a == b or b == cc or a == cc: continue
            if not np.any(np.cross(uniq[b] - uniq[a], uniq[cc] - uniq[a])): continue
            faces.append(col.TFace(a, b, cc, s, 0xAA))
        verts = uniq.astype(float) / 128
        model.mesh_verts = [col.TVertex(*p) for p in verts]; model.mesh_faces = faces
        pts += verts.tolist()
    for lo, hi, s in c.boxes:
        assert max(abs(x) for x in lo + hi) < 255.9, (path, 'box out of COL range')
    if visual_bounds is not None:
        pts += [list(visual_bounds[0]), list(visual_bounds[1])]
    assert pts, path
    P = np.asarray(pts, float); lo = P.min(axis=0); hi = P.max(axis=0); center = (lo + hi) / 2
    radius = float(np.linalg.norm(hi - center)) + 0.05
    model.bounds = col.TBounds(tuple(lo), tuple(hi), tuple(center), radius)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    col.coll(model).write_file(str(path))
    return {'boxes': len(model.boxes), 'faces': len(model.mesh_faces), 'bounds': [lo.tolist(), hi.tolist()], 'radius': radius}


def rot2(x, y, deg):
    a = math.radians(deg); return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)

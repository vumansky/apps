"""Street surface, granite setts, furniture, lights, leaves on the ground and in the air."""
import numpy as np
import bpy
from .mb import MB, mesh_from_arrays
from .trees import leaves_mesh

HALF_W = 13.5          # facade line
LANE = 8.6             # half width of the sett-paved carriageway
TREE_X = 9.9
LAMP_X = 8.25
Y0, Y1 = -60.0, 548.0
GEO_Y = (-16.0, 64.0)  # real stone geometry here (the camera starts low over it)


def setts_geo(get_mat, coll, rng):
    py, px = 0.112, 0.118
    ys = np.arange(GEO_Y[0], GEO_Y[1], py)
    xs = np.arange(-LANE, LANE, px)
    X, Y = np.meshgrid(xs, ys)
    X = X + (np.arange(len(ys)) % 2)[:, None] * px * 0.5 + rng.normal(size=X.shape) * 0.004
    Y = Y + rng.normal(size=Y.shape) * 0.003
    n = X.size
    cx, cy = X.ravel(), Y.ravel()
    hx = px / 2 - 0.0045 + rng.normal(size=n) * 0.002
    hy = py / 2 - 0.0045 + rng.normal(size=n) * 0.002
    zt = rng.normal(size=n) * 0.0022
    bev = 0.011
    ang = rng.normal(size=n) * 0.03
    ca, sa = np.cos(ang), np.sin(ang)
    sx = np.array([-1, 1, 1, -1.0]); sy = np.array([-1, -1, 1, 1.0])
    def ring(hx_, hy_, z):
        lx = sx[None, :] * hx_[:, None]; ly = sy[None, :] * hy_[:, None]
        x = cx[:, None] + lx * ca[:, None] - ly * sa[:, None]
        y = cy[:, None] + lx * sa[:, None] + ly * ca[:, None]
        return np.stack([x, y, z], -1)
    ztop = zt[:, None] + rng.normal(size=(n, 4)) * 0.0015
    top = ring(hx - bev, hy - bev, ztop)
    bot = ring(hx, hy, np.repeat(zt[:, None] - 0.016, 4, 1))
    V = np.concatenate([top, bot], 1).reshape(-1, 3)
    base = (np.arange(n) * 8)[:, None]
    quads = np.array([(0, 1, 2, 3), (4, 5, 1, 0), (5, 6, 2, 1), (6, 7, 3, 2), (7, 4, 0, 3)])
    F = (base[:, None, :] + quads[None, :, :]).reshape(-1, 4)
    rnd = np.repeat(rng.random(n), 8)
    ob = mesh_from_arrays('SettsGeo', V, F, get_mat, 'setts:geo', attr=rnd, coll=coll, smooth=False)
    return ob


def ground(get_mat, coll, cross_streets):
    g = MB()
    # mortar bed under the geometric setts + textured setts elsewhere
    g.quad([(-LANE, GEO_Y[0], -0.0085), (LANE, GEO_Y[0], -0.0085), (LANE, GEO_Y[1], -0.0085), (-LANE, GEO_Y[1], -0.0085)], 'mortar:')
    for a, b in ((Y0, GEO_Y[0]), (GEO_Y[1], Y1)):
        g.quad([(-LANE, a, -0.002), (LANE, a, -0.002), (LANE, b, -0.002), (-LANE, b, -0.002)], 'setts:tex')
    # sidewalks with granite kerbs; cross streets are paved with setts too
    edges = [Y0] + [v for c, w in cross_streets for v in (c - w / 2, c + w / 2)] + [Y1]
    for s in (-1, 1):
        for i in range(0, len(edges), 2):
            a, b = edges[i], edges[i + 1]
            xa, xb = sorted((s * LANE, s * 40.0))
            g.box(xa, xb, a, b, -0.3, 0.10, 'slabs:')
            ka, kb = sorted((s * LANE, s * (LANE - 0.22)))
            g.box(ka, kb, a, b, -0.3, 0.115, 'trim:grey')
        for c, w in cross_streets:
            xa, xb = sorted((s * LANE, s * 400.0))
            g.quad([(xa, c - w / 2, -0.002), (xb, c - w / 2, -0.002), (xb, c + w / 2, -0.002), (xa, c + w / 2, -0.002)], 'setts:tex')
    return g.to_object('Ground', get_mat, coll=coll)


def lamp_post(mb, x, y, rot=0.0):
    """cast-iron candelabra with two lanterns (as on Deribasivska)."""
    I = 'iron:'
    mb.set_frame((x, y, 0), (np.cos(rot), np.sin(rot), 0), (-np.sin(rot), np.cos(rot), 0))
    c = (0, 0)
    mb.cyl(c, 0.26, 0.24, 0.10, 0.22, I, n=8); mb.cyl(c, 0.2, 0.15, 0.22, 0.9, I, n=8)
    mb.cyl(c, 0.17, 0.11, 0.9, 1.05, I, n=8); mb.cyl(c, 0.075, 0.055, 1.05, 4.1, I, n=8)
    mb.cyl(c, 0.10, 0.10, 2.0, 2.08, I, n=8); mb.cyl(c, 0.09, 0.12, 3.9, 4.1, I, n=8)
    mb.box(-0.62, 0.62, -0.025, 0.025, 4.0, 4.06, I)
    for s in (-1, 1):
        # scroll brace
        pts = [(s * 0.07, 3.55), (s * 0.3, 3.7), (s * 0.5, 3.95), (s * 0.6, 4.02)]
        for (ua, za), (ub, zb) in zip(pts[:-1], pts[1:]):
            mb.prism([(ua, za), (ub, zb), (ub, zb + .03), (ua, za + .03)], -0.012, 0.012, I)
        lanternc = (s * 0.6, 0)
        mb.cyl(lanternc, 0.035, 0.05, 4.06, 4.22, I, n=6)
        mb.cyl(lanternc, 0.085, 0.16, 4.22, 4.62, 'lamp:', n=6)
        mb.cyl(lanternc, 0.19, 0.06, 4.62, 4.74, I, n=6)
        mb.cyl(lanternc, 0.03, 0.01, 4.74, 4.9, I, n=6)
        for k in range(6):
            a = 2 * np.pi * k / 6
            mb.add([(s * 0.6 + 0.085 * np.cos(a), 0.085 * np.sin(a), 4.22), (s * 0.6 + 0.16 * np.cos(a), 0.16 * np.sin(a), 4.62),
                    (s * 0.6 + 0.165 * np.cos(a + .08), 0.165 * np.sin(a + .08), 4.62), (s * 0.6 + 0.09 * np.cos(a + .08), 0.09 * np.sin(a + .08), 4.22)], [(0, 1, 2, 3)], I)
    mb.cyl(c, 0.03, 0.01, 4.1, 4.5, I, n=6)
    mb.set_frame((0, 0, 0), (1, 0, 0), (0, 1, 0))


def bench(mb, x, y, face):
    """face=+1 looks toward +x"""
    mb.set_frame((x, y, 0), (0, 1, 0), (face, 0, 0))
    W = 'paint:wood'; I = 'iron:'
    for u in (-0.85, 0.85):
        mb.box(u - .03, u + .03, -0.28, 0.28, 0.0, 0.42, I)
        mb.box(u - .03, u + .03, -0.3, -0.24, 0.42, 0.9, I)
        mb.box(u - .03, u + .03, -0.28, 0.3, 0.6, 0.64, I)
    for k in range(5):
        d = -0.2 + k * 0.105
        mb.box(-0.95, 0.95, d, d + 0.085, 0.42, 0.455, W)
    for k in range(4):
        z = 0.52 + k * 0.105
        mb.box(-0.95, 0.95, -0.29 - k * 0.012, -0.26 - k * 0.012, z, z + 0.085, W)
    mb.set_frame((0, 0, 0), (1, 0, 0), (0, 1, 0))


def flowers(mb, rng, u0, u1, d0, d1, z, key=None):
    cols = ['paint:burgundy', 'paint:gold', 'paint:linen', 'paint:terracotta', 'paint:ochre']
    n = int((u1 - u0) * (d1 - d0) * 60)
    c = key or str(rng.choice(cols))
    for i in range(n):
        u, d = rng.uniform(u0, u1), rng.uniform(d0, d1)
        r = rng.uniform(0.04, 0.075)
        zz = z + rng.uniform(0.02, 0.22)
        m = c if rng.random() < 0.6 else ('paint:green' if rng.random() < 0.6 else str(rng.choice(cols)))
        mb.dome((u, d), r, zz, r * 0.8, m, n=5, rings=2)


def terrace(mb, rng, x0, x1, y0, y1):
    """cafe summer terrace: deck, flower boxes, tables, bentwood-ish chairs, parasols."""
    W = 'paint:wood'; DW = 'paint:darkwood'
    mb.box(x0, x1, y0, y1, 0.0, 0.14, W)
    # planter boxes around the perimeter with autumn chrysanthemums
    def planter(a, b, c, d):
        mb.box(a, b, c, d, 0.14, 0.62, DW)
        mb.box(a + .04, b - .04, c + .04, d - .04, 0.6, 0.64, 'paint:black')
        flowers(mb, rng, a + .05, b - .05, c + .05, d - .05, 0.62)
    xs = x0
    for ya in np.arange(y0, y1 - 0.5, 2.4):
        planter(x0, x0 + 0.4, ya + .1, min(ya + 2.2, y1))
        if ya > y0 + 3: planter(x1 - 0.4, x1, ya + .1, min(ya + 2.2, y1))
    planter(x0 + .5, x1 - 1.8, y1 - 0.4, y1)
    # tables
    ty = np.arange(y0 + 1.6, y1 - 1.2, 2.5)
    for j, yy in enumerate(ty):
        for xx in ((x0 + 1.5, x1 - 1.5) if x1 - x0 > 4 else ((x0 + x1) / 2,)):
            c = (xx + rng.normal() * 0.08, yy + rng.normal() * 0.08)
            mb.cyl(c, 0.2, 0.03, 0.14, 0.2, 'iron:', n=8); mb.cyl(c, 0.03, 0.03, 0.2, 0.86, 'iron:', n=6)
            mb.cyl(c, 0.42, 0.42, 0.86, 0.89, 'paint:linen', n=14)
            mb.cyl(c, 0.42, 0.46, 0.62, 0.86, 'paint:linen', n=14, cap=False)
            mb.cyl((c[0] + .1, c[1] - .05), 0.035, 0.045, 0.89, 1.0, 'lamp:', n=6)       # candle glass
            mb.cyl((c[0] - .12, c[1] + .1), 0.05, 0.03, 0.89, 0.97, 'paint:terracotta', n=6)
            for k in range(rng.integers(2, 5)):
                a = 2 * np.pi * k / 4 + rng.normal() * 0.25 + 0.4
                chair(mb, c[0] + 0.72 * np.cos(a), c[1] + 0.72 * np.sin(a), a + np.pi + rng.normal() * 0.2)
        if j % 2 == 0:
            parasol(mb, (x0 + x1) / 2, yy + 1.2, closed=(rng.random() < 0.3))


def chair(mb, x, y, ang):
    mb.set_frame((x, y, 0.14), (np.cos(ang), np.sin(ang), 0), (-np.sin(ang), np.cos(ang), 0))
    D = 'paint:darkwood'
    for u in (-0.19, 0.19):
        for d in (-0.19, 0.19):
            mb.box(u - .015, u + .015, d - .015, d + .015, 0, 0.45, D)
    mb.cyl((0, 0), 0.23, 0.23, 0.45, 0.48, 'paint:wood', n=10)
    for d in (-0.19, 0.19):
        mb.box(-0.205, -0.175, d - .015, d + .015, 0.45, 0.9, D)
    mb.box(-0.205, -0.18, -0.2, 0.2, 0.82, 0.9, D); mb.box(-0.2, -0.185, -0.2, 0.2, 0.62, 0.66, D)
    mb.set_frame((0, 0, 0), (1, 0, 0), (0, 1, 0))


def parasol(mb, x, y, closed=False):
    c = (x, y)
    mb.cyl(c, 0.3, 0.3, 0.14, 0.2, 'iron:', n=8)
    mb.cyl(c, 0.025, 0.025, 0.2, 2.75, 'paint:darkwood', n=6)
    if closed:
        mb.cyl(c, 0.14, 0.03, 1.3, 2.7, 'awning:canvas', n=8)
    else:
        mb.cyl(c, 1.55, 0.04, 2.25, 2.75, 'awning:canvas', n=8, cap=False)
        mb.cyl(c, 1.55, 1.55, 2.1, 2.25, 'awning:canvas', n=8, cap=False)


def string_lights(mb, p0, p1, sag, spacing=0.38, bulb=True):
    p0 = np.array(p0, float); p1 = np.array(p1, float)
    L = np.linalg.norm(p1 - p0); n = max(4, int(L / spacing))
    f = np.linspace(0, 1, n + 1)
    pts = p0[None] + (p1 - p0)[None] * f[:, None]
    pts[:, 2] -= sag * 4 * f * (1 - f)
    mb.tube(pts, np.full(n + 1, 0.006), 'iron:', n=3)
    if bulb:
        for p in pts[1:-1]:
            o = mb.o.copy(); mb.o = np.zeros(3)
            mb.dome((p[0], p[1]), 0.028, p[2] - 0.075, 0.03, 'bulb:', n=5, rings=2)
            mb.cyl((p[0], p[1]), 0.004, 0.028, p[2] - 0.1, p[2] - 0.075, 'bulb:', n=5)
            mb.o = o


def rotunda(mb, x, y):
    """City Garden bandstand rotunda: round stylobate, 8 columns, entablature, dome."""
    mb.set_frame((x, y, 0), (1, 0, 0), (0, 1, 0))
    T = 'trim:white'; c = (0, 0)
    for k in range(4):
        mb.cyl(c, 5.0 - 0.32 * k, 5.0 - 0.32 * k, 0.16 * k, 0.16 * (k + 1), 'trim:grey', n=24)
    for k in range(8):
        a = 2 * np.pi * (k + 0.5) / 8
        cc = (3.4 * np.cos(a), 3.4 * np.sin(a))
        mb.cyl(cc, 0.3, 0.3, 0.64, 0.84, T, n=10)
        mb.cyl(cc, 0.22, 0.19, 0.84, 4.6, T, n=10)
        mb.cyl(cc, 0.2, 0.3, 4.6, 4.85, T, n=10)
        a2 = 2 * np.pi * (k + 1.5) / 8
        # low iron railing between columns (skip the entrance bay)
        if k not in (5,):
            p0 = np.array([x + 3.4 * np.cos(a), y + 3.4 * np.sin(a), 1.5]); p1 = np.array([x + 3.4 * np.cos(a2), y + 3.4 * np.sin(a2), 1.5])
            mb.tube([p0, p1], [0.025, 0.025], 'iron:', n=4)
            for f in np.linspace(0.08, 0.92, 9):
                q = p0 + (p1 - p0) * f
                mb.tube([q - (0, 0, 0.86), q], [0.01, 0.01], 'iron:', n=3)
    mb.cyl(c, 3.75, 3.75, 4.85, 5.4, T, n=24); mb.cyl(c, 3.95, 3.95, 5.4, 5.55, T, n=24)
    mb.cyl(c, 3.3, 3.3, 4.84, 4.86, 'stucco:ivory', n=24)
    mb.dome(c, 3.85, 5.55, 2.3, 'roof:green', n=24, rings=8, power=0.9)
    mb.cyl(c, 0.3, 0.2, 7.8, 8.3, T, n=8); mb.cyl(c, 0.2, 0.01, 8.3, 9.3, 'roof:green', n=8)
    mb.set_frame((0, 0, 0), (1, 0, 0), (0, 1, 0))


def ground_leaves(get_mat, coll, rng, n=42000, extra=None):
    y = rng.uniform(-22, 190, n)
    side = rng.choice([-1, 1], n)
    k = rng.random(n)
    x = np.where(k < 0.45, side * (TREE_X + rng.normal(size=n) * 1.6),
                 np.where(k < 0.6, side * (LANE - np.abs(rng.normal(size=n)) * 0.5), rng.uniform(-HALF_W, HALF_W, n)))
    x = np.clip(x, -HALF_W + 0.1, HALF_W - 0.1)
    # windrows: leaves drift into clumps
    cl = rng.random(n) < 0.35
    cx = rng.uniform(-LANE, LANE, 160); cy = rng.uniform(-22, 120, 160)
    ci = rng.integers(0, 160, n)
    x = np.where(cl, cx[ci] + rng.normal(size=n) * 0.55, x); y = np.where(cl, cy[ci] + rng.normal(size=n) * 0.9, y)
    if extra is not None:
        x = np.concatenate([x, extra[:, 0]]); y = np.concatenate([y, extra[:, 1]]); n = len(x)
    z = np.where(np.abs(x) > LANE, 0.118, 0.012) + rng.random(n) * 0.012
    P = np.c_[x, y, z]
    Nrm = rng.normal(size=(n, 3)) * np.array([0.16, 0.16, 0.0]) + np.array([0, 0, 1.0])
    Nrm /= np.linalg.norm(Nrm, axis=1, keepdims=True)
    size = rng.uniform(0.13, 0.21, n)
    V, F = leaves_mesh(P, Nrm, size, rng)
    return mesh_from_arrays('GroundLeaves', V, F, get_mat, 'leaf:ground', attr=np.repeat(rng.random(n), 13), coll=coll)


class FallingLeaves:
    """airborne leaves; vertices rewritten analytically every frame (deterministic)."""
    def __init__(self, get_mat=None, coll=None, n=1500, seed=5, obj=None):
        rng = np.random.default_rng(seed)
        self.n = n
        self.x0 = rng.uniform(-11.5, 11.5, n); self.y0 = rng.uniform(-12, 200, n)
        # more near the camera's opening metres
        k = n // 6
        self.x0[:k] = rng.uniform(-3.5, 4.5, k); self.y0[:k] = rng.uniform(-2, 30, k)
        self.zph = rng.uniform(0, 1, n)
        self.vz = rng.uniform(0.55, 1.15, n)
        self.top = rng.uniform(9, 15, n)
        self.sw_a = rng.uniform(0.25, 0.8, n); self.sw_f = rng.uniform(0.25, 0.6, n); self.sw_p = rng.uniform(0, 6.28, (n, 2))
        self.spin = rng.uniform(0.8, 3.0, n) * rng.choice([-1, 1], n); self.sp_p = rng.uniform(0, 6.28, n)
        self.tum = rng.uniform(0.6, 2.2, n)
        self.size = rng.uniform(0.2, 0.3, n)
        self.rnd = rng.random(n)
        self.wind = np.array([0.35, -0.5])
        from .trees import LEAF_P, LEAF_T
        self.L = LEAF_P - np.array([0, 0.4, 0]); self.T = LEAF_T
        if obj is None:
            V = self.verts(0.0)
            F = (self.T[None] + (np.arange(n) * 13)[:, None, None]).reshape(-1, 3)
            obj = mesh_from_arrays('FallingLeaves', V, F, get_mat, 'leaf:fall', attr=np.repeat(self.rnd, 13), coll=coll)
        self.obj = obj

    def verts(self, t, cam_pos=None):
        period = self.top / self.vz
        ph = (self.zph + t / period) % 1.0
        z = self.top * (1 - ph) + 0.03
        tt = ph * period
        x = self.x0 + self.wind[0] * tt + self.sw_a * np.sin(self.sw_f * 6.28 * tt + self.sw_p[:, 0])
        y = self.y0 + self.wind[1] * tt + self.sw_a * 0.7 * np.sin(self.sw_f * 5.1 * tt + self.sw_p[:, 1])
        a = self.spin * tt + self.sp_p
        b = 0.9 * np.sin(self.tum * tt + self.sp_p * 2)
        # leaf frame: normal tilts back and forth, in-plane rotation spins
        nrm = np.stack([np.sin(b) * np.cos(a * 0.37), np.sin(b) * np.sin(a * 0.37), np.cos(b)], -1)
        r = np.stack([np.cos(a), np.sin(a), np.zeros_like(a)], -1)
        u = np.cross(nrm, r); u /= np.linalg.norm(u, axis=1, keepdims=True) + 1e-9
        v = np.cross(nrm, u)
        P = np.stack([x, y, z], -1)
        L = self.L
        size = self.size
        if cam_pos is not None:   # leaves about to hit the lens shrink away instead of flashing across the frame
            dist = np.linalg.norm(P - np.asarray(cam_pos)[None], axis=1)
            size = size * np.clip((dist - 0.9) / 1.3, 0.0, 1.0)
        V = P[:, None, :] + size[:, None, None] * (L[None, :, 0:1] * u[:, None] + L[None, :, 1:2] * v[:, None] + L[None, :, 2:3] * nrm[:, None])
        return V.reshape(-1, 3)

    def update(self, t, cam_pos=None):
        me = self.obj.data
        me.vertices.foreach_set("co", self.verts(t, cam_pos).astype(np.float32).ravel())
        me.update()

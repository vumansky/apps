"""Deribasivska building rows + the surrounding city: blocks, courtyards, Opera, slope, port, sea."""
import numpy as np
import bpy, bmesh
from .mb import MB, mesh_from_arrays
from . import facade
from .street import HALF_W

CROSS = [(-75.0, 18.0), (108.0, 18.0), (250.0, 18.0), (395.0, 18.0)]   # (centre y, width)
GARDEN = (22.0, 99.0)      # City Garden (Miskyi Sad) opening on the left side
SEA_Z = -40.0
YEND = 540.0            # the plateau ends here; a park slope drops to the port
WCOL = ['cream', 'butter', 'sand', 'ochre', 'limestone', 'pistachio', 'rose', 'ivory', 'grey', 'salmon']
ROOFC = ['red', 'zinc', 'brown', 'green', 'zinc', 'brown']


def segments():
    ys = [-48.0] + [v for c, w in CROSS[1:] for v in (c - w / 2, c + w / 2)] + [YEND]
    return [(ys[i], ys[i + 1]) for i in range(0, len(ys), 2)]


def street_rows(get_mat, coll, rng):
    """detailed facades on both sides. returns list of (side, y0, y1, H) for later use."""
    info = []
    n = 0
    for side in (-1, 1):
        for (a, b) in segments():
            spans = [(a, b)]
            if side == -1 and a < GARDEN[0] < b:
                spans = [(a, GARDEN[0])]
            for (s0, s1) in spans:
                y = s0
                fixed = [24.0, 26.0, 32.0, 32.0, 33.0] if (side == 1 and s0 < 0) else []
                while y < s1 - 1:
                    W = float(rng.uniform(17, 30))
                    if s1 - (y + W) < 15: W = s1 - y
                    if fixed: W = fixed.pop(0)
                    first, last = (y == s0), (y + W >= s1 - 0.01)
                    st = facade.make_style(rng)
                    far = y > 300
                    hero = (side == 1 and abs(y - 34.0) < 0.5)
                    if hero:   # Bolshaya Moskovskaya-like: butter yellow, white ornament, zinc mansard
                        st = facade.make_style(rng, floors=4, body='butter')
                        st.update(body='stucco:hero', rustic='rustic:hero', trim='trim:white', roof='roof:zinc', mansard=True, balcony='alt', bal2=True, order='pilasters',
                                  pil_step=1, parapet='none', attic='attic', hoods=['seg', 'tri', 'flat'], arch_floor=3, modillions=True)
                    elif rng.random() < 0.3:
                        st['mansard'] = True; st['parapet'] = 'none'
                    corner_lo, corner_hi = first and s0 > -40, last and s1 < YEND - 5
                    if side == -1 and last and abs(s1 - GARDEN[0]) < 0.1: corner_hi = True
                    if (corner_lo or corner_hi) and rng.random() < 0.6:
                        st['turret'] = ([0.0] if corner_lo else []) + ([W] if corner_hi else [])
                    mb = MB()
                    depth = float(rng.uniform(13, 16))
                    if side == 1:   # right side: facade faces -x, u runs +y
                        H, zp = facade.building(mb, rng, (HALF_W, y, 0), (0, 1, 0), (-1, 0, 0), W, depth, st,
                                                side_left=corner_lo, side_right=corner_hi, back=not far)
                    else:           # left side: facade faces +x, u runs -y
                        H, zp = facade.building(mb, rng, (-HALF_W, y + W, 0), (0, -1, 0), (1, 0, 0), W, depth, st,
                                                side_left=corner_hi, side_right=corner_lo, back=not far)
                    mb.to_object('Bld_%02d' % n, get_mat, coll=coll)
                    info.append((side, y, y + W, zp)); n += 1
                    y += W
    return info


def simple_building(mb, rng, x0, x1, y0, y1, H=None):
    H = H or float(rng.choice([9.5, 13.5, 13.5, 17.5, 17.5, 21]))
    m = 'wintex:' + str(rng.choice(WCOL))
    mb.box(x0, x1, y0, y1, -1.0, H, m)
    mb.box(x0 - .4, x1 + .4, y0 - .4, y1 + .4, H, H + 0.35, 'trim:white')
    rise = float(rng.uniform(2.0, 3.5))
    ins = min(rise * 1.3, (x1 - x0) / 2 - 0.3, (y1 - y0) / 2 - 0.3)
    mb.frustum(x0 - .3, x1 + .3, y0 - .3, y1 + .3, H + 0.35, H + 0.35 + rise, ins, 'roof:' + str(rng.choice(ROOFC)))
    for k in range(int(rng.integers(2, 6))):
        if x1 - x0 < 6 or y1 - y0 < 6: break
        cx, cy = rng.uniform(x0 + 2, x1 - 2), rng.uniform(y0 + 2, y1 - 2)
        mb.box(cx, cx + 0.9, cy, cy + 0.6, H, H + rise + rng.uniform(0.8, 1.6), 'stucco:terracotta')
    for k in range(int(rng.integers(0, 4))):   # dormers / skylights break up the roof planes
        if x1 - x0 < 6 or y1 - y0 < 6: break
        cx, cy = rng.uniform(x0 + 1.5, x1 - 2.5), rng.uniform(y0 + 1.5, y1 - 2.5)
        mb.box(cx, cx + 1.3, cy, cy + 1.3, H + 0.3, H + 1.7, m)
        mb.frustum(cx - .15, cx + 1.45, cy - .15, cy + 1.45, H + 1.7, H + 2.2, 0.6, 'roof:zinc')
    return H


def block(mb, rng, x0, x1, y0, y1, skip_side=None, blobs=None):
    """perimeter block of simple buildings around a leafy courtyard."""
    d = 13.0
    def row(ax, a, b, fixed0, fixed1):
        p = a
        while p < b - 2:
            w = float(rng.uniform(16, 32))
            if b - (p + w) < 12: w = b - p
            if ax == 'y': simple_building(mb, rng, fixed0, fixed1, p, p + w)
            else: simple_building(mb, rng, p, p + w, fixed0, fixed1)
            p += w
    if skip_side != 'x0': row('y', y0, y1, x0, x0 + d)
    if skip_side != 'x1': row('y', y0, y1, x1 - d, x1)
    row('x', x0 + d, x1 - d, y0, y0 + d)
    row('x', x0 + d, x1 - d, y1 - d, y1)
    # courtyard wings + trees
    for k in range(int(rng.integers(1, 4))):
        if x1 - x0 < 2 * d + 30 or y1 - y0 < 2 * d + 40: break
        cx = rng.uniform(x0 + d + 4, x1 - d - 14); cy = rng.uniform(y0 + d + 4, y1 - d - 20)
        if cx > x0 + d and cy > y0 + d:
            simple_building(mb, rng, cx, cx + 10, cy, cy + rng.uniform(12, 30), H=float(rng.choice([6.0, 9.5, 13.5])))
    if blobs is not None:
        for k in range(int(max(0, x1 - x0 - 2 * d - 4) * max(0, y1 - y0 - 2 * d - 4) / 300)):
            blobs.append((rng.uniform(x0 + d + 2, x1 - d - 2), rng.uniform(y0 + d + 2, y1 - d - 2), rng.uniform(7, 13), rng.uniform(4.5, 8)))


def blobs_mesh(get_mat, coll, rng, blobs, name='CityTrees'):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    bV = np.array([v.co[:] for v in bm.verts]); bF = np.array([[v.index for v in f.verts] for f in bm.faces])
    bm.free()
    Vs, Fs = [], []
    for i, (x, y, zc, r) in enumerate(blobs):
        d = 1 + 0.28 * np.sin(bV @ rng.normal(size=3) * 2.5 + rng.uniform(0, 6)) + 0.12 * rng.normal(size=len(bV))
        V = bV * d[:, None] * np.array([r, r, r * 0.8]) + np.array([x, y, zc])
        Vs.append(V); Fs.append(bF + i * len(bV))
    return mesh_from_arrays(name, np.concatenate(Vs), np.concatenate(Fs), get_mat, 'blob:', coll=coll, smooth=True)


def city(get_mat, coll, rng):
    mb = MB(); blobs = []
    ys = [-260.0] + [v for c, w in CROSS for v in (c - w / 2, c + w / 2)] + [YEND + 5]
    yseg = [(ys[i], ys[i + 1]) for i in range(0, len(ys), 2)]
    xs_r = [HALF_W, 118.5, 136.5, 250, 268, 380, 398, 520, 538, 660]
    xs_l = [-HALF_W, -118.5, -136.5, -250, -268, -372]
    for (a, b) in yseg:
        for i in range(0, len(xs_r), 2):
            x0, x1 = xs_r[i], xs_r[i + 1]
            if i == 0 and a > -100:
                block(mb, rng, x0 + 14.5, x1, a, b, skip_side='x0', blobs=blobs)
            else:
                block(mb, rng, x0, x1, a, b, blobs=blobs)
        for i in range(0, len(xs_l), 2):
            x1, x0 = xs_l[i], xs_l[i + 1]
            if i == 0 and a < GARDEN[0] < b:
                # City Garden: open park, only the far (north) edge is built
                p_ = GARDEN[0]
                while p_ < b - 2:
                    w_ = min(float(rng.uniform(18, 30)), b - p_)
                    simple_building(mb, rng, x0, x0 + 14, p_, p_ + w_); p_ += w_
                block(mb, rng, x0, x1 - 14.5, a, GARDEN[0] - 1, skip_side='x1', blobs=blobs)
                continue
            if i == 0 and a > -100:
                block(mb, rng, x0, x1 - 14.5, a, b, skip_side='x1', blobs=blobs)
            else:
                block(mb, rng, x0, x1, a, b, blobs=blobs)
    # street trees on the other streets (rows of canopies)
    for c, w in CROSS:
        for s in (-1, 1):
            for x in np.arange(-365, 655, 9.5):
                if abs(x) < 34: continue
                blobs.append((x + rng.normal(), c + s * (w / 2 - 3.2), rng.uniform(8, 11), rng.uniform(3.6, 5.2)))
    for xs in (xs_r[1:-1], xs_l[1:-1]):
        for i in range(0, len(xs) - 1, 2):
            xc = (xs[i] + xs[i + 1]) / 2; hw = abs(xs[i + 1] - xs[i]) / 2
            for s in (-1, 1):
                for y in np.arange(-250, YEND, 9.5):
                    if any(abs(y - c) < w / 2 + 2 for c, w in CROSS): continue
                    blobs.append((xc + s * (hw - 3.2), y + rng.normal(), rng.uniform(8, 11), rng.uniform(3.6, 5.2)))
            mb.quad([(xc - hw, -260, -0.02), (xc + hw, -260, -0.02), (xc + hw, YEND + 8, -0.02), (xc - hw, YEND + 8, -0.02)], 'setts:tex')
    # far Deribasivska trees beyond the detailed ones are real trees; park slope down to the port
    for k in range(260):
        yy = rng.uniform(YEND + 8, YEND + 62)
        blobs.append((rng.uniform(-430, 700), yy, -(yy - YEND - 8) * 0.68 + rng.uniform(1, 5), rng.uniform(6, 10)))
        blobs.append((rng.uniform(-430, -380), rng.uniform(-250, 700), rng.uniform(-28, -2), rng.uniform(6, 10)))
    # land mass with slope
    mb.set_frame((0, 0, 0), (1, 0, 0), (0, 1, 0))
    P = [(-470, -700, SEA_Z - 2), (1800, -700, SEA_Z - 2), (1800, YEND + 70, SEA_Z - 2), (-470, YEND + 70, SEA_Z - 2),
         (-385, -700, -0.3), (1800, -700, -0.3), (1800, YEND + 8, -0.3), (-385, YEND + 8, -0.3)]
    from .mb import BOX_F
    mb.add(P, BOX_F, 'paint:green')
    # port apron, moles, warehouses
    PY = YEND + 70
    mb.box(-900, 1500, PY, PY + 60, SEA_Z - 3, SEA_Z + 1.8, 'slabs:')
    mb.box(-560, -470, -500, PY + 60, SEA_Z - 3, SEA_Z + 1.8, 'slabs:')
    for x in (-250, 60, 380, 700):
        L = float(rng.uniform(180, 320))
        mb.box(x, x + 55, PY + 60, PY + 60 + L, SEA_Z - 3, SEA_Z + 1.8, 'slabs:')
        for k in range(int(L / 70)):
            simple_building(mb, rng, x + 10, x + 45, PY + 75 + k * 70, PY + 75 + k * 70 + 50, H=SEA_Z + 1.8 + 9)
    # long breakwater + Vorontsov lighthouse
    mb.box(-640, -628, PY + 60, PY + 760, SEA_Z - 3, SEA_Z + 2.5, 'trim:grey')
    mb.cyl((-634, PY + 760), 3.0, 2.0, SEA_Z + 2.5, SEA_Z + 24, 'trim:white', n=12)
    mb.cyl((-634, PY + 760), 2.4, 2.4, SEA_Z + 24, SEA_Z + 27, 'lamp:', n=10)
    mb.cyl((-634, PY + 760), 2.8, 0.2, SEA_Z + 27, SEA_Z + 30, 'roof:red', n=10)
    # gantry cranes
    for (x, y) in [(-230, PY + 270), (-215, PY + 140), (95, PY + 190), (110, PY + 320), (405, PY + 160), (420, PY + 300), (735, PY + 220), (-520, 600), (-520, 480), (-525, 330)]:
        crane(mb, x, y, SEA_Z + 1.8, rng)
    # ships
    for (x, y, L, ang) in [(-120, PY + 510, 120, 0.3), (230, PY + 860, 170, -1.2), (560, PY + 410, 90, 1.3), (-380, PY + 1400, 200, 1.5), (900, PY + 1900, 220, 1.4)]:
        ship(mb, x, y, L, ang)
    mb.set_frame((0, 0, 0), (1, 0, 0), (0, 1, 0))
    opera(mb, -165.0, 330.0)
    ob = mb.to_object('City', get_mat, coll=coll)
    from . import trees
    fars = [trees.gen_far_tree(np.random.default_rng(500 + i), 'FarTree%d' % i, get_mat, coll) for i in range(4)]
    for fo in fars:
        fo.location = (0, 0, -200); fo.hide_render = True
    for i, (x, y, zc, r) in enumerate(blobs):
        src = fars[i % 4]
        o = bpy.data.objects.new('F_%d' % i, src.data); coll.objects.link(o)
        o.location = (x, y, zc); o.scale = (r * 1.15, r * 1.15, r); o.rotation_euler = (0, 0, float(rng.uniform(0, 6.28)))
    print('far trees', len(blobs), flush=True)
    bo = None
    # sea
    s = MB()
    R = 60000
    s.quad([(-R, -3000, SEA_Z), (R, -3000, SEA_Z), (R, R, SEA_Z), (-R, R, SEA_Z)], 'water:')
    s.to_object('Sea', get_mat, coll=coll)
    return ob, bo


def crane(mb, x, y, z, rng):
    I = 'paint:grey' if rng.random() < 0.5 else 'paint:terracotta'
    mb.set_frame((x, y, z), (1, 0, 0), (0, 1, 0))
    for u in (-5, 5):
        for d in (-5, 5):
            mb.box(u - .5, u + .5, d - .5, d + .5, 0, 26, I)
    mb.box(-6, 6, -6, 6, 26, 28, I)
    mb.box(-2, 2, -2, 2, 28, 40, I)
    a = rng.uniform(0, 6.28)
    p0 = np.array([x, y, z + 38.0]); p1 = p0 + np.array([np.cos(a) * 34, np.sin(a) * 34, 22.0])
    mb.tube([p0, p1], [0.9, 0.5], I, n=4)
    mb.tube([p0 + (0, 0, 2), p0 - np.array([np.cos(a) * 9, np.sin(a) * 9, -4.0])], [0.8, 0.8], I, n=4)
    mb.set_frame((0, 0, 0), (1, 0, 0), (0, 1, 0))


def ship(mb, x, y, L, ang):
    mb.set_frame((x, y, SEA_Z), (np.cos(ang), np.sin(ang), 0), (-np.sin(ang), np.cos(ang), 0))
    B = L * 0.14
    hull = [(-L / 2, -B / 2), (L * 0.32, -B / 2), (L / 2, 0), (L * 0.32, B / 2), (-L / 2, B / 2)]
    P = [(u, d, -1.0) for u, d in hull] + [(u * 1.02, d * 1.05, 7.0) for u, d in hull]
    mb.add(P, [(0, 1, 2, 3, 4), (9, 8, 7, 6, 5)] + [(i, (i + 1) % 5, 5 + (i + 1) % 5, 5 + i) for i in range(5)], 'paint:navy')
    mb.box(-L * 0.42, -L * 0.2, -B * 0.4, B * 0.4, 7, 19, 'paint:linen')
    mb.box(-L * 0.36, -L * 0.28, -B * 0.15, B * 0.15, 19, 25, 'paint:terracotta')
    mb.set_frame((0, 0, 0), (1, 0, 0), (0, 1, 0))


def opera(mb, x, y):
    """Odesa Opera and Ballet Theatre, simplified: horseshoe auditorium drum, dome, two-tier portico, stage house."""
    mb.set_frame((x, y, 0), (1, 0, 0), (0, 1, 0))
    T = 'trim:white'; B = 'stucco:cream'
    c = (0, 0)
    mb.cyl(c, 30, 30, 0, 9, 'wintex:cream', n=40); mb.cyl(c, 30.6, 30.6, 9, 9.8, T, n=40)
    mb.cyl(c, 27, 27, 9.8, 17, 'wintex:cream', n=40); mb.cyl(c, 27.6, 27.6, 17, 17.8, T, n=40)
    mb.cyl(c, 22, 22, 17.8, 23, B, n=40); mb.cyl(c, 22.6, 22.6, 23, 23.6, T, n=40)
    mb.dome(c, 22.4, 23.6, 9.0, 'roof:zinc', n=40, rings=8, power=0.8)
    mb.cyl(c, 2.2, 1.6, 32.2, 35.5, T, n=10); mb.dome(c, 1.9, 35.5, 2.2, 'roof:zinc', n=10, rings=4)
    for k in range(20):
        a = 2 * np.pi * k / 20
        pu, pd = 30.2 * np.cos(a), 30.2 * np.sin(a)
        mb.box(pu - .7, pu + .7, pd - .7, pd + .7, 0, 9, T)
        pu, pd = 27.2 * np.cos(a), 27.2 * np.sin(a)
        mb.box(pu - .6, pu + .6, pd - .6, pd + .6, 9.8, 17, T)
    # portico toward -y (facing the street side) and stage house behind
    mb.box(-11, 11, -39, -26, 0, 20, B)
    mb.box(-12, 12, -40, -26, 20, 21.2, T)
    mb.prism([(-12, 21.2), (12, 21.2), (0, 26.5)], -40, -26, T)
    for u in (-9, -5.5, -2, 2, 5.5, 9):
        mb.cyl((u, -40), 0.8, 0.7, 0.5, 9.5, T, n=8); mb.cyl((u, -40), 0.7, 0.6, 10.5, 19.5, T, n=8)
    mb.box(-12, 12, -41, -26, 9.5, 10.5, T)
    mb.box(-21, 21, 20, 46, 0, 27, 'wintex:cream'); mb.box(-21.6, 21.6, 19.4, 46.6, 27, 28, T)
    mb.frustum(-21.6, 21.6, 19.4, 46.6, 28, 33, 9, 'roof:zinc')
    mb.set_frame((0, 0, 0), (1, 0, 0), (0, 1, 0))

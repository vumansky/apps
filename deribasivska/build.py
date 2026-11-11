"""Build the whole Deribasivska scene procedurally and save it as a .blend."""
import sys, os, time, math
import numpy as np
import bpy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dz import mb as M, mats, facade, world, trees, street, city, cam

OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else os.path.join(HERE, 'out', 'scene.blend')
QUICK = '--quick' in sys.argv


def main():
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    world.setup_world(sc); world.setup_render(sc)
    G = mats.get_mat
    def coll(name):
        c = bpy.data.collections.new(name); sc.collection.children.link(c); return c
    rng = np.random.default_rng(1794)   # year Odesa was founded

    # ---- ground
    c_g = coll('Ground')
    street.ground(G, c_g, city.CROSS)
    street.setts_geo(G, c_g, np.random.default_rng(3))
    print('ground', round(time.time() - t0, 1), flush=True)

    # ---- facades
    c_b = coll('Buildings')
    info = city.street_rows(G, c_b, rng)
    print('facades', len(info), round(time.time() - t0, 1), flush=True)

    # ---- trees: 5 plane-tree variants, instanced down both sides
    c_t = coll('Trees')
    variants = [trees.gen_tree(np.random.default_rng(100 + i), 'Plane%d' % i, G, c_t, n_leaves=9500, scale=[1.0, 1.08, 0.95, 1.12, 1.0][i]) for i in range(5)]
    for w, l in variants:
        w.location = l.location = (0, 0, -100)   # originals hidden far below
        w.hide_render = l.hide_render = True
    trng = np.random.default_rng(42)
    tree_pos = []
    def plant(x, y, s=None, zr=None):
        k = int(trng.integers(0, 5)); w, l = variants[k]
        s = s or float(trng.uniform(0.88, 1.12)); rz = trng.uniform(0, 6.28) if zr is None else zr
        for src in (w, l):
            o = bpy.data.objects.new('T_' + src.name, src.data); c_t.objects.link(o)
            o.location = (x, y, 0.0 if abs(x) < street.LANE else 0.1); o.rotation_euler = (0, 0, rz); o.scale = (s, s, s * float(trng.uniform(0.95, 1.1)))
        tree_pos.append((x, y))
    for side in (-1, 1):
        for y in np.arange(-44, 536, 8.2):
            if any(abs(y - c) < w / 2 + 1.5 for c, w in city.CROSS): continue
            if side == 1 and 40 < y < 62: continue   # gap in the trees: the camera turns to a grand facade here
            plant(side * (street.TREE_X + trng.normal() * 0.25), y + trng.normal() * 0.5)
    # cross-street trees close to Deribasivska
    for c, w in city.CROSS[1:]:
        for s in (-1, 1):
            for x in (18, 27, 36, 46):
                for sx in (-1, 1):
                    plant(sx * x, c + s * (w / 2 - 3.0))
    # City Garden trees
    gx0, gx1 = -80.0, -street.HALF_W - 3
    for k in range(34):
        for _ in range(20):
            x, y = trng.uniform(gx0, gx1), trng.uniform(city.GARDEN[0] + 3, city.GARDEN[1] - 3)
            if math.hypot(x + 36, y - 60) > 9.5 and all(math.hypot(x - a, y - b) > 6.5 for a, b in tree_pos):
                plant(x, y, s=float(trng.uniform(0.9, 1.3))); break
    print('trees', len(tree_pos), round(time.time() - t0, 1), flush=True)

    # ---- street furniture
    c_f = coll('Furniture')
    f = M.MB()
    lamps = []
    for side in (-1, 1):
        for y in np.arange(-40, 536, 16.4):
            if any(abs(y - c) < w / 2 + 1 for c, w in city.CROSS): continue
            yy = y + (4.1 if side > 0 else 0)
            street.lamp_post(f, side * street.LAMP_X, yy, rot=math.pi / 2)
            lamps.append((side * street.LAMP_X, yy))
    # tree grates (round cast iron) and benches
    for (x, y) in tree_pos:
        if abs(abs(x) - street.TREE_X) < 1.5 and -44 <= y <= 540:
            z = 0.1
            f.cyl((x, y), 0.95, 0.95, z, z + 0.02, 'iron:', n=14)
            f.cyl((x, y), 0.5, 0.5, z + 0.02, z + 0.025, 'mortar:', n=10)
    for side in (-1, 1):
        for y in np.arange(-30, 300, 16.4):
            if any(abs(y - c) < w / 2 + 3 for c, w in city.CROSS): continue
            if side == 1 and 6 < y < 32: continue
            street.bench(f, side * (street.LANE - 0.9), y + 8 + (4.1 if side > 0 else 0), -side)
    # festive garlands: zig-zag across the lane between lamp posts + a few longitudinal runs
    L = sorted([l for l in lamps if l[0] < 0 and -45 < l[1] < 235], key=lambda p: p[1])
    R = sorted([l for l in lamps if l[0] > 0 and -45 < l[1] < 235], key=lambda p: p[1])
    path = np.array([cam.state(tt)['pos'] for tt in np.linspace(0, cam.DUR, 600)])
    def garland(p0, p1):
        p0 = np.array(p0); p1 = np.array(p1); fr = np.linspace(0, 1, 60)
        pts = p0[None] + (p1 - p0)[None] * fr[:, None]; pts[:, 2] -= 0.9 * 4 * fr * (1 - fr)
        dmin = np.min(np.linalg.norm(pts[:, None, :] - path[None], axis=2))
        if dmin < 1.1:
            print('garland skipped (%.2f m from the lens)' % dmin); return
        street.string_lights(f, p0, p1, 0.9)
    for i in range(min(len(L), len(R))):
        garland((L[i][0], L[i][1], 4.95), (R[i][0], R[i][1], 4.95))
        if i + 1 < len(L):
            garland((R[i][0], R[i][1], 4.95), (L[i + 1][0], L[i + 1][1], 4.95))
    # cafe terraces
    frng = np.random.default_rng(77)
    street.terrace(f, frng, 3.6, 8.0, 8.0, 30.0)
    street.terrace(f, frng, -8.0, -4.6, 104.0 - 60, 104.0 - 44)
    street.terrace(f, frng, 4.2, 8.0, 126.0, 146.0)
    # big planters with chrysanthemums along the lane edge
    for side in (-1, 1):
        for y in np.arange(-36, 240, 16.4):
            if any(abs(y - c) < w / 2 + 2 for c, w in city.CROSS): continue
            if side == 1 and (4 < y < 34 or 122 < y < 150): continue
            x = side * (street.LANE - 1.0); yy = y + 2.5
            f.cyl((x, yy), 0.42, 0.55, 0.0, 0.55, 'trim:grey', n=10)
            street.flowers(f, frng, x - .38, x + .38, yy - .38, yy + .38, 0.5)
    street.rotunda(f, -36.0, 60.0)
    # garden: lawn + path + low fence
    f.set_frame((0, 0, 0), (1, 0, 0), (0, 1, 0))
    f.box(-110, -street.HALF_W - 0.3, city.GARDEN[0], city.GARDEN[1], 0.1, 0.16, 'paint:green')
    f.box(-36 - 7, -36 + 7, 60 - 7, 60 + 7, 0.1, 0.18, 'slabs:')
    f.box(-36, -street.HALF_W, 58.4, 61.6, 0.1, 0.18, 'slabs:')
    f.to_object('Furniture', G, coll=c_f)
    print('furniture', round(time.time() - t0, 1), flush=True)

    # ---- leaves on the ground and in the air
    c_l = coll('Leaves')
    hero = np.c_[np.random.default_rng(9).normal(1.6, 1.6, 650), np.random.default_rng(10).uniform(-5, 10, 650)]
    street.ground_leaves(G, c_l, np.random.default_rng(8), extra=hero)
    street.FallingLeaves(G, c_l)

    # ---- the rest of the city
    if not QUICK:
        c_c = coll('City')
        city.city(G, c_c, np.random.default_rng(2024))
        print('city', round(time.time() - t0, 1), flush=True)

    # ---- camera
    cd = bpy.data.cameras.new('Cam'); co = bpy.data.objects.new('Cam', cd); sc.collection.objects.link(co); sc.camera = co
    cd.sensor_width = 36; cd.clip_start = 0.03; cd.clip_end = 100000
    cd.dof.aperture_blades = 7
    sc.render.fps = cam.FPS; sc.frame_start = 1; sc.frame_end = cam.NFRAMES
    for fr in range(0, cam.NFRAMES + 2):
        cam.apply(co, (fr - 1) / cam.FPS)
        co.keyframe_insert('location', frame=fr); co.keyframe_insert('rotation_euler', frame=fr)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    tris = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == 'MESH')
    print('saved', OUT, 'objects', len(bpy.data.objects), 'faces(incl. instances)', tris, 'time', round(time.time() - t0, 1))


main()

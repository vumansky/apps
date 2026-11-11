"""Tiny mesh builder: accumulates boxes / quads / prisms in a local frame and bakes one Blender mesh."""
import numpy as np
import bpy, bmesh

BOX_F = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]


class MB:
    def __init__(self):
        self.V, self.F, self.M = [], [], []
        self.n = 0
        self.mats = []
        self.attr = None  # optional per-vertex float list
        self.set_frame((0, 0, 0), (1, 0, 0), (0, 1, 0))

    # local frame: u along facade, d outward, z up
    def set_frame(self, origin, U, N):
        self.o = np.array(origin, float)
        self.U = np.array(U, float)
        self.N = np.array(N, float)

    def mat(self, name):
        if name not in self.mats:
            self.mats.append(name)
        return self.mats.index(name)

    def w(self, P):
        P = np.asarray(P, float).reshape(-1, 3)
        return self.o + np.outer(P[:, 0], self.U) + np.outer(P[:, 1], self.N) + np.outer(P[:, 2], (0, 0, 1))

    def add(self, P, faces, m, local=True):
        P = self.w(P) if local else np.asarray(P, float).reshape(-1, 3)
        mi = self.mat(m)
        b = self.n
        self.V.append(P)
        for f in faces:
            self.F.append(tuple(b + i for i in f))
            self.M.append(mi)
        self.n += len(P)

    def box(self, u0, u1, d0, d1, z0, z1, m):
        P = [(u0, d0, z0), (u1, d0, z0), (u1, d1, z0), (u0, d1, z0),
             (u0, d0, z1), (u1, d0, z1), (u1, d1, z1), (u0, d1, z1)]
        self.add(P, BOX_F, m)

    def quad(self, pts, m):
        self.add(pts, [(0, 1, 2, 3)], m)

    def prism(self, pts_uz, d0, d1, m):
        """extrude polygon given in (u,z) between depths d0,d1 (convex polys)."""
        n = len(pts_uz)
        P = [(u, d0, z) for u, z in pts_uz] + [(u, d1, z) for u, z in pts_uz]
        F = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
        F += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        self.add(P, F, m)

    def frustum(self, u0, u1, d0, d1, z0, z1, inset, m, inset_u=None):
        iu = inset if inset_u is None else inset_u
        P = [(u0, d0, z0), (u1, d0, z0), (u1, d1, z0), (u0, d1, z0),
             (u0 + iu, d0 + inset, z1), (u1 - iu, d0 + inset, z1), (u1 - iu, d1 - inset, z1), (u0 + iu, d1 - inset, z1)]
        self.add(P, BOX_F, m)

    def cyl(self, c, r0, r1, z0, z1, m, n=12, cap=True, a0=0.0, a1=2 * np.pi):
        """vertical cylinder / cone in local frame, c=(u,d)."""
        full = abs((a1 - a0) - 2 * np.pi) < 1e-6
        k = n if full else n + 1
        a = np.linspace(a0, a1, n, endpoint=False) if full else np.linspace(a0, a1, n + 1)
        P = [(c[0] + r0 * np.cos(t), c[1] + r0 * np.sin(t), z0) for t in a] + \
            [(c[0] + r1 * np.cos(t), c[1] + r1 * np.sin(t), z1) for t in a]
        F = []
        rng = range(k) if full else range(k - 1)
        for i in rng:
            j = (i + 1) % k
            F.append((i, j, k + j, k + i))
        if cap and full:
            F.append(tuple(range(2 * k - 1, k - 1, -1)))
        self.add(P, F, m)

    def dome(self, c, r, z0, h, m, n=14, rings=6, power=1.0):
        prev = None
        P, F = [], []
        for j in range(rings + 1):
            t = j / rings * np.pi / 2
            rr = r * np.cos(t) ** power
            zz = z0 + h * np.sin(t)
            for i in range(n):
                a = 2 * np.pi * i / n
                P.append((c[0] + rr * np.cos(a), c[1] + rr * np.sin(a), zz))
        for j in range(rings):
            for i in range(n):
                a, b = j * n + i, j * n + (i + 1) % n
                F.append((a, b, b + n, a + n))
        self.add(P, F, m)

    def tube(self, pts, radii, m, n=6):
        """tube along world-space polyline (used for branches, posts, wires)."""
        pts = np.asarray(pts, float)
        K = len(pts)
        P = []
        for i in range(K):
            t = pts[min(i + 1, K - 1)] - pts[max(i - 1, 0)]
            t /= np.linalg.norm(t) + 1e-9
            a = np.cross(t, (0, 0, 1))
            if np.linalg.norm(a) < 1e-3:
                a = np.cross(t, (1, 0, 0))
            a /= np.linalg.norm(a)
            b = np.cross(t, a)
            for k in range(n):
                th = 2 * np.pi * k / n
                P.append(pts[i] + radii[i] * (np.cos(th) * a + np.sin(th) * b))
        F = []
        for i in range(K - 1):
            for k in range(n):
                a_, b_ = i * n + k, i * n + (k + 1) % n
                F.append((a_, b_, b_ + n, a_ + n))
        self.add(P, F, m, local=False)

    def to_object(self, name, get_mat, coll=None, smooth=False, recalc=True, attr=None):
        V = np.concatenate(self.V) if self.V else np.zeros((0, 3))
        me = bpy.data.meshes.new(name)
        me.from_pydata(V.tolist(), [], self.F)
        me.polygons.foreach_set("material_index", self.M)
        for mn in self.mats:
            me.materials.append(get_mat(mn))
        if smooth:
            me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        me.update()
        if recalc:
            bm = bmesh.new(); bm.from_mesh(me)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(me); bm.free()
        if attr is not None:
            a = me.attributes.new("rnd", 'FLOAT', 'POINT')
            a.data.foreach_set("value", np.asarray(attr, np.float32))
        ob = bpy.data.objects.new(name, me)
        (coll or bpy.context.scene.collection).objects.link(ob)
        return ob


def mesh_from_arrays(name, V, F4, get_mat, matname, attr=None, coll=None, smooth=False, tris=False):
    """fast path: V (n,3) float, F (m,4 or 3) int arrays."""
    me = bpy.data.meshes.new(name)
    k = F4.shape[1]
    me.vertices.add(len(V)); me.vertices.foreach_set("co", V.astype(np.float32).ravel())
    me.loops.add(F4.size); me.loops.foreach_set("vertex_index", F4.astype(np.int32).ravel())
    me.polygons.add(len(F4))
    me.polygons.foreach_set("loop_start", np.arange(0, F4.size, k, dtype=np.int32))
    me.polygons.foreach_set("loop_total", np.full(len(F4), k, np.int32))
    if smooth:
        me.polygons.foreach_set("use_smooth", np.ones(len(F4), bool))
    me.materials.append(get_mat(matname))
    me.update(calc_edges=True)
    if attr is not None:
        for an, av in (attr.items() if isinstance(attr, dict) else [("rnd", attr)]):
            a = me.attributes.new(an, 'FLOAT', 'POINT')
            a.data.foreach_set("value", np.asarray(av, np.float32))
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob

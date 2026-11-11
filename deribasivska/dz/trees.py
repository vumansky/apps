"""Plane trees (Platanus): branching skeleton + thousands of palmate mesh leaves."""
import numpy as np
from .mb import MB, mesh_from_arrays

# palmate plane-leaf outline (unit size, stem at origin), 12 points + raised centre
_OUT = np.array([(0.0, 0.0), (0.22, -0.03), (0.50, 0.18), (0.28, 0.33), (0.47, 0.62), (0.18, 0.62),
                 (0.0, 1.0), (-0.18, 0.62), (-0.47, 0.62), (-0.28, 0.33), (-0.50, 0.18), (-0.22, -0.03)])
LEAF_P = np.concatenate([np.c_[_OUT, np.zeros(12)], [[0.0, 0.40, 0.07]]])
LEAF_P[[2, 4, 6, 8, 10], 2] = -0.05          # lobe tips droop a little
LEAF_T = np.array([(12, i, (i + 1) % 12) for i in range(12)])


def leaves_mesh(P, Nrm, size, rng, spin=None):
    """vectorised leaf instancing -> (verts, tris). P (n,3), Nrm (n,3) unit, size (n,)"""
    n = len(P)
    r = rng.normal(size=(n, 3))
    a = np.cross(Nrm, r); a /= np.linalg.norm(a, axis=1, keepdims=True) + 1e-9
    b = np.cross(Nrm, a)
    L = LEAF_P - np.array([0, 0.4, 0])
    V = (P[:, None, :] + size[:, None, None] * (L[None, :, 0:1] * a[:, None, :] + L[None, :, 1:2] * b[:, None, :] + L[None, :, 2:3] * Nrm[:, None, :]))
    F = (LEAF_T[None, :, :] + (np.arange(n) * 13)[:, None, None]).reshape(-1, 3)
    return V.reshape(-1, 3), F


def _unit(v):
    return v / (np.linalg.norm(v) + 1e-9)


def gen_tree(rng, name, get_mat, coll, n_leaves=9000, scale=1.0):
    wood = MB()
    leaf_pts = []   # (point, cluster id)
    up = np.array([0, 0, 1.0])
    cid = [0]

    def grow(p, d, L, r, level):
        nseg = 4
        pts = [p.copy()]; cur = d.copy()
        for i in range(nseg):
            cur = _unit(cur + rng.normal(size=3) * (0.13 + 0.05 * level) + up * (0.10 if level > 0 else 0.0))
            p = p + cur * L / nseg
            pts.append(p.copy())
        pts = np.array(pts)
        wood.tube(pts, np.linspace(r, r * 0.62, nseg + 1), 'bark:', n=[9, 7, 5, 4, 3][level])
        if level >= 3:
            cid[0] += 1
            for k in range(3):
                leaf_pts.append((pts[2] + (pts[4] - pts[2]) * rng.random(), cid[0], 0.75))
        if level >= 4:
            return
        if level == 3:
            return
        nch = [5, 3, 3][level - 1] if level > 0 else int(rng.integers(4, 6))
        az0 = rng.uniform(0, 2 * np.pi)
        for k in range(nch):
            az = az0 + 2 * np.pi * k / nch + rng.normal() * 0.35
            tilt = rng.uniform(0.55, 1.0) if level == 0 else rng.uniform(0.45, 0.95)
            a = np.cross(cur, up)
            if np.linalg.norm(a) < 0.1: a = np.array([1.0, 0, 0])
            a = _unit(a); b = np.cross(cur, a)
            side = np.cos(az) * a + np.sin(az) * b
            nd = _unit(cur * np.cos(tilt) + side * np.sin(tilt))
            start = pts[-1] if (k < nch - 1 or level == 0) else pts[2]
            grow(start, nd, L * rng.uniform(0.62, 0.78), r * 0.58, level + 1)
        if level >= 1:   # leader continues
            grow(pts[-1], cur, L * 0.7, r * 0.55, level + 1)

    th = rng.uniform(4.6, 6.0) * scale
    grow(np.zeros(3), _unit(up + rng.normal(size=3) * 0.03), th, 0.34 * scale, 0)
    # root flare
    wood.tube(np.array([[0, 0, -0.1], [0, 0, 0.25], [0, 0, 0.8]]), [0.55 * scale, 0.42 * scale, 0.34 * scale], 'bark:', n=10)
    wo = wood.to_object(name + '_wood', get_mat, coll=coll, smooth=True, recalc=False)

    C = np.array([p for p, _, _ in leaf_pts]); cl = np.array([c for _, c, _ in leaf_pts])
    idx = rng.integers(0, len(C), n_leaves)
    P = C[idx] + rng.normal(size=(n_leaves, 3)) * np.array([0.62, 0.62, 0.5]) * scale
    P[:, 2] = np.maximum(P[:, 2], th * 0.75)
    Nrm = rng.normal(size=(n_leaves, 3)) * np.array([1, 1, 0.55]) + np.array([0, 0, 0.75])
    Nrm /= np.linalg.norm(Nrm, axis=1, keepdims=True)
    size = rng.uniform(0.26, 0.40, n_leaves) * scale
    V, F = leaves_mesh(P, Nrm, size, rng)
    crand = np.random.default_rng(int(rng.integers(1 << 30))).random(cl.max() + 2)
    rnd = np.clip(0.55 * crand[cl[idx]] + 0.45 * rng.random(n_leaves) + rng.normal() * 0.0, 0, 1)
    lo = mesh_from_arrays(name + '_leaves', V, F, get_mat, 'leaf:tree', attr=np.repeat(rnd, 13), coll=coll)
    return wo, lo


def gen_far_tree(rng, name, get_mat, coll, n_leaves=2400):
    """cheap unit-size tree for courtyards and other streets: same leaf cards, bigger and fewer."""
    d = rng.normal(size=(n_leaves, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
    lobes = rng.normal(size=(7, 3)); lobes /= np.linalg.norm(lobes, axis=1, keepdims=True)
    rad = 0.72 + 0.28 * np.max(d @ lobes.T, axis=1) ** 2
    P = d * (rad * rng.uniform(0.72, 1.0, n_leaves))[:, None] * np.array([1, 1, 0.8])
    Nrm = d * 0.6 + rng.normal(size=(n_leaves, 3)) * 0.5 + np.array([0, 0, 0.5]); Nrm /= np.linalg.norm(Nrm, axis=1, keepdims=True)
    V, F = leaves_mesh(P, Nrm, rng.uniform(0.14, 0.21, n_leaves), rng)
    rnd = np.clip(0.5 * (0.5 + 0.5 * np.sin(d @ rng.normal(size=3) * 3)) + 0.5 * rng.random(n_leaves), 0, 1)
    lo = mesh_from_arrays(name, V, F, get_mat, 'leaf:tree', attr=np.repeat(rnd, 13), coll=coll)
    return lo

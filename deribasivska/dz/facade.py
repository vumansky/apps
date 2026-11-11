"""Procedural 19th-century Odesa facades (Italianate / neo-renaissance / eclectic)."""
import numpy as np

WALL_T = 0.45
BODY = ['salmon', 'cream', 'butter', 'sand', 'ochre', 'limestone', 'pistachio', 'rose', 'ivory', 'cream', 'limestone', 'butter', 'sky']
ROOFS = ['red', 'zinc', 'brown', 'green', 'zinc', 'red']
SHOPF = ['darkwood', 'green', 'burgundy', 'black', 'navy', 'wood']
AWN = ['burgundy', 'green', 'canvas', 'navy', 'burgundy_s', 'green_s', 'canvas']


def arch_spandrel(mb, u0, u1, zs, d0, d1, m, n=10):
    """fill between a semicircular arch (spring line zs) and the horizontal line at its crown."""
    r = (u1 - u0) / 2; cu = (u0 + u1) / 2; zt = zs + r
    for i in range(n):
        a0 = np.pi - np.pi * i / n; a1 = np.pi - np.pi * (i + 1) / n
        ua, za = cu + r * np.cos(a0), zs + r * np.sin(a0)
        ub, zb = cu + r * np.cos(a1), zs + r * np.sin(a1)
        mb.quad([(ua, d1, za), (ub, d1, zb), (ub, d1, zt), (ua, d1, zt)], m)       # front
        mb.quad([(ua, d0, za), (ub, d0, zb), (ub, d1, zb), (ua, d1, za)], m)       # intrados


def arch_ring(mb, u0, u1, zs, d0, d1, w, m, n=12):
    """archivolt moulding around a semicircular arch."""
    r = (u1 - u0) / 2; cu = (u0 + u1) / 2
    for i in range(n):
        a0 = np.pi - np.pi * i / n; a1 = np.pi - np.pi * (i + 1) / n
        pts = [(cu + r * np.cos(a0), zs + r * np.sin(a0)), (cu + r * np.cos(a1), zs + r * np.sin(a1)),
               (cu + (r + w) * np.cos(a1), zs + (r + w) * np.sin(a1)), (cu + (r + w) * np.cos(a0), zs + (r + w) * np.sin(a0))]
        mb.prism(pts, d0, d1, m)


def railing(mb, u0, u1, d, z0, h=1.0, side_d=None, m='iron:', belly=True):
    """wrought-iron balcony railing along u at depth d (+ optional returns back to side_d)."""
    t = 0.02
    def run(p0, p1):
        (ua, da), (ub, db) = p0, p1
        L = np.hypot(ub - ua, db - da); n = max(2, int(L / 0.115))
        mb.box(min(ua, ub) - t, max(ua, ub) + t, min(da, db) - t, max(da, db) + t, z0 + h - 0.04, z0 + h, m)
        mb.box(min(ua, ub) - t, max(ua, ub) + t, min(da, db) - t, max(da, db) + t, z0 + 0.08, z0 + 0.11, m)
        mb.box(min(ua, ub) - t, max(ua, ub) + t, min(da, db) - t, max(da, db) + t, z0 + h - 0.2, z0 + h - 0.18, m)
        for i in range(n + 1):
            f = i / n
            u, dd = ua + (ub - ua) * f, da + (db - da) * f
            if belly and da == db:
                # pot-bellied Odesa balusters: lower half swells outward
                mb.add([(u - .007, dd, z0 + h - .2), (u + .007, dd, z0 + h - .2), (u + .007, dd + .09, z0 + .42), (u - .007, dd + .09, z0 + .42)], [(0, 1, 2, 3)], m)
                mb.add([(u - .007, dd + .09, z0 + .42), (u + .007, dd + .09, z0 + .42), (u + .007, dd, z0 + .1), (u - .007, dd, z0 + .1)], [(0, 1, 2, 3)], m)
            else:
                mb.box(u - .007, u + .007, dd - .007, dd + .007, z0 + 0.1, z0 + h - 0.05, m)
    run((u0, d), (u1, d))
    if side_d is not None:
        run((u0, side_d), (u0, d)); run((u1, side_d), (u1, d))


def window(mb, rng, uc, ww, z0, wh, st, arched=False, door=False, hood='none', trim='trim:white', frame='paint:ivory'):
    u0, u1 = uc - ww / 2, uc + ww / 2
    zt = z0 + wh
    g = 'glass:lit' if rng.random() < st['lit'] else ('glass:dim' if rng.random() < 0.12 else 'glass:dark')
    zc = zt + (ww / 2 if arched else 0)
    mb.quad([(u0 - .02, -0.30, z0), (u1 + .02, -0.30, z0), (u1 + .02, -0.30, zc), (u0 - .02, -0.30, zc)], g)
    # sash frame
    f = 0.06
    for a, b in ((u0, u0 + f), (u1 - f, u1), (uc - f / 2, uc + f / 2)):
        mb.box(a, b, -0.30, -0.24, z0, zt, frame)
    for a, b in ((z0, z0 + f), (zt - f, zt), (z0 + wh * 0.68, z0 + wh * 0.68 + f)):
        mb.box(u0, u1, -0.30, -0.24, a, b, frame)
    if arched:
        arch_ring(mb, u0 + f, u1 - f, zt, -0.30, -0.24, f, frame, n=8)
        mb.box(uc - f / 2, uc + f / 2, -0.30, -0.24, zt, zt + ww / 2 - f, frame)
    # architrave
    aw = st['arch_w']
    mb.box(u0 - aw, u0, 0, 0.07, z0 - (0 if door else 0.0), zt, trim)
    mb.box(u1, u1 + aw, 0, 0.07, z0, zt, trim)
    if arched:
        arch_ring(mb, u0, u1, zt, 0, 0.08, aw, trim)
        mb.box(uc - 0.11, uc + 0.11, 0, 0.14, zc - 0.05, zc + aw + 0.12, trim)  # keystone
        ztop = zc + aw
    else:
        mb.box(u0 - aw, u1 + aw, 0, 0.07, zt, zt + aw, trim)
        ztop = zt + aw
    if not door:
        mb.box(u0 - aw - .06, u1 + aw + .06, 0, 0.16, z0 - 0.12, z0, trim)       # sill
        mb.box(u0 - aw, u1 + aw, 0, 0.04, z0 - 0.62, z0 - 0.12, trim)             # apron panel
        mb.box(u0 - aw + .1, u1 + aw - .1, 0.04, 0.07, z0 - 0.54, z0 - 0.2, st['body'])
    # hood
    if hood in ('flat', 'tri', 'seg'):
        zf = ztop + 0.14
        mb.box(u0 - aw, u1 + aw, 0, 0.05, ztop, zf, trim)                         # frieze
        for s in (-1, 1):                                                         # consoles
            cu = uc + s * (ww / 2 + aw * 0.5)
            mb.box(cu - .07, cu + .07, 0, 0.16, ztop - 0.25, zf, trim)
        mb.box(u0 - aw - .12, u1 + aw + .12, 0, 0.24, zf, zf + 0.09, trim)        # cornice
        hw = ww / 2 + aw + 0.12
        if hood == 'tri':
            mb.prism([(uc - hw, zf + .09), (uc + hw, zf + .09), (uc, zf + .09 + hw * 0.42)], 0, 0.18, trim)
            mb.prism([(uc - hw, zf + .09), (uc, zf + .09 + hw * 0.42), (uc, zf + .19 + hw * 0.42), (uc - hw - .06, zf + .17)], 0, 0.26, trim)
            mb.prism([(uc + hw, zf + .09), (uc + hw + .06, zf + .17), (uc, zf + .19 + hw * 0.42), (uc, zf + .09 + hw * 0.42)], 0, 0.26, trim)
        elif hood == 'seg':
            n = 8; R = hw * 1.25; cz = zf + .09 - np.sqrt(R * R - hw * hw)
            a_m = np.arcsin(hw / R)
            pts = [(uc + R * np.sin(a), cz + R * np.cos(a)) for a in np.linspace(-a_m, a_m, n + 1)]
            for i in range(n):
                (ua, za), (ub, zb) = pts[i], pts[i + 1]
                mb.prism([(ua, zf + .09), (ub, zf + .09), (ub, zb), (ua, za)], 0, 0.16, trim)
                mb.prism([(ua, za), (ub, zb), (ub, zb + .09), (ua, za + .09)], 0, 0.26, trim)
    elif hood == 'lintel':
        mb.box(u0 - aw - .08, u1 + aw + .08, 0, 0.18, ztop, ztop + 0.1, trim)
    return ztop


def cornice(mb, u0, u1, z, st, trim, scale=1.0, d_side=None):
    s = scale
    mb.box(u0, u1, 0, 0.06, z - 0.55 * s, z, trim)                       # frieze
    n = int((u1 - u0) / (0.26 * s))
    for i in range(n):                                                    # dentils
        u = u0 + (i + 0.25) * (u1 - u0) / n
        mb.box(u, u + 0.13 * s, 0.06, 0.17 * s, z - 0.16 * s, z, trim)
    if st['modillions']:
        nm = max(2, int((u1 - u0) / (0.85 * s)))
        for i in range(nm + 1):
            u = u0 + 0.1 + i * (u1 - u0 - 0.2) / nm
            mb.box(u - .08, u + .08, 0.06, 0.46 * s, z - 0.02, z + 0.16 * s, trim)
            mb.box(u - .08, u + .08, 0.06, 0.26 * s, z - 0.2 * s, z - 0.02, trim)
    mb.box(u0 - .5 * s, u1 + .5 * s, -0.2, 0.52 * s, z + 0.16 * s, z + 0.30 * s, trim)   # corona
    mb.box(u0 - .58 * s, u1 + .58 * s, -0.2, 0.60 * s, z + 0.30 * s, z + 0.38 * s, trim)
    mb.box(u0 - .66 * s, u1 + .66 * s, -0.2, 0.68 * s, z + 0.38 * s, z + 0.44 * s, 'roof:zinc')
    return z + 0.44 * s


def parapet(mb, rng, u0, u1, z, st, trim, bays):
    h = 0.95
    kind = st['parapet']
    if kind == 'none':
        return z
    edges = np.linspace(u0, u1, bays + 1)
    for i, u in enumerate(edges):
        mb.box(u - .22, u + .22, -0.35, 0.05, z, z + h + 0.12, trim)
        mb.box(u - .27, u + .27, -0.40, 0.10, z + h + 0.12, z + h + 0.2, trim)
        if st['urns'] and i % 2 == 0:
            mb.cyl((u, -0.15), 0.08, 0.2, z + h + 0.2, z + h + 0.48, trim, n=8)
            mb.cyl((u, -0.15), 0.2, 0.05, z + h + 0.48, z + h + 0.72, trim, n=8)
    for i in range(bays):
        a, b = edges[i] + .22, edges[i + 1] - .22
        mb.box(a, b, -0.3, 0.0, z, z + 0.16, trim)
        mb.box(a, b, -0.32, 0.02, z + h - 0.02, z + h + 0.1, trim)
        if kind == 'balusters':
            n = int((b - a) / 0.24)
            for k in range(n):
                u = a + (k + 0.5) * (b - a) / n
                mb.box(u - .055, u + .055, -0.21, -0.09, z + 0.16, z + h - 0.02, trim)
        else:
            mb.box(a, b, -0.26, -0.04, z + 0.16, z + h - 0.02, st['body'])
    return z + h + 0.2


def facade(mb, rng, W, st, side=False):
    """build one facade in the current frame of mb. returns height of wall top."""
    floors = st['floors']; gh = st['gh']; fh = st['fh']
    body, trim, rustic = st['body'], st['trim'], st['rustic']
    nb = max(2, int(round(W / st['bay'])))
    bw = W / nb
    H = gh + (floors - 1) * fh
    # ---------------- ground floor
    mb.box(0, W, 0, 0.07, 0, 0.55, 'trim:grey')                            # plinth
    gate = (nb // 2) if (st['gate'] and not side and nb >= 5) else -1
    for b in range(nb):
        ub0, ub1 = b * bw, (b + 1) * bw
        uc = (ub0 + ub1) / 2
        if b == gate:                                                      # carriage arch into courtyard
            ow = min(2.9, bw - 0.7); zs = 2.6
            u0, u1 = uc - ow / 2, uc + ow / 2
            mb.box(ub0, u0, -WALL_T, 0, 0, gh, rustic); mb.box(u1, ub1, -WALL_T, 0, 0, gh, rustic)
            mb.box(u0, u1, -WALL_T, 0, zs + ow / 2, gh, rustic)
            arch_spandrel(mb, u0, u1, zs, -WALL_T, 0, rustic)
            arch_ring(mb, u0, u1, zs, 0, 0.1, 0.3, trim)
            mb.box(uc - .16, uc + .16, 0, 0.2, zs + ow / 2 - .05, zs + ow / 2 + 0.5, trim)
            mb.quad([(u0, -3.5, 0), (u1, -3.5, 0), (u1, -3.5, gh), (u0, -3.5, gh)], 'paint:black')
            mb.box(u0 - .01, u0, -3.5, -WALL_T, 0, gh, 'stucco:sand'); mb.box(u1, u1 + .01, -3.5, -WALL_T, 0, gh, 'stucco:sand')
            for k in range(int(ow / 0.13) + 1):                           # iron gate, half open look
                u = u0 + k * 0.13
                mb.box(u - .009, u + .009, -0.5, -0.48, 0.05, zs + np.sqrt(max(0, (ow / 2) ** 2 - (u - uc) ** 2)) - 0.03, 'iron:')
            mb.box(u0, u1, -0.51, -0.47, 1.1, 1.16, 'iron:'); mb.box(u0, u1, -0.51, -0.47, 2.5, 2.56, 'iron:')
            continue
        is_shop = st['shops'] and rng.random() < 0.9
        if is_shop:
            ow = bw - 0.75; zt = min(3.55, gh - 1.0)
            u0, u1 = uc - ow / 2, uc + ow / 2
            mb.box(ub0, u0, -WALL_T, 0, 0, gh, rustic); mb.box(u1, ub1, -WALL_T, 0, 0, gh, rustic)
            mb.box(u0, u1, -WALL_T, 0, zt, gh, rustic)
            sf = st['shopf']
            is_door = rng.random() < 0.35
            riser = 0.0 if is_door else 0.55
            if riser: mb.box(u0, u1, -0.32, -0.1, 0, riser, sf)
            mb.quad([(u0, -0.28, riser), (u1, -0.28, riser), (u1, -0.28, zt), (u0, -0.28, zt)], 'shopglass:')
            fw = 0.07
            for a, c in ((u0, u0 + fw), (u1 - fw, u1)):
                mb.box(a, c, -0.3, -0.16, riser, zt, sf)
            mb.box(u0, u1, -0.3, -0.16, zt - fw, zt, sf)
            mb.box(u0, u1, -0.3, -0.18, zt - 0.75, zt - 0.69, sf)          # transom bar
            if is_door:
                for a in (uc - 0.5, uc + 0.5):
                    mb.box(a - .035, a + .035, -0.3, -0.18, 0, zt - 0.72, sf)
                mb.box(uc - .5, uc + .5, -0.3, -0.2, 0, 0.3, sf)
                mb.box(uc + .38, uc + .42, -0.18, -0.12, 1.0, 1.35, 'metal:gold')
                mb.box(uc - .7, uc + .7, -0.1, 0.25, 0, 0.09, 'trim:grey')    # step
            else:
                n = max(1, int(ow / 1.3))
                for k in range(1, n):
                    a = u0 + k * ow / n
                    mb.box(a - .025, a + .025, -0.3, -0.18, riser, zt, sf)
            # signage fascia
            mb.box(u0 - .12, u1 + .12, 0, 0.09, zt + 0.08, zt + 0.62, sf)
            mb.box(u0 - .12, u1 + .12, 0.09, 0.11, zt + 0.12, zt + 0.15, 'metal:gold')
            mb.box(u0 - .12, u1 + .12, 0.09, 0.11, zt + 0.55, zt + 0.58, 'metal:gold')
            if rng.random() < 0.55:
                sw = ow * rng.uniform(0.3, 0.55)
                mb.box(uc - sw / 2, uc + sw / 2, 0.09, 0.115, zt + 0.25, zt + 0.45, 'metal:gold')
            if st['awn'] and rng.random() < 0.85:
                am = 'awning:' + st['awn']
                proj = st['awn_p']
                mb.quad([(u0 - .1, 0.1, zt + .05), (u1 + .1, 0.1, zt + .05), (u1 + .1, proj, zt - .75), (u0 - .1, proj, zt - .75)], am)
                mb.quad([(u0 - .1, proj, zt - .75), (u1 + .1, proj, zt - .75), (u1 + .1, proj, zt - 1.0), (u0 - .1, proj, zt - 1.0)], am)
                for a in (u0 - .1, u1 + .1):
                    mb.add([(a, 0.1, zt + .05), (a, proj, zt - .75), (a, 0.1, zt - .75)], [(0, 1, 2)], am)
            elif rng.random() < 0.5:                                       # lantern beside shop
                mb.box(ub0 - .03, ub0 + .03, 0, 0.35, 3.0, 3.04, 'iron:')
                mb.box(ub0 - .1, ub0 + .1, 0.25, 0.45, 2.62, 3.0, 'lamp:')
                mb.frustum(ub0 - .13, ub0 + .13, 0.22, 0.48, 3.0, 3.1, 0.1, 'iron:')
        else:
            ww = min(1.3, bw - 1.2); z0 = 1.15; wh = gh - 2.4
            u0, u1 = uc - ww / 2, uc + ww / 2
            mb.box(ub0, u0, -WALL_T, 0, 0, gh, rustic); mb.box(u1, ub1, -WALL_T, 0, 0, gh, rustic)
            mb.box(u0, u1, -WALL_T, 0, 0, z0, rustic)
            arch = st['g_arch']
            mb.box(u0, u1, -WALL_T, 0, z0 + wh + (ww / 2 if arch else 0), gh, rustic)
            if arch: arch_spandrel(mb, u0, u1, z0 + wh, -WALL_T, 0, rustic)
            window(mb, rng, uc, ww, z0, wh, st, arched=arch, hood='none', trim=trim, frame=st['frame'])
    zc = gh
    mb.box(-0.05, W + 0.05, 0, 0.2, zc - 0.28, zc - 0.1, trim)             # belt course over ground floor
    mb.box(-0.08, W + 0.08, 0, 0.26, zc - 0.1, zc, trim)
    # ---------------- upper floors
    bal_bays = set()
    if st['balcony'] != 'none' and floors > 1 and not side:
        mid = nb // 2
        if st['balcony'] == 'center': bal_bays = {mid} if nb % 2 else {mid - 1, mid}
        elif st['balcony'] == 'wide': bal_bays = {mid - 1, mid, mid + 1} if nb >= 5 else {mid}
        elif st['balcony'] == 'alt': bal_bays = set(range(1, nb - 1, 2))
        elif st['balcony'] == 'ends': bal_bays = {1, nb - 2} if nb >= 5 else {mid}
    for fl in range(1, floors):
        zf = gh + (fl - 1) * fh
        top = fl == floors - 1
        ww = st['ww']; sill = 0.95
        wh = min(st['wh'] - (0.25 if (top and floors > 2) else 0), fh - sill - 0.85)
        arched = st['arch_floor'] == fl
        hood = st['hoods'][min(fl - 1, len(st['hoods']) - 1)]
        if arched: wh -= ww / 2 * 0.7; hood = 'none'
        for b in range(nb):
            ub0, ub1 = b * bw, (b + 1) * bw
            uc = (ub0 + ub1) / 2
            door = (b in bal_bays) and (fl == 1 or (fl == 2 and st['bal2']))
            z0 = zf + (0.12 if door else sill)
            whh = wh + (sill - 0.12 if door else 0)
            u0, u1 = uc - ww / 2, uc + ww / 2
            mb.box(ub0, u0, -WALL_T, 0, zf, zf + fh, body); mb.box(u1, ub1, -WALL_T, 0, zf, zf + fh, body)
            mb.box(u0, u1, -WALL_T, 0, zf, z0, body)
            mb.box(u0, u1, -WALL_T, 0, z0 + whh + (ww / 2 if arched else 0), zf + fh, body)
            if arched: arch_spandrel(mb, u0, u1, z0 + whh, -WALL_T, 0, body)
            window(mb, rng, uc, ww, z0, whh, st, arched=arched, door=door, hood=hood, trim=trim, frame=st['frame'])
        # balconies
        if bal_bays and (fl == 1 or (fl == 2 and st['bal2'])):
            runs = []
            for b in sorted(bal_bays):
                if runs and st['balcony'] == 'wide' and b == runs[-1][1] + 1: runs[-1][1] = b
                else: runs.append([b, b])
            for a, b in runs:
                u0 = a * bw + (bw - ww) / 2 - 0.45; u1 = (b + 1) * bw - (bw - ww) / 2 + 0.45
                pr = st['bal_p']
                mb.box(u0, u1, 0, pr, zf - 0.04, zf + 0.1, trim)
                mb.box(u0 + .04, u1 - .04, 0, pr - .05, zf - 0.12, zf - 0.04, trim)
                nbk = max(2, int((u1 - u0) / 1.5) + 1)
                for k in range(nbk):                                       # scrolled consoles
                    u = u0 + 0.18 + k * (u1 - u0 - 0.36) / (nbk - 1)
                    if st['bal_iron']:
                        mb.add([(u - .02, 0.0, zf - 0.12), (u + .02, 0.0, zf - 0.12), (u + .02, pr - .1, zf - 0.12), (u - .02, pr - .1, zf - 0.12),
                                (u - .02, 0.0, zf - 0.8), (u + .02, 0.0, zf - 0.8)], [(0, 1, 2, 3), (0, 3, 4), (1, 5, 2), (4, 5, 2, 3)], 'iron:')
                    else:
                        mb.box(u - .09, u + .09, 0, pr * 0.85, zf - 0.3, zf - 0.12, trim)
                        mb.box(u - .09, u + .09, 0, pr * 0.5, zf - 0.52, zf - 0.3, trim)
                        mb.box(u - .09, u + .09, 0, pr * 0.22, zf - 0.75, zf - 0.52, trim)
                railing(mb, u0 + .05, u1 - .05, pr - 0.06, zf + 0.1, side_d=0.0)
        if not top and st['belt']:
            mb.box(-0.03, W + 0.03, 0, 0.12, zf + fh - 0.14, zf + fh, trim)
    # pilasters / quoins
    if st['order'] == 'pilasters' and floors > 1:
        step = st['pil_step']
        for b in range(0, nb + 1, step):
            u = min(max(b * bw, 0.32), W - 0.32)
            mb.box(u - .3, u + .3, 0, 0.11, gh, H - 0.6, trim)
            mb.box(u - .36, u + .36, 0, 0.16, gh, gh + 0.35, trim)
            mb.box(u - .36, u + .36, 0, 0.17, H - 0.95, H - 0.6, trim)
            mb.box(u - .4, u + .4, 0, 0.2, H - 0.68, H - 0.6, trim)
    elif st['order'] == 'quoins':
        for u in (0.0, W):
            k = 0; z = gh
            while z < H - 0.7:
                w = 0.55 if k % 2 == 0 else 0.36
                a, b_ = (u, u + w) if u == 0 else (u - w, u)
                mb.box(a, b_, 0, 0.06, z + .02, z + 0.4, trim)
                z += 0.42; k += 1
    ztop = cornice(mb, 0, W, H, st, trim, scale=st['corn'])
    ztop2 = parapet(mb, rng, 0.2, W - 0.2, ztop, st, trim, nb) 
    # attic / pediment over centre
    if st['attic'] != 'none' and not side and nb >= 5:
        a = (nb // 2 - 1) * bw; b = (nb // 2 + 2) * bw if nb % 2 else (nb // 2 + 1) * bw
        if st['attic'] == 'pediment':
            hh = (b - a) * 0.2
            mb.box(a, b, -0.4, 0.1, ztop, ztop + 0.5, trim)
            mb.prism([(a - .2, ztop + .5), (b + .2, ztop + .5), ((a + b) / 2, ztop + .5 + hh)], -0.4, 0.14, trim)
            mb.prism([(a + .5, ztop + .62), (b - .5, ztop + .62), ((a + b) / 2, ztop + .42 + hh)], 0.14, 0.16, body)
        else:
            mb.box(a, b, -0.4, 0.08, ztop, ztop + 1.7, body)
            mb.box(a - .1, b + .1, -0.45, 0.2, ztop + 1.7, ztop + 1.9, trim)
            mb.box(a + .6, b - .6, 0.08, 0.13, ztop + 0.4, ztop + 1.4, trim)
            n = 9; R = (b - a) / 2 - 0.4
            for i in range(n):
                a0 = np.pi * i / n; a1 = np.pi * (i + 1) / n
                mb.prism([((a + b) / 2 + R * np.cos(a0), ztop + 1.9), ((a + b) / 2 + R * np.cos(a1), ztop + 1.9),
                          ((a + b) / 2 + R * np.cos(a1), ztop + 1.9 + R * 0.45 * np.sin(a1)), ((a + b) / 2 + R * np.cos(a0), ztop + 1.9 + R * 0.45 * np.sin(a0))], -0.4, 0.1, trim)
    return H, ztop, ztop2


def make_style(rng, floors=None, body=None):
    floors = floors or int(rng.choice([2, 3, 3, 3, 4, 4]))
    body_k = body or str(rng.choice(BODY))
    trim_k = 'white' if body_k not in ('ivory', 'white') else 'sand'
    if rng.random() < 0.18: trim_k = body_k if body_k in ('limestone', 'cream') else trim_k
    hoods_all = ['tri', 'seg', 'flat', 'lintel', 'flat', 'tri']
    h1 = str(rng.choice(hoods_all)); h2 = str(rng.choice(['flat', 'lintel', 'seg', 'tri'])); h3 = str(rng.choice(['lintel', 'none', 'flat']))
    return dict(
        floors=floors, gh=float(rng.uniform(4.7, 5.4)), fh=float(rng.uniform(4.0, 4.5)), bay=float(rng.uniform(2.7, 3.3)),
        body='stucco:' + body_k, trim='trim:' + trim_k,
        rustic='rustic:' + str(rng.choice(['limestone', 'cream', 'sand', 'limestone', body_k if body_k in ('cream', 'sand', 'butter', 'ivory') else 'limestone'])),
        ww=float(rng.uniform(1.15, 1.35)), wh=float(rng.uniform(2.3, 2.6)), arch_w=float(rng.uniform(0.16, 0.22)),
        hoods=[h1, h2, h3], arch_floor=int(rng.choice([0, 0, 0, 1, 2, 3])), g_arch=bool(rng.random() < 0.5),
        balcony=str(rng.choice(['center', 'wide', 'alt', 'ends', 'alt', 'none', 'center'])), bal2=bool(rng.random() < 0.4),
        bal_p=float(rng.uniform(0.85, 1.15)), bal_iron=bool(rng.random() < 0.5),
        belt=bool(rng.random() < 0.7), order=str(rng.choice(['pilasters', 'quoins', 'none', 'pilasters'])),
        pil_step=int(rng.choice([1, 1, 2])), modillions=bool(rng.random() < 0.65), corn=float(rng.uniform(0.9, 1.25)),
        parapet=str(rng.choice(['balusters', 'solid', 'none', 'balusters', 'solid'])), urns=bool(rng.random() < 0.35),
        attic=str(rng.choice(['none', 'none', 'pediment', 'attic', 'none'])),
        gate=bool(rng.random() < 0.6), shops=True, shopf='paint:' + str(rng.choice(SHOPF)),
        awn=(str(rng.choice(AWN)) if rng.random() < 0.6 else ''), awn_p=float(rng.uniform(1.3, 1.9)),
        frame='paint:' + str(rng.choice(['ivory', 'ivory', 'darkwood', 'wood'])), lit=float(rng.uniform(0.04, 0.2)),
        roof='roof:' + str(rng.choice(ROOFS)), turret=False,
    )


def building(mb, rng, origin, U, N, W, depth, st, side_left=False, side_right=False, back=True):
    """full building: front facade along U from origin, outward normal N."""
    origin = np.array(origin, float); U = np.array(U, float); N = np.array(N, float)
    mb.set_frame(origin, U, N)
    H, ztop, zpar = facade(mb, rng, W, st)
    body = st['body']
    # mass behind the facade
    mb.box(0.02, W - 0.02, -depth, -WALL_T + 0.02, 0, H + 0.3, body)
    # roof (hip) + chimneys + dormers
    rz = ztop - 0.1
    rise = float(rng.uniform(2.2, 3.4))
    if st.get('mansard'):
        mh = 3.3
        mb.frustum(-0.25, W + 0.25, -depth - 0.25, -0.2, rz, rz + mh, 1.1, st['roof'])
        mb.frustum(-0.25 + 1.1, W + 0.25 - 1.1, -depth - 0.25 + 1.1, -0.2 - 1.1, rz + mh, rz + mh + 1.3, 3.2, st['roof'])
        mb.box(0.8, W - 0.8, -1.38, -1.25, rz + mh - 0.05, rz + mh + 0.12, st['trim'])
        nb_ = max(2, int(round(W / st['bay'])))
        for k in range(nb_):
            u = (k + 0.5) * W / nb_
            mb.box(u - .62, u + .62, -1.6, -0.5, rz + 0.35, rz + 2.35, st['trim'])
            mb.quad([(u - .42, -0.49, rz + .6), (u + .42, -0.49, rz + .6), (u + .42, -0.49, rz + 2.1), (u - .42, -0.49, rz + 2.1)], 'glass:dark' if rng.random() > 0.2 else 'glass:lit')
            mb.box(u - .03, u + .03, -0.5, -0.46, rz + .6, rz + 2.1, st['frame'])
            n_ = 6
            for i in range(n_):
                a0 = np.pi * i / n_; a1 = np.pi * (i + 1) / n_
                mb.prism([(u, rz + 2.35), (u + .72 * np.cos(a0), rz + 2.35 + .5 * np.sin(a0)), (u + .72 * np.cos(a1), rz + 2.35 + .5 * np.sin(a1))], -1.6, -0.42, st['roof'])
        rise = mh + 1.3
    else:
        mb.frustum(-0.3, W + 0.3, -depth - 0.3, -0.25, rz, rz + rise, rise * 1.25, st['roof'])
    for k in range(int(W / 7) + 1):
        u = rng.uniform(1.5, W - 1.5); d = -rng.uniform(depth * 0.35, depth * 0.65)
        w = rng.uniform(0.7, 1.3)
        mb.box(u, u + w, d, d + 0.6, rz + rise * 0.5, rz + rise + rng.uniform(0.8, 1.5), 'stucco:terracotta' if rng.random() < 0.5 else body)
    if st['floors'] <= 3 and rng.random() < 0.5:
        nd = max(1, int(W / 6))
        for k in range(nd):
            u = (k + 0.5) * W / nd
            mb.box(u - .6, u + .6, -2.6, -1.0, rz + 0.5, rz + 1.7, body)
            mb.quad([(u - .4, -0.99, rz + .7), (u + .4, -0.99, rz + .7), (u + .4, -0.99, rz + 1.5), (u - .4, -0.99, rz + 1.5)], 'glass:dark')
            mb.prism([(u - .75, rz + 1.7), (u + .75, rz + 1.7), (u, rz + 2.15)], -2.6, -0.9, st['roof'])
    # sides
    for flag, o2, U2, N2 in ((side_left, origin - N * depth, N, -U), (side_right, origin + U * W, -N, U)):
        if flag:
            mb.set_frame(o2, U2, N2)
            facade(mb, rng, depth, dict(st, gate=False, balcony='none', attic='none'), side=True)
    mb.set_frame(origin, U, N)
    if st.get('turret'):
        for uu in st['turret']:
            r = 2.3
            c = (uu, -r * 0.55)
            mb.cyl(c, r, r, st['gh'], zpar + 1.2, body, n=16)
            for k in range(8):
                a = 2 * np.pi * k / 8
                pu, pd = c[0] + r * np.cos(a), c[1] + r * np.sin(a)
                mb.box(pu - .16, pu + .16, pd - .16, pd + .16, st['gh'], zpar + 1.2, st['trim'])
            mb.cyl(c, r + .3, r + .3, zpar + 1.2, zpar + 1.5, st['trim'], n=16)
            mb.cyl(c, r + .25, r + .25, st['gh'] - .3, st['gh'], st['trim'], n=16)
            mb.dome(c, r + 0.1, zpar + 1.5, r * 1.5, st['roof'], n=16, rings=7, power=0.8)
            mb.cyl(c, 0.35, 0.3, zpar + 1.5 + r * 1.45, zpar + 2.6 + r * 1.5, st['trim'], n=8)
            mb.cyl(c, 0.3, 0.02, zpar + 2.6 + r * 1.5, zpar + 5.0 + r * 1.5, st['roof'], n=8)
    if back:
        # simple rear windows
        mb.set_frame(origin - N * depth + U * W, -U, -N)
        nb = max(2, int(W / 3.2))
        for fl in range(st['floors']):
            z = (0 if fl == 0 else st['gh'] + (fl - 1) * st['fh']) + 1.0
            for b in range(nb):
                uc = (b + 0.5) * W / nb
                mb.box(uc - .55, uc + .55, 0.0, 0.02, z, z + 2.0, 'glass:dark')
                mb.box(uc - .65, uc + .65, 0.0, 0.05, z - .1, z, st['trim'])
        mb.set_frame(origin, U, N)
    return H, zpar

"""Procedural Cycles materials. get_mat('type:key') builds lazily and caches."""
import bpy

PAL = {  # Odesa facade palette (linear-ish sRGB values, tuned against reference photos)
    'cream': (0.80, 0.66, 0.42), 'sand': (0.74, 0.58, 0.34), 'ochre': (0.78, 0.55, 0.22),
    'butter': (0.86, 0.72, 0.40), 'pistachio': (0.52, 0.60, 0.40), 'rose': (0.76, 0.48, 0.38),
    'grey': (0.58, 0.58, 0.55), 'white': (0.84, 0.80, 0.70), 'ivory': (0.88, 0.82, 0.66),
    'sky': (0.52, 0.62, 0.68), 'salmon': (0.80, 0.42, 0.26), 'terracotta': (0.62, 0.30, 0.18), 'limestone': (0.78, 0.67, 0.45),
    'roof_red': (0.19, 0.05, 0.03), 'roof_zinc': (0.10, 0.105, 0.11), 'roof_green': (0.055, 0.105, 0.085),
    'roof_brown': (0.105, 0.058, 0.038), 'burgundy': (0.30, 0.03, 0.04), 'green': (0.04, 0.16, 0.08),
    'navy': (0.03, 0.06, 0.16), 'black': (0.015, 0.015, 0.017), 'wood': (0.22, 0.10, 0.04),
    'darkwood': (0.08, 0.035, 0.015), 'canvas': (0.80, 0.72, 0.56), 'linen': (0.85, 0.83, 0.78),
    'gold': (0.75, 0.50, 0.12), 'copper': (0.20, 0.42, 0.34),
}
_cache = {}


class NT:
    def __init__(self, mat):
        self.t = mat.node_tree
        self.t.nodes.clear()
        self.out = self.n('ShaderNodeOutputMaterial')

    def n(self, typ, ins=None, **props):
        nd = self.t.nodes.new(typ)
        for k, v in props.items():
            setattr(nd, k, v)
        for k, v in (ins or {}).items():
            self.set(nd, k, v)
        return nd

    def set(self, nd, key, v):
        sock = nd.inputs[key]
        if isinstance(v, bpy.types.NodeSocket):
            self.t.links.new(v, sock)
        elif isinstance(v, bpy.types.Node):
            self.t.links.new(v.outputs[0], sock)
        else:
            if hasattr(sock, 'default_value'):
                try:
                    sock.default_value = v
                except Exception:
                    sock.default_value = tuple(v) + (1.0,)

    def math(self, op, a, b=None, c=None, clamp=False):
        if op == 'SMOOTHSTEP':   # smoothstep(lo=a, hi=b, x=c)
            nd = self.n('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
            self.set(nd, 'Value', c); self.set(nd, 'From Min', a); self.set(nd, 'From Max', b)
            return nd.outputs[0]
        nd = self.n('ShaderNodeMath', operation=op, use_clamp=clamp)
        self.set(nd, 0, a)
        if b is not None: self.set(nd, 1, b)
        if c is not None: self.set(nd, 2, c)
        return nd.outputs[0]

    def mix(self, fac, a, b, blend='MIX'):
        nd = self.n('ShaderNodeMix', data_type='RGBA', blend_type=blend)
        self.set(nd, 0, fac); self.set(nd, 6, a); self.set(nd, 7, b)
        return nd.outputs[2]

    def ramp(self, fac, stops, interp='LINEAR'):
        nd = self.n('ShaderNodeValToRGB')
        cr = nd.color_ramp
        cr.interpolation = interp
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for e, (p, c) in zip(cr.elements, stops):
            e.position = p
            e.color = tuple(c) + (1.0,) if len(c) == 3 else c
        self.set(nd, 0, fac)
        return nd.outputs[0]

    def noise(self, vec, scale, detail=3.0, rough=0.55, dim='3D', w=None):
        nd = self.n('ShaderNodeTexNoise', noise_dimensions=dim)
        if vec is not None: self.set(nd, 'Vector', vec)
        if w is not None: self.set(nd, 'W', w)
        self.set(nd, 'Scale', scale); self.set(nd, 'Detail', detail); self.set(nd, 'Roughness', rough)
        return nd.outputs[0]

    def bump(self, height, strength=0.3, dist=0.02, normal=None):
        nd = self.n('ShaderNodeBump')
        self.set(nd, 'Height', height); self.set(nd, 'Strength', strength); self.set(nd, 'Distance', dist)
        if normal is not None: self.set(nd, 'Normal', normal)
        return nd.outputs[0]

    def pos(self):
        return self.n('ShaderNodeNewGeometry').outputs['Position']

    def facade_uv(self):
        """(along-wall, height) coordinates from world position + normal."""
        g = self.n('ShaderNodeNewGeometry')
        sp = self.n('ShaderNodeSeparateXYZ', {0: g.outputs['Position']})
        sn = self.n('ShaderNodeSeparateXYZ', {0: g.outputs['True Normal']})
        ax = self.math('ABSOLUTE', sn.outputs[0]); ay = self.math('ABSOLUTE', sn.outputs[1])
        sel = self.math('GREATER_THAN', ax, ay)
        h = self.math('ADD', self.math('MULTIPLY', sel, sp.outputs[1]),
                      self.math('MULTIPLY', self.math('SUBTRACT', 1.0, sel), sp.outputs[0]))
        return self.n('ShaderNodeCombineXYZ', {0: h, 1: sp.outputs[2], 2: 0.0}).outputs[0], sp.outputs[2]

    def principled(self, **ins):
        nd = self.n('ShaderNodeBsdfPrincipled')
        for k, v in ins.items():
            self.set(nd, k.replace('_', ' '), v)
        return nd

    def finish(self, shader):
        self.t.links.new(shader.outputs[0] if isinstance(shader, bpy.types.Node) else shader, self.out.inputs[0])


def _new(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, NT(m)


def m_stucco(name, key, rustic=False):
    m, t = _new(name)
    col = PAL[key]
    uv, z = t.facade_uv()
    p = t.pos()
    stain = t.noise(p, 0.35, 2, 0.6)
    streak_v = t.n('ShaderNodeMapping', {'Vector': uv, 'Scale': (3.0, 0.12, 1.0)})
    streak = t.noise(streak_v, 2.0, 1, 0.6)
    c = t.mix(t.math('MULTIPLY', t.math('SUBTRACT', stain, 0.35, clamp=True), 0.55), col,
              tuple(x * 0.72 for x in col))
    c = t.mix(t.math('MULTIPLY', t.math('SUBTRACT', streak, 0.5, clamp=True), 0.5), c,
              (col[0] * 0.55, col[1] * 0.52, col[2] * 0.5))
    h = 0.0
    if rustic:
        # coquina limestone blocks: joints + porous shell texture
        br = t.n('ShaderNodeTexBrick', {'Vector': uv, 'Scale': 1.0, 'Mortar Size': 0.018, 'Mortar Smooth': 0.6,
                                         'Brick Width': 0.95, 'Row Height': 0.42,
                                         'Color1': (0.55, 0.55, 0.55, 1), 'Color2': (0.42, 0.42, 0.42, 1),
                                         'Mortar': (0.0, 0.0, 0.0, 1)}, offset=0.5)
        blockv = t.n('ShaderNodeSeparateColor', {0: br.outputs['Color']}).outputs[0]
        c = t.mix(1.0, c, t.n('ShaderNodeCombineColor', {0: t.math('ADD', blockv, 0.5),
                                                          1: t.math('ADD', blockv, 0.5),
                                                          2: t.math('ADD', blockv, 0.5)}).outputs[0], 'MULTIPLY')
        vor = t.n('ShaderNodeTexVoronoi', {'Vector': p, 'Scale': 45.0}, feature='F1')
        pores = t.math('SMOOTHSTEP', 0.0, 0.25, vor.outputs['Distance'])
        c = t.mix(t.math('SUBTRACT', 1.0, pores), c, tuple(x * 0.55 for x in col))
        h = t.math('SUBTRACT', 1.0, br.outputs['Fac'])
        nrm = t.bump(h, 0.9, 0.025)
    else:
        nrm = None
    # ground dirt
    dirt = t.math('SUBTRACT', 1.0, t.math('SMOOTHSTEP', 0.0, 1.6, z))
    c = t.mix(t.math('MULTIPLY', dirt, 0.35), c, (0.16, 0.14, 0.12))
    pr = t.principled(Base_Color=c, Roughness=0.86)
    if nrm is not None: t.set(pr, 'Normal', nrm)
    t.finish(pr)
    return m


def m_flat(name, key, rough=0.5, metal=0.0, spec=None):
    m, t = _new(name)
    col = PAL[key]
    p = t.pos()
    n = t.noise(p, 3.0, 3, 0.6)
    c = t.mix(t.math('MULTIPLY', n, 0.35), col, tuple(x * 0.6 for x in col))
    t.finish(t.principled(Base_Color=c, Roughness=rough, Metallic=metal))
    return m


def m_roof(name, key):
    m, t = _new(name)
    col = PAL[key]
    p = t.pos()
    uv, z = t.facade_uv()
    sx = t.n('ShaderNodeSeparateXYZ', {0: p})
    # standing seams every 0.55 m (along x+y so both slopes get them)
    s = t.math('ADD', sx.outputs[0], sx.outputs[1])
    seam = t.math('PINGPONG', s, 0.28)
    seam = t.math('SMOOTHSTEP', 0.0, 0.03, seam)
    n = t.noise(p, 0.8, 4, 0.65)
    c = t.mix(t.math('MULTIPLY', n, 0.6), col, tuple(min(1, x * 1.35 + 0.01) for x in col))
    rust = t.noise(p, 2.5, 5, 0.7)
    c = t.mix(t.math('SMOOTHSTEP', 0.6, 0.8, rust), c, (0.25, 0.12, 0.06))
    nrm = t.bump(t.math('SUBTRACT', 1.0, seam), 0.5, 0.02)
    t.finish(t.principled(Base_Color=c, Roughness=t.math('ADD', 0.62, t.math('MULTIPLY', n, 0.3)),
                          Metallic=0.0, Normal=nrm))
    return m


def m_glass(name, lit=0.0, tint=(0.02, 0.03, 0.04)):
    m, t = _new(name)
    p = t.pos()
    wav = t.noise(p, 1.3, 2, 0.5)
    nrm = t.bump(wav, 0.06, 0.02)
    pr = t.principled(Base_Color=tint, Roughness=0.03, Normal=nrm)
    t.set(pr, 'Specular IOR Level', 1.0)
    if lit > 0:
        uv, z = t.facade_uv()
        cur = t.noise(t.n('ShaderNodeMapping', {'Vector': uv, 'Scale': (6.0, 0.3, 1.0)}), 1.5, 2, 0.5)
        ec = t.mix(cur, (1.0, 0.55, 0.20), (1.0, 0.72, 0.38))
        t.set(pr, 'Emission Color', ec); t.set(pr, 'Emission Strength', lit)
    t.finish(pr)
    m.cycles.emission_sampling = 'NONE'
    return m


def m_shopglass(name):
    """shop window: fresnel reflection over a fake warm-lit interior."""
    m, t = _new(name)
    uv, z = t.facade_uv()
    cell = t.n('ShaderNodeTexVoronoi', {'Vector': t.n('ShaderNodeMapping', {'Vector': uv, 'Scale': (1.3, 0.9, 1)}),
                                         'Scale': 1.0}, feature='F1')
    sm = t.noise(uv, 5.0, 3, 0.6)
    warm = t.ramp(t.math('ADD', t.math('MULTIPLY', cell.outputs['Distance'], 0.8), t.math('MULTIPLY', sm, 0.5)),
                  [(0.0, (1.0, 0.62, 0.25)), (0.45, (0.9, 0.42, 0.12)), (0.75, (0.30, 0.10, 0.03)), (1.0, (0.05, 0.02, 0.01))])
    hfall = t.math('SMOOTHSTEP', 0.2, 3.6, z)
    warm = t.mix(t.math('MULTIPLY', hfall, 0.5), warm, (1.0, 0.75, 0.42))
    pr = t.principled(Base_Color=(0.02, 0.02, 0.02), Roughness=0.02)
    t.set(pr, 'Specular IOR Level', 1.0)
    t.set(pr, 'Emission Color', warm); t.set(pr, 'Emission Strength', 3.0)
    t.finish(pr)
    m.cycles.emission_sampling = 'NONE'
    return m


def m_emit(name, col, strength, sample=False):
    m, t = _new(name)
    e = t.n('ShaderNodeEmission', {'Color': tuple(col) + (1,), 'Strength': strength})
    t.finish(e)
    m.cycles.emission_sampling = 'AUTO' if sample else 'NONE'
    return m


def _wet(t, p, base_rough=0.55):
    """wetness mask (puddles/damp patches): returns (wet 0..1)"""
    n = t.noise(p, 0.22, 2, 0.6)
    return t.math('SMOOTHSTEP', 0.46, 0.66, n)


def m_setts(name, geo=False):
    """granite setts. geo=True: real stone geometry with per-stone 'rnd'; else brick-texture + bump."""
    m, t = _new(name)
    p = t.pos()
    wet = _wet(t, p)
    grain = t.noise(p, 180.0, 1, 0.7)
    if geo:
        rnd = t.n('ShaderNodeAttribute', attribute_name='rnd').outputs['Fac']
        h = None
        mort = 0.0
    else:
        br = t.n('ShaderNodeTexBrick', {'Vector': t.n('ShaderNodeMapping', {'Vector': p, 'Rotation': (0, 0, 0)}),
                                         'Scale': 1.0, 'Mortar Size': 0.007, 'Mortar Smooth': 0.9,
                                         'Brick Width': 0.118, 'Row Height': 0.112,
                                         'Color1': (0.1, 0.1, 0.1, 1), 'Color2': (0.9, 0.9, 0.9, 1)}, offset=0.5)
        rnd = t.n('ShaderNodeSeparateColor', {0: br.outputs['Color']}).outputs[0]
        mort = br.outputs['Fac']
        h = t.math('SUBTRACT', 1.0, mort)
    c = t.ramp(rnd, [(0.0, (0.11, 0.105, 0.10)), (0.35, (0.17, 0.16, 0.15)), (0.6, (0.21, 0.19, 0.17)),
                     (0.82, (0.25, 0.20, 0.16)), (1.0, (0.30, 0.28, 0.26))])
    c = t.mix(t.math('MULTIPLY', grain, 0.5), c, t.mix(0.5, c, (0.32, 0.30, 0.28)))
    c = t.mix(t.math('MULTIPLY', wet, 0.55), c, t.mix(0.6, c, (0.02, 0.02, 0.02)))
    if not geo:
        c = t.mix(mort, c, (0.035, 0.03, 0.025))
    rough = t.math('SUBTRACT', 0.62, t.math('MULTIPLY', wet, 0.52))
    rough = t.math('ADD', rough, t.math('MULTIPLY', grain, 0.08))
    pr = t.principled(Base_Color=c, Roughness=rough)
    if h is not None:
        t.set(pr, 'Normal', t.bump(h, 0.55, 0.012))
    t.set(pr, 'Specular IOR Level', 0.6)
    t.finish(pr)
    return m


def m_mortar(name):
    m, t = _new(name)
    p = t.pos()
    wet = _wet(t, p)
    n = t.noise(p, 40, 3, 0.7)
    c = t.mix(n, (0.035, 0.03, 0.025), (0.08, 0.07, 0.055))
    pr = t.principled(Base_Color=c, Roughness=t.math('SUBTRACT', 0.8, t.math('MULTIPLY', wet, 0.75)))
    t.finish(pr)
    return m


def m_slabs(name):
    """sidewalk: large grey paving slabs."""
    m, t = _new(name)
    p = t.pos()
    wet = _wet(t, p)
    br = t.n('ShaderNodeTexBrick', {'Vector': p, 'Scale': 1.0, 'Mortar Size': 0.006, 'Mortar Smooth': 0.8,
                                     'Brick Width': 0.6, 'Row Height': 0.4,
                                     'Color1': (0.2, 0.2, 0.2, 1), 'Color2': (0.8, 0.8, 0.8, 1)}, offset=0.5)
    rnd = t.n('ShaderNodeSeparateColor', {0: br.outputs['Color']}).outputs[0]
    c = t.ramp(rnd, [(0.0, (0.20, 0.19, 0.18)), (1.0, (0.33, 0.31, 0.28))])
    g = t.noise(p, 90, 3, 0.7)
    c = t.mix(t.math('MULTIPLY', g, 0.4), c, (0.38, 0.36, 0.33))
    c = t.mix(t.math('MULTIPLY', wet, 0.5), c, (0.04, 0.04, 0.04))
    c = t.mix(br.outputs['Fac'], c, (0.04, 0.035, 0.03))
    nrm = t.bump(t.math('SUBTRACT', 1.0, br.outputs['Fac']), 0.4, 0.008)
    t.finish(t.principled(Base_Color=c, Roughness=t.math('SUBTRACT', 0.7, t.math('MULTIPLY', wet, 0.5)), Normal=nrm))
    return m


def m_leaf(name, ground=False, glow=0.0):
    m, t = _new(name)
    rnd = t.n('ShaderNodeAttribute', attribute_name='rnd').outputs['Fac']
    oi = t.n('ShaderNodeObjectInfo')
    r = t.math('ADD', rnd, t.math('MULTIPLY', t.math('SUBTRACT', oi.outputs['Random'], 0.5), 0.22))
    if ground:
        stops = [(0.0, (0.30, 0.12, 0.03)), (0.3, (0.62, 0.30, 0.04)), (0.6, (0.85, 0.52, 0.05)),
                 (0.85, (0.90, 0.66, 0.10)), (1.0, (0.50, 0.20, 0.04))]
    else:
        stops = [(0.0, (0.30, 0.40, 0.04)), (0.14, (0.62, 0.56, 0.03)), (0.36, (0.90, 0.60, 0.02)),
                 (0.62, (0.95, 0.44, 0.015)), (0.82, (0.82, 0.24, 0.015)), (1.0, (0.40, 0.11, 0.02))]
    c = t.ramp(r, stops)
    g = t.n('ShaderNodeNewGeometry')
    c = t.mix(t.math('MULTIPLY', t.noise(g.outputs['Position'], 25.0, 2, 0.6), 0.35), c, t.mix(0.5, c, (0.35, 0.12, 0.02)))
    dif = t.n('ShaderNodeBsdfDiffuse', {'Color': c})
    tr = t.n('ShaderNodeBsdfTranslucent', {'Color': t.mix(0.25, c, (1.0, 0.75, 0.1))})
    gl = t.n('ShaderNodeBsdfGlossy', {'Color': (1, 1, 1, 1), 'Roughness': 0.32})
    mx = t.n('ShaderNodeMixShader', {0: 0.42 if not ground else 0.15, 1: dif, 2: tr})
    fr = t.n('ShaderNodeFresnel', {'IOR': 1.4})
    mx2 = t.n('ShaderNodeMixShader', {0: t.math('MULTIPLY', fr.outputs[0], 0.6 if not ground else 0.9), 1: mx, 2: gl})
    if glow > 0:
        em = t.n('ShaderNodeEmission', {'Color': c, 'Strength': glow})
        mx2 = t.n('ShaderNodeAddShader', {0: mx2, 1: em})
        m.cycles.emission_sampling = 'NONE'
    t.finish(mx2)
    return m


def m_bark(name):
    """plane-tree bark: mottled cream / olive / grey-brown flakes."""
    m, t = _new(name)
    p = t.n('ShaderNodeTexCoord').outputs['Object']
    pv = t.n('ShaderNodeMapping', {'Vector': p, 'Scale': (1.0, 1.0, 0.45)})
    v = t.n('ShaderNodeTexVoronoi', {'Vector': pv, 'Scale': 6.5, 'Randomness': 1.0}, feature='F1')
    cellc = t.n('ShaderNodeSeparateColor', {0: v.outputs['Color']}).outputs[0]
    n = t.noise(pv, 3.0, 4, 0.6)
    k = t.math('ADD', t.math('MULTIPLY', cellc, 0.6), t.math('MULTIPLY', n, 0.5))
    c = t.ramp(k, [(0.0, (0.10, 0.075, 0.05)), (0.38, (0.20, 0.16, 0.10)), (0.5, (0.34, 0.33, 0.20)),
                   (0.66, (0.55, 0.50, 0.36)), (1.0, (0.70, 0.66, 0.52))], 'CONSTANT')
    fine = t.noise(p, 50, 3, 0.7)
    c = t.mix(t.math('MULTIPLY', fine, 0.3), c, (0.1, 0.08, 0.06))
    nrm = t.bump(t.math('ADD', k, t.math('MULTIPLY', fine, 0.3)), 0.5, 0.02)
    t.finish(t.principled(Base_Color=c, Roughness=0.8, Normal=nrm))
    return m


def m_awning(name, key):
    m, t = _new(name)
    col = PAL[key]
    uv, z = t.facade_uv()
    sx = t.n('ShaderNodeSeparateXYZ', {0: uv})
    stripe = t.math('GREATER_THAN', t.math('PINGPONG', sx.outputs[0], 0.22), 0.11)
    c = t.mix(stripe, col, PAL['canvas']) if key in ('burgundy', 'green', 'navy') and name.endswith('s') else col
    dif = t.n('ShaderNodeBsdfDiffuse', {'Color': c if isinstance(c, bpy.types.NodeSocket) else tuple(c) + (1,)})
    tr = t.n('ShaderNodeBsdfTranslucent', {'Color': c if isinstance(c, bpy.types.NodeSocket) else tuple(c) + (1,)})
    t.finish(t.n('ShaderNodeMixShader', {0: 0.25, 1: dif, 2: tr}))
    return m


def m_water(name):
    m, t = _new(name)
    p = t.pos()
    w1 = t.noise(t.n('ShaderNodeMapping', {'Vector': p, 'Scale': (0.05, 0.12, 1.0)}), 1.0, 5, 0.65)
    w2 = t.noise(p, 0.6, 3, 0.6)
    nrm = t.bump(t.math('ADD', w1, t.math('MULTIPLY', w2, 0.25)), 0.55, 1.0)
    pr = t.principled(Base_Color=(0.012, 0.045, 0.07), Roughness=0.13, Normal=nrm)
    t.set(pr, 'Specular IOR Level', 1.0)
    t.finish(pr)
    return m


def m_windows_tex(name, key):
    """cheap background-city wall: stucco colour with procedural window grid."""
    m, t = _new(name)
    col = PAL[key]
    uv, z = t.facade_uv()
    s = t.n('ShaderNodeSeparateXYZ', {0: uv})
    fx = t.math('FRACT', t.math('DIVIDE', s.outputs[0], 3.0))
    fz = t.math('FRACT', t.math('DIVIDE', t.math('SUBTRACT', s.outputs[1], 0.6), 4.0))
    wx = t.math('MULTIPLY', t.math('GREATER_THAN', fx, 0.32), t.math('LESS_THAN', fx, 0.68))
    wz = t.math('MULTIPLY', t.math('GREATER_THAN', fz, 0.22), t.math('LESS_THAN', fz, 0.78))
    win = t.math('MULTIPLY', wx, wz)
    n = t.noise(t.pos(), 0.3, 3, 0.6)
    col = tuple(x * 0.78 for x in col)
    c = t.mix(t.math('MULTIPLY', n, 0.6), col, tuple(x * 0.6 for x in col))
    c = t.mix(win, c, (0.03, 0.04, 0.05))
    rough = t.math('SUBTRACT', 0.85, t.math('MULTIPLY', win, 0.8))
    t.finish(t.principled(Base_Color=c, Roughness=rough))
    return m


def m_blob(name):
    """distant tree canopy (courtyards, other streets): noisy golden foliage."""
    m, t = _new(name)
    p = t.pos()
    oi = t.n('ShaderNodeObjectInfo')
    n = t.noise(p, 1.6, 4, 0.7)
    n2 = t.noise(p, 0.12, 2, 0.5)
    k = t.math('ADD', t.math('MULTIPLY', n, 0.6), t.math('MULTIPLY', n2, 0.5))
    c = t.ramp(k, [(0.25, (0.20, 0.22, 0.04)), (0.45, (0.55, 0.40, 0.04)), (0.6, (0.80, 0.50, 0.04)),
                   (0.8, (0.70, 0.30, 0.03))])
    nrm = t.bump(t.noise(p, 3.5, 4, 0.8), 1.0, 0.6)
    dif = t.n('ShaderNodeBsdfDiffuse', {'Color': c, 'Normal': nrm})
    tr = t.n('ShaderNodeBsdfTranslucent', {'Color': c, 'Normal': nrm})
    t.finish(t.n('ShaderNodeMixShader', {0: 0.3, 1: dif, 2: tr}))
    return m


def get_mat(name):
    if name in _cache:
        return _cache[name]
    typ, _, key = name.partition(':')
    if typ == 'stucco': m = m_stucco(name, key)
    elif typ == 'rustic': m = m_stucco(name, key, rustic=True)
    elif typ == 'trim': m = m_stucco(name, key)
    elif typ == 'roof': m = m_roof(name, 'roof_' + key)
    elif typ == 'glass': m = m_glass(name, lit={'dark': 0.0, 'lit': 3.0, 'dim': 1.0}[key])
    elif typ == 'shopglass': m = m_shopglass(name)
    elif typ == 'iron': m = m_flat(name, 'black', rough=0.38, metal=0.8)
    elif typ == 'paint': m = m_flat(name, key, rough=0.45)
    elif typ == 'metal': m = m_flat(name, key, rough=0.3, metal=1.0)
    elif typ == 'awning': m = m_awning(name, key[:-2] if key.endswith('_s') else key)
    elif typ == 'setts': m = m_setts(name, geo=(key == 'geo'))
    elif typ == 'mortar': m = m_mortar(name)
    elif typ == 'slabs': m = m_slabs(name)
    elif typ == 'leaf': m = m_leaf(name, ground=(key == 'ground'), glow=(0.55 if key == 'fall' else 0.0))
    elif typ == 'bark': m = m_bark(name)
    elif typ == 'bulb': m = m_emit(name, (1.0, 0.60, 0.22), 26.0)
    elif typ == 'lamp': m = m_emit(name, (1.0, 0.66, 0.30), 14.0)
    elif typ == 'water': m = m_water(name)
    elif typ == 'wintex': m = m_windows_tex(name, key)
    elif typ == 'blob': m = m_blob(name)
    else: raise KeyError(name)
    _cache[name] = m
    return m

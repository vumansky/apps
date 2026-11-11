"""Sky, sun and render settings."""
import bpy, math
import numpy as np

from .world_const import SUN_AZ_OFF, SUN_EL, SUN_DIR


def setup_world(scene):
    w = bpy.data.worlds.new("Sky"); scene.world = w
    w.use_nodes = True
    t = w.node_tree; t.nodes.clear()
    N = t.nodes.new; L = t.links.new
    out = N('ShaderNodeOutputWorld')
    sky = N('ShaderNodeTexSky')
    sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_disc = False
    sky.sun_elevation = SUN_EL
    sky.sun_rotation = -SUN_AZ_OFF + math.pi  # tuned in test renders
    sky.air_density = 1.0; sky.aerosol_density = 2.2; sky.ozone_density = 1.5
    # high cirrus lit pink-gold: noise on a projected sky plane
    tc = N('ShaderNodeTexCoord')
    sep = N('ShaderNodeSeparateXYZ'); L(tc.outputs['Generated'], sep.inputs[0])
    zc = N('ShaderNodeMath'); zc.operation = 'MAXIMUM'; L(sep.outputs[2], zc.inputs[0]); zc.inputs[1].default_value = 0.07
    dx = N('ShaderNodeMath'); dx.operation = 'DIVIDE'; L(sep.outputs[0], dx.inputs[0]); L(zc.outputs[0], dx.inputs[1])
    dy = N('ShaderNodeMath'); dy.operation = 'DIVIDE'; L(sep.outputs[1], dy.inputs[0]); L(zc.outputs[0], dy.inputs[1])
    cv = N('ShaderNodeCombineXYZ'); L(dx.outputs[0], cv.inputs[0]); L(dy.outputs[0], cv.inputs[1])
    mp = N('ShaderNodeMapping'); L(cv.outputs[0], mp.inputs['Vector']); mp.inputs['Scale'].default_value = (0.55, 0.30, 1.0)
    mp.inputs['Rotation'].default_value = (0, 0, 1.1)
    nz = N('ShaderNodeTexNoise'); L(mp.outputs[0], nz.inputs['Vector'])
    nz.inputs['Scale'].default_value = 1.7; nz.inputs['Detail'].default_value = 8; nz.inputs['Roughness'].default_value = 0.62
    nz.inputs['Distortion'].default_value = 0.6
    cr = N('ShaderNodeValToRGB'); L(nz.outputs[0], cr.inputs[0])
    cr.color_ramp.elements[0].position = 0.54; cr.color_ramp.elements[0].color = (0, 0, 0, 1)
    cr.color_ramp.elements[1].position = 0.74; cr.color_ramp.elements[1].color = (1, 1, 1, 1)
    # fade clouds near horizon/zenith a little
    hz = N('ShaderNodeMapRange'); L(sep.outputs[2], hz.inputs[0]); hz.inputs[1].default_value = 0.02; hz.inputs[2].default_value = 0.16
    cm = N('ShaderNodeMath'); cm.operation = 'MULTIPLY'; L(cr.outputs[0], cm.inputs[0]); L(hz.outputs[0], cm.inputs[1])
    # cloud colour: warm near the sun, cooler away
    sd = N('ShaderNodeVectorMath'); sd.operation = 'DOT_PRODUCT'; L(tc.outputs['Generated'], sd.inputs[0]); sd.inputs[1].default_value = tuple(SUN_DIR)
    cc = N('ShaderNodeValToRGB'); L(sd.outputs['Value'], cc.inputs[0])
    cc.color_ramp.elements[0].position = 0.0; cc.color_ramp.elements[0].color = (0.50, 0.36, 0.42, 1)
    cc.color_ramp.elements[1].position = 1.0; cc.color_ramp.elements[1].color = (3.2, 1.55, 0.62, 1)
    e2 = cc.color_ramp.elements.new(0.75); e2.color = (1.5, 0.75, 0.50, 1)
    mix = N('ShaderNodeMix'); mix.data_type = 'RGBA'
    L(cm.outputs[0], mix.inputs[0]); L(sky.outputs[0], mix.inputs[6]); L(cc.outputs[0], mix.inputs[7])
    # visible sun disc + aureole (camera only)
    sun_c = N('ShaderNodeMapRange'); L(sd.outputs['Value'], sun_c.inputs[0])
    sun_c.inputs[1].default_value = 0.99990; sun_c.inputs[2].default_value = 0.99996
    aur = N('ShaderNodeMath'); aur.operation = 'POWER'; aur.use_clamp = True
    mx0 = N('ShaderNodeMath'); mx0.operation = 'MAXIMUM'; L(sd.outputs['Value'], mx0.inputs[0]); mx0.inputs[1].default_value = 0.0
    L(mx0.outputs[0], aur.inputs[0]); aur.inputs[1].default_value = 500.0
    sm = N('ShaderNodeMath'); sm.operation = 'MULTIPLY'; L(sun_c.outputs[0], sm.inputs[0]); sm.inputs[1].default_value = 600.0
    am = N('ShaderNodeMath'); am.operation = 'MULTIPLY'; L(aur.outputs[0], am.inputs[0]); am.inputs[1].default_value = 9.0
    sa = N('ShaderNodeMath'); sa.operation = 'ADD'; L(sm.outputs[0], sa.inputs[0]); L(am.outputs[0], sa.inputs[1])
    lp = N('ShaderNodeLightPath')
    sc = N('ShaderNodeMath'); sc.operation = 'MULTIPLY'; L(sa.outputs[0], sc.inputs[0]); L(lp.outputs['Is Camera Ray'], sc.inputs[1])
    sunem = N('ShaderNodeEmission'); sunem.inputs['Color'].default_value = (1.0, 0.62, 0.30, 1); L(sc.outputs[0], sunem.inputs['Strength'])
    bg = N('ShaderNodeBackground'); L(mix.outputs[2], bg.inputs['Color']); bg.inputs['Strength'].default_value = 0.25
    add = N('ShaderNodeAddShader'); L(bg.outputs[0], add.inputs[0]); L(sunem.outputs[0], add.inputs[1])
    L(add.outputs[0], out.inputs['Surface'])

    sun = bpy.data.lights.new("Sun", 'SUN')
    sun.energy = 9.0
    sun.color = (1.0, 0.56, 0.26)
    sun.angle = math.radians(1.6)
    ob = bpy.data.objects.new("Sun", sun); scene.collection.objects.link(ob)
    # sun lamp shines along -Z local; point -Z toward -SUN_DIR
    from mathutils import Vector
    ob.rotation_euler = Vector(tuple(SUN_DIR)).to_track_quat('Z', 'Y').to_euler()
    return sky


def setup_render(scene, w=1280, h=720, spp=48):
    r = scene.render
    r.engine = 'CYCLES'
    r.resolution_x, r.resolution_y, r.resolution_percentage = w, h, 100
    c = scene.cycles
    c.device = 'CPU'
    c.samples = spp
    c.use_adaptive_sampling = False
    c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'
    try:
        c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'; c.denoising_prefilter = 'FAST'
    except Exception: pass
    c.max_bounces = 3; c.diffuse_bounces = 1; c.glossy_bounces = 2; c.transmission_bounces = 2
    c.transparent_max_bounces = 4; c.volume_bounces = 0
    c.caustics_reflective = False; c.caustics_refractive = False
    c.sample_clamp_indirect = 6.0; c.sample_clamp_direct = 0.0
    c.blur_glossy = 0.6
    c.use_light_tree = True
    r.use_persistent_data = True
    r.threads_mode = 'AUTO'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'None'
    r.film_transparent = False
    try:
        c.pixel_filter_type = 'BLACKMAN_HARRIS'
    except Exception: pass

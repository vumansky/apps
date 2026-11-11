"""Render frames of the Deribasivska shot with Cycles.
usage: python render.py -- --range 1 480 --res 1280 720 --spp 24 --out out/exr [--png] [--step 1]"""
import sys, os, time
import bpy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dz import cam, street, world

a = sys.argv[sys.argv.index('--') + 1:]
def opt(name, n=1, default=None):
    if name in a:
        i = a.index(name); return a[i + 1:i + 1 + n] if n > 1 else a[i + 1]
    return default
blend = opt('--blend', default=os.path.join(HERE, 'out', 'scene.blend'))
res = [int(v) for v in opt('--res', 2, ['1280', '720'])]
spp = int(opt('--spp', default='24'))
out = opt('--out', default=os.path.join(HERE, 'out', 'exr'))
png = '--png' in a
if '--frames' in a:
    frames = [int(v) for v in opt('--frames').split(',')]
else:
    r = [int(v) for v in opt('--range', 2, ['1', str(cam.NFRAMES)])]
    frames = list(range(r[0], r[1] + 1, int(opt('--step', default='1'))))
os.makedirs(out, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
world.setup_render(sc, res[0], res[1], spp)
sc.render.use_motion_blur = '--nomb' not in a
sc.render.motion_blur_shutter = 0.35
if png:
    sc.view_settings.exposure = float(opt('--exposure', default='0'))
s = sc.render.image_settings
if png:
    s.file_format = 'PNG'
else:
    s.file_format = 'OPEN_EXR'; s.color_depth = '16'; s.exr_codec = 'ZIP'; s.color_mode = 'RGB'
# depth comes from a second 1-sample pass with an override material that emits camera distance
dm = bpy.data.materials.new('DepthOverride'); dm.use_nodes = True
nt = dm.node_tree; nt.nodes.clear()
cd_ = nt.nodes.new('ShaderNodeCameraData'); em = nt.nodes.new('ShaderNodeEmission'); om = nt.nodes.new('ShaderNodeOutputMaterial')
nt.links.new(cd_.outputs['View Z Depth'], em.inputs['Strength']); nt.links.new(em.outputs[0], om.inputs[0])
dm.cycles.emission_sampling = 'NONE'   # otherwise every triangle in the city becomes a light
farw = bpy.data.worlds.new('Far'); farw.use_nodes = True
farw.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0e5
main_world = sc.world
vl = sc.view_layers[0]
DEPTH = '--depth' in a
if DEPTH:
    for me_ in bpy.data.meshes:
        for i_ in range(len(me_.materials)): me_.materials[i_] = dm
    sc.world = farw
    sc.cycles.samples = 1; sc.cycles.use_denoising = False; sc.render.use_motion_blur = False
    s.color_depth = '32'; s.color_mode = 'BW'
co = sc.camera
fl = street.FallingLeaves(obj=bpy.data.objects['FallingLeaves'])
ext = 'png' if png else 'exr'
for f in frames:
    fp = os.path.join(out, '%s%04d.%s' % ('d' if DEPTH else 'f', f, ext))
    if os.path.exists(fp) and os.path.getsize(fp) > 1000:
        continue
    t0 = time.time()
    t = (f - 1) / cam.FPS
    sc.frame_set(f)
    st_ = cam.state(t)
    co.data.lens = st_['lens']; co.data.dof.use_dof = not DEPTH
    co.data.dof.focus_distance = st_['focus']; co.data.dof.aperture_fstop = st_['fstop']
    fl.update(t, st_['pos'])
    sc.render.filepath = fp + '.tmp.' + ext
    bpy.ops.render.render(write_still=True)
    os.replace(sc.render.filepath, fp)
    print('FRAME %d done in %.1fs' % (f, time.time() - t0), flush=True)
print('ALLDONE', flush=True)

"""One continuous camera move: from the wet cobbles, down the golden tunnel, up through the canopy to the sea."""
import numpy as np
from scipy.interpolate import PchipInterpolator, CubicSpline

FPS = 24
DUR = 20.0
NFRAMES = int(FPS * DUR)

#        t     x      y      z     yaw   pitch  lens  focus  fstop
KEYS = [(0.0,  1.7,  -4.0,  0.24, -5.0,  5.0,  30.0, 1.2,   1.6),
        (3.0,  1.3,   2.6,  0.50, -3.0,  8.0,  28.0, 3.5,   2.0),
        (5.4,  0.2,  14.0,  1.75,  2.0,  7.0,  24.0, 14.0,  2.8),
        (7.8, -1.6,  33.0,  3.2,  17.0, 12.0,  22.0, 22.0,  4.0),
        (9.6, -1.2,  54.0,  6.0,   6.0,  9.0,  22.0, 60.0,  5.6),
        (11.4, -0.6, 80.0, 12.0,  -4.0,  2.0,  22.0, 150.0, 8.0),
        (13.2, -1.0, 106.0, 23.5, -7.0, -5.0,  22.0, 300.0, 11.0),
        (15.5, -1.8, 134.0, 34.0, -8.0, -8.0,  23.0, 500.0, 11.0),
        (20.0, -3.5, 168.0, 46.0, -8.5, -9.0,  25.0, 500.0, 11.0)]
_K = np.array(KEYS)
_T = _K[:, 0]
_sp = {i: PchipInterpolator(_T, _K[:, i]) for i in (3, 6, 7, 8)}
_sp.update({i: CubicSpline(_T, _K[:, i], bc_type='clamped') for i in (1, 4, 5)})
_sp[2] = PchipInterpolator(_T, _K[:, 2])


def state(t):
    t = float(np.clip(t, 0, DUR))
    x, y, z, yaw, pitch, lens, focus, fst = (float(_sp[i](t)) for i in range(1, 9))
    # gentle handheld-free "breathing" drift so the move feels alive but stable
    x += 0.035 * np.sin(t * 0.9); z += 0.012 * np.sin(t * 1.3 + 1.0) * min(1.0, z)
    yaw += 0.25 * np.sin(t * 0.7 + 0.5); roll = 0.5 * np.sin(t * 0.45 + 2.0)
    return dict(pos=(x, y, z), yaw=yaw, pitch=pitch, roll=roll, lens=lens, focus=focus, fstop=fst)


def apply(cam_obj, t):
    import math
    from mathutils import Euler, Matrix
    s = state(t)
    cam_obj.location = s['pos']
    # camera looks along -Z; build rotation: yaw about Z (0 = +Y), pitch up, roll
    rz = Matrix.Rotation(-math.radians(s['yaw']), 4, 'Z')
    rx = Matrix.Rotation(math.radians(90 + s['pitch']), 4, 'X')
    rr = Matrix.Rotation(math.radians(s['roll']), 4, 'Z')
    cam_obj.rotation_euler = (rz @ rx @ rr).to_euler()
    c = cam_obj.data
    c.lens = s['lens']
    c.dof.use_dof = True
    c.dof.focus_distance = s['focus']
    c.dof.aperture_fstop = s['fstop']
    return s

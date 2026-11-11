"""Post pipeline: linear EXR + depth -> temporal stabilisation -> haze, sun shafts, bloom -> filmic grade -> 1080p frames."""
import os, sys, math
import numpy as np
import OpenEXR, Imath
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dz import cam
from dz.world_const import SUN_DIR

FLOAT = Imath.PixelType(Imath.PixelType.FLOAT)
PATCH = (118, 236)


def read_exr(path, chans):
    f = OpenEXR.InputFile(path)
    dw = f.header()['dataWindow']; w, h = dw.max.x - dw.min.x + 1, dw.max.y - dw.min.y + 1
    out = np.stack([np.frombuffer(f.channel(c, FLOAT), np.float32).reshape(h, w) for c in chans], -1)
    f.close()
    return out


def load(dirn, fr):
    rgb = read_exr(os.path.join(dirn, 'f%04d.exr' % fr), 'RGB')
    # patch pass: re-rendered frames (yellow hero facade) cross-faded in over the main render
    pp = os.path.join(dirn + '_hero', 'f%04d.exr' % fr)
    if os.path.exists(pp):
        w = float(np.clip(min(fr - PATCH[0], PATCH[1] - fr) / 10.0, 0, 1))
        if w > 0: rgb = rgb * (1 - w) + read_exr(pp, 'RGB') * w
    d = read_exr(os.path.join(dirn, 'd%04d.exr' % fr), 'V')[..., 0]
    return np.nan_to_num(rgb, posinf=50.0, neginf=0.0).clip(0, 200), d


def cam_basis(t):
    """camera position, rotation matrix (columns: right, up, back) and tan(half fov x)."""
    s = cam.state(t)
    yaw, pitch, roll = (math.radians(s[k]) for k in ('yaw', 'pitch', 'roll'))
    def rz(a): return np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
    def rx(a): return np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    R = rz(-yaw) @ rx(math.pi / 2 + pitch) @ rz(roll)
    return np.array(s['pos']), R, 18.0 / s['lens']


def view_dirs(R, thx, h, w):
    xs = (np.arange(w) + 0.5) / w * 2 - 1; ys = 1 - (np.arange(h) + 0.5) / h * 2
    X, Y = np.meshgrid(xs * thx, ys * thx * h / w)
    dc = np.stack([X, Y, -np.ones_like(X)], -1)          # camera space, z depth = 1
    return dc @ R.T                                       # world dirs (not normalised; scale by z-depth)


def project(P, pos, R, thx, h, w):
    pc = (P - pos) @ R
    z = -pc[..., 2]
    u = (pc[..., 0] / np.maximum(z, 1e-6) / thx * 0.5 + 0.5) * w - 0.5
    v = (0.5 - pc[..., 1] / np.maximum(z, 1e-6) / (thx * h / w) * 0.5) * h - 0.5
    return u, v, z


def gauss(img, s):
    return ndi.gaussian_filter(img, (s, s, 0)[:img.ndim], mode='nearest')


def lum(x):
    return x @ np.array([0.2126, 0.7152, 0.0722], np.float32)


class Temporal:
    """depth-reprojected temporal accumulation (static world): cuts noise/flicker of low-sample renders."""
    def __init__(self, alpha=0.62):
        self.hist = None; self.prev = None; self.alpha = alpha

    def __call__(self, rgb, d, t):
        h, w = d.shape
        pos, R, thx = cam_basis(t)
        if self.hist is not None:
            ppos, pR, pthx, pd = self.prev
            P = pos + view_dirs(R, thx, h, w) * np.minimum(d, 4e4)[..., None]
            u, v, z = project(P, ppos, pR, pthx, h, w)
            ok = (u > 0) & (u < w - 1) & (v > 0) & (v < h - 1) & (z > 0)
            co = np.stack([v, u])
            hrgb = np.stack([ndi.map_coordinates(self.hist[..., c], co, order=1, mode='nearest') for c in range(3)], -1)
            hz = ndi.map_coordinates(pd, co, order=1, mode='nearest')
            sky = d > 3e4
            ok &= (np.abs(hz - z) < 0.04 * z + 0.05) | (sky & (hz > 3e4))
            # neighbourhood clamp (in a compressed space) to stop ghosting from reflections / disocclusion
            c = rgb / (1 + lum(rgb))[..., None]
            hc = hrgb / (1 + lum(hrgb))[..., None]
            mn = ndi.minimum_filter(c, size=(3, 3, 1)); mx = ndi.maximum_filter(c, size=(3, 3, 1))
            m = gauss(c, 1.0); pad = 0.5 * (mx - mn) + 0.01
            hc = np.clip(hc, np.minimum(mn, m - pad), np.maximum(mx, m + pad))
            a = np.where(ok, self.alpha, 0.0)[..., None]
            oc = c * (1 - a) + hc * a
            rgb = oc / np.maximum(1 - lum(oc), 1e-3)[..., None]
        self.hist = rgb; self.prev = (pos, R, thx, d)
        return rgb


def atmosphere(rgb, d, t, strength=1.0):
    """warm morning haze by distance + height, forward-scatter glow toward the sun."""
    h, w = d.shape
    pos, R, thx = cam_basis(t)
    D = view_dirs(R, thx, h, w)
    dist = d * np.linalg.norm(D, axis=-1)
    dn = D / np.linalg.norm(D, axis=-1, keepdims=True)
    cs = np.clip(dn @ SUN_DIR, 0, 1)
    sky = d > 3e4
    zmid = pos[2] + dn[..., 2] * np.minimum(dist, 3000) * 0.5
    dens = np.exp(-np.clip(zmid + 40, 0, None) / 110.0)             # thicker low down (over the port and the sea)
    tau = np.minimum(dist, 12000) / 950.0 * dens * strength
    fog = 1 - np.exp(-tau)
    fog_sky = np.exp(-np.clip(dn[..., 2], 0, None) * 26.0) * 0.92          # horizon band of the sky melts into the haze
    fog = np.where(sky, fog_sky, fog)
    base = np.array([0.150, 0.118, 0.105], np.float32)              # cool-pink haze, in scene radiance units
    glow = np.array([1.05, 0.50, 0.17], np.float32)
    fc = base[None, None] * (0.65 + 0.35 * cs[..., None]) + glow[None, None] * (cs[..., None] ** 10) * 0.9 + glow[None, None] * (cs[..., None] ** 80) * 1.6
    return rgb * (1 - fog[..., None]) + fc * fog[..., None], sky, cs, (pos, R, thx)


def sun_shafts(rgb, sky, cs, camb, strength=0.55):
    """screen-space light shafts: bright sky seen through the canopy is smeared away from the sun."""
    h, w = sky.shape
    pos, R, thx = camb
    sc = SUN_DIR @ R
    if -sc[2] <= 0.05:
        return rgb
    su = (sc[0] / -sc[2] / thx * 0.5 + 0.5) * w; sv = (0.5 - sc[1] / -sc[2] / (thx * h / w) * 0.5) * h
    k = 4
    src = np.where(sky[..., None], np.minimum(rgb, 6.0), 0.0) * (cs[..., None] ** 6)
    src = ndi.zoom(src, (1 / k, 1 / k, 1), order=1)
    hh, ww = src.shape[:2]
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    acc = np.zeros_like(src); N = 40
    for i in range(N):
        f = 1 - 0.75 * i / N
        co = np.stack([sv / k + (yy - sv / k) * f, su / k + (xx - su / k) * f])
        wgt = (1 - i / N) ** 1.5
        for c in range(3):
            acc[..., c] += wgt * ndi.map_coordinates(src[..., c], co, order=1, mode='constant')
    acc /= N * 0.4
    acc = gauss(acc, 1.2)
    acc = ndi.zoom(acc, (h / hh, w / ww, 1), order=1)[:h, :w]
    return rgb + acc * strength


def bloom(rgb, thr=1.6, amt=0.22):
    hi = np.maximum(rgb - thr, 0)
    hi = hi / (1 + lum(hi)[..., None] * 0.08)
    small = ndi.zoom(hi, (0.25, 0.25, 1), order=1)
    acc = np.zeros_like(small)
    for s, wg in ((1.5, 0.45), (5, 0.3), (14, 0.25)):
        acc += wg * gauss(small, s)
    h, w = rgb.shape[:2]
    acc = ndi.zoom(acc, (h / small.shape[0], w / small.shape[1], 1), order=1)[:h, :w]
    # slight anamorphic streak on the very brightest points
    st = ndi.gaussian_filter(small * (lum(small) > 4)[..., None], (0.6, 22, 0), mode='nearest')
    st = ndi.zoom(st, (h / small.shape[0], w / small.shape[1], 1), order=1)[:h, :w]
    return rgb + acc * amt + st * amt * 0.6 * np.array([1.0, 0.75, 0.55], np.float32)


def tonemap(x):
    """filmic curve (Hable-style) with highlight desaturation -> display-linear 0..1"""
    l = lum(x)[..., None]
    x = l + (x - l) * (1.0 / (1.0 + 0.045 * l))            # ease saturation in the brightest areas
    A, B, C, D_, E, F = 0.22, 0.30, 0.10, 0.20, 0.01, 0.30
    def f(v): return (v * (A * v + C * B) + D_ * E) / (v * (A * v + B) + D_ * F) - E / F
    return np.clip(f(x * 1.9) / f(np.float32(11.2)), 0, 1)


def grade(y, t, h, w):
    """display-referred look: contrast, warm highlights / teal shadows, saturation, vignette."""
    y = np.power(np.clip(y, 0, 1), 1 / 2.2)
    l = lum(y)[..., None]
    y = l + (y - l) * 1.22                                              # saturation
    y = np.clip(y, 0, 1)
    y = y + 0.11 * (y - 0.5) * (1 - np.abs(2 * y - 1))                  # gentle S-curve
    sh = (1 - l) ** 3; hi = l ** 2
    y = y + sh * np.array([-0.012, 0.004, 0.022], np.float32) + hi * np.array([0.022, 0.008, -0.022], np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    r2 = ((xx / w - 0.5) ** 2 * 1.0 + (yy / h - 0.5) ** 2 * 1.25)
    y = y * (1 - 0.55 * r2 ** 1.3)[..., None]
    return np.clip(y, 0, 1)


def exposure_curve(dirn, frames):
    """auto exposure from log-average luminance, smoothed over time."""
    ev = []
    for fr in frames:
        rgb, d = load(dirn, fr)
        L = lum(rgb[::4, ::4])
        Lc = L[L.shape[0] // 5:, :]                                    # weight the lower/centre part (not open sky)
        ev.append(np.exp(np.mean(np.log(Lc + 0.004))))
    ev = np.array(ev)
    target = 0.115 / ev
    target = np.clip(target, 0.42, 6.0)
    sm = ndi.gaussian_filter1d(np.log(target), 14, mode='nearest') if len(frames) > 30 else np.log(target)
    return dict(zip(frames, np.exp(sm)))


def process(rgb, d, t, expo, taa=None, shafts=0.55):
    if taa is not None:
        rgb = taa(rgb, d, t)
    h, w = d.shape
    x, sky, cs, camb = atmosphere(rgb, d, t)
    x = sun_shafts(x, sky, cs, camb, strength=shafts)
    x = x * expo
    x = bloom(x)
    return grade(tonemap(x), t, h, w)


if __name__ == '__main__':
    from PIL import Image
    dirn = sys.argv[1]; frames = [int(v) for v in sys.argv[2].split(',')]
    ex = exposure_curve(dirn, frames)
    ims = []
    for fr in frames:
        rgb, d = load(dirn, fr)
        y = process(rgb, d, (fr - 1) / cam.FPS, ex[fr])
        print(fr, 'expo %.2f' % ex[fr], 'mean', y.mean().round(3), 'skyraw', np.median(rgb[d > 3e4], axis=0).round(2) if (d > 3e4).any() else '-')
        ims.append(Image.fromarray((y * 255 + 0.5).astype(np.uint8)))
    w, h = ims[0].size; cols = 2 if len(ims) <= 6 else 3
    sheet = Image.new('RGB', (w * cols, h * ((len(ims) + cols - 1) // cols)))
    for i, im in enumerate(ims): sheet.paste(im, ((i % cols) * w, (i // cols) * h))
    sheet.save(sys.argv[3], quality=90)

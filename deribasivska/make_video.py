"""Assemble the film: EXR frames -> post (post.py) -> 1080p -> titles -> H.264 + AAC MP4.
usage: python make_video.py out/exr out/deribasivska_autumn.mp4 [--frames a b] [--music out/music.wav] [--still N out.png]"""
import os, sys, subprocess, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import post
from dz import cam

W, H = 1920, 1080
CH_I = '/usr/share/fonts/X11/Type1/c0648bt_.pfb'


def find_font(cands, size):
    for c in cands:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    return ImageFont.load_default(size)

INTER_L = ['/usr/share/fonts/truetype/inter/InterDisplay-Light.ttf', '/usr/share/fonts/opentype/inter/InterDisplay-Light.otf',
           '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
INTER_M = ['/usr/share/fonts/truetype/inter/InterDisplay-Medium.ttf', '/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf',
           '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
SERIF_I = ['/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf', '/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf']


def tracked(text, font, tracking):
    """render letter-spaced text to an L image (alpha)."""
    ws = [font.getbbox(c)[2] for c in text]
    asc, desc = font.getmetrics()
    w = int(sum(ws) + tracking * (len(text) - 1)) + 8; h = asc + desc + 8
    im = Image.new('L', (w, h), 0); d = ImageDraw.Draw(im)
    x = 4
    for c, cw in zip(text, ws):
        d.text((x, 4), c, font=font, fill=255); x += cw + tracking
    return im


def smooth(a, b, t):
    x = np.clip((t - a) / (b - a), 0, 1); return x * x * (3 - 2 * x)


class Titles:
    def __init__(self):
        self.title = tracked('DERIBASIVSKA', find_font(INTER_L, 132), 34)
        self.sub = tracked('ODESA  ·  UKRAINE', find_font(INTER_M, 34), 17)
        self.tag = tracked('Autumn is golden here.', find_font(SERIF_I, 58), 1)
        self.open1 = tracked('ODESA', find_font(INTER_M, 30), 16)
        self.open2 = tracked('a November morning', find_font(SERIF_I, 40), 1)

    def layer(self, t):
        """returns (alpha L image, shadow L image) for time t, or None."""
        items = []
        # opening lower-third
        a = float(smooth(0.7, 1.6, t) * (1 - smooth(3.6, 4.5, t)))
        if a > 0.003:
            items.append((self.open1, (150, 880), a, 0))
            items.append((self.open2, (148, 922), a * 0.95, 0))
        # end title: letters drift apart slightly as they fade in
        a1 = float(smooth(14.9, 16.4, t)); a2 = float(smooth(15.9, 17.1, t)); a3 = float(smooth(16.6, 17.8, t))
        out = 1 - float(smooth(19.5, 20.0, t)) * 0.0
        if a1 > 0.003:
            dy = int((1 - a1) * 14)
            items.append((self.tag, ((W - self.tag.width) // 2, 356 + dy), a3 * out, 0))
            items.append((self.title, ((W - self.title.width) // 2, 430 + dy), a1 * out, 1))
            items.append((self.sub, ((W - self.sub.width) // 2, 606 + dy), a2 * out, 0))
        if not items:
            return None
        al = Image.new('L', (W, H), 0)
        for im, (x, y), a, _ in items:
            al.paste(Image.eval(im, lambda v, a=a: int(v * a)), (x, y), im)
        rule_a = float(smooth(16.2, 17.4, t))
        if rule_a > 0:
            d = ImageDraw.Draw(al); hw = int(170 * rule_a)
            d.line([(W // 2 - hw, 590), (W // 2 + hw, 590)], fill=int(200 * rule_a), width=2)
        sh = al.filter(ImageFilter.GaussianBlur(14))
        return np.asarray(al, np.float32) / 255, np.asarray(sh, np.float32) / 255


def upscale(y):
    """float (h,w,3) 0..1 -> 1080p with Lanczos, then unsharp mask."""
    chans = [np.asarray(Image.fromarray(y[..., c].astype(np.float32), 'F').resize((W, H), Image.LANCZOS)) for c in range(3)]
    z = np.stack(chans, -1)
    blur = ndi.gaussian_filter(z, (1.1, 1.1, 0))
    return np.clip(z + 0.55 * (z - blur), 0, 1)


def finish(y, t, titles, fr):
    z = upscale(y)
    lay = titles.layer(t)
    if lay is not None:
        al, sh = lay
        z = z * (1 - 0.55 * sh[..., None])                                 # soft shadow so type holds on a bright sky
        z = z * (1 - al[..., None]) + np.array([1.0, 0.965, 0.90], np.float32) * al[..., None]
    g = np.random.default_rng(fr).normal(size=(H, W, 1)).astype(np.float32)
    l = post.lum(z)[..., None]
    z = z + g * 0.010 * (0.35 + (1 - l))                                    # film grain, stronger in the shadows
    fade = float(smooth(0.0, 0.55, t)) * (1 - float(smooth(19.35, 20.0, t)))
    z = z * fade
    # ordered-ish dither to 8 bit
    z = z + (np.random.default_rng(fr + 7).random((H, W, 3)).astype(np.float32) - 0.5) / 255
    return (np.clip(z, 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    a = sys.argv
    dirn, outp = a[1], a[2]
    f0, f1 = (int(a[a.index('--frames') + 1]), int(a[a.index('--frames') + 2])) if '--frames' in a else (1, cam.NFRAMES)
    music = a[a.index('--music') + 1] if '--music' in a else None
    frames = [f for f in range(f0, f1 + 1) if os.path.exists(os.path.join(dirn, 'f%04d.exr' % f)) and os.path.exists(os.path.join(dirn, 'd%04d.exr' % f))]
    print('frames', frames[0], '..', frames[-1], len(frames), flush=True)
    ex = post.exposure_curve(dirn, frames)
    titles = Titles(); taa = post.Temporal()
    stills = {}
    if '--stills' in a:
        i = a.index('--stills'); stills = {int(v): None for v in a[i + 1].split(',')}; still_dir = a[i + 2]; os.makedirs(still_dir, exist_ok=True)
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(cam.FPS), '-i', '-']
    if music: cmd += ['-i', music]
    cmd += ['-c:v', 'libx264', '-preset', 'slow', '-crf', '19', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
            '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-movflags', '+faststart']
    if music: cmd += ['-c:a', 'aac', '-b:a', '256k', '-shortest']
    cmd += [outp]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    prev = None
    for fr in frames:
        if prev is not None and fr != prev + 1: taa = post.Temporal()
        t = (fr - 1) / cam.FPS
        rgb, d = post.load(dirn, fr)
        y = post.process(rgb, d, t, ex[fr], taa=taa)
        img = finish(y, t, titles, fr)
        ff.stdin.write(img.tobytes())
        if fr in stills:
            Image.fromarray(img).save(os.path.join(still_dir, 'still_%04d.jpg' % fr), quality=92)
        prev = fr
        if fr % 20 == 0: print('post', fr, flush=True)
    ff.stdin.close(); ff.wait()
    print('wrote', outp)


if __name__ == '__main__':
    main()

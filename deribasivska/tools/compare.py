"""Side-by-side sheet: reference photo (left) vs render still (right).
usage: python tools/compare.py out.jpg ref1.jpg:still1.jpg [ref2.jpg:still2.jpg ...]"""
import sys
from PIL import Image

out, pairs = sys.argv[1], [p.split(':') for p in sys.argv[2:]]
CW, CH = 800, 450
sheet = Image.new('RGB', (CW * 2, CH * len(pairs)), (12, 12, 12))
for i, (r, s) in enumerate(pairs):
    for j, f in enumerate((r, s)):
        im = Image.open(f).convert('RGB')
        k = max(CW / im.width, CH / im.height)
        im = im.resize((int(im.width * k + 0.5), int(im.height * k + 0.5)), Image.LANCZOS)
        x0 = (im.width - CW) // 2; y0 = (im.height - CH) // 2
        sheet.paste(im.crop((x0, y0, x0 + CW, y0 + CH)), (j * CW, i * CH))
sheet.save(out, quality=88)
print('wrote', out)

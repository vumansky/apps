"""Original 20-second score, synthesised from scratch with numpy (no samples).
D major, 96 bpm, 8 bars: felt-piano arpeggio -> strings and solo violin -> swell -> full bloom at the reveal (12.5 s)."""
import sys, numpy as np
from scipy import signal
import wave

SR = 48000
BPM = 96.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT            # 2.5 s
DUR = 20.0
N = int(SR * (DUR + 4.0))  # tail room for reverb, trimmed later
rng = np.random.default_rng(1794)
dry = np.zeros((N, 2)); wet = np.zeros((N, 2))

NOTE = {'C': -9, 'C#': -8, 'D': -7, 'D#': -6, 'E': -5, 'F': -4, 'F#': -3, 'G': -2, 'G#': -1, 'A': 0, 'A#': 1, 'B': 2}
def hz(n):
    name, octv = n[:-1], int(n[-1])
    return 440.0 * 2 ** ((NOTE[name] + 12 * (octv - 4)) / 12)

def put(buf, sig, t0, pan=0.0, gain=1.0):
    i = max(0, int(t0 * SR))
    if i >= N: return
    sig = sig[:N - i]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:i + len(sig), 0] += sig * l * gain; buf[i:i + len(sig), 1] += sig * r * gain

def env(n, a, d, s, r, hold):
    t = np.arange(n) / SR
    e = np.minimum(t / max(a, 1e-4), 1.0)
    e *= s + (1 - s) * np.exp(-np.maximum(t - a, 0) / max(d, 1e-4))
    rel = np.clip((hold + r - t) / max(r, 1e-4), 0, 1)
    return e * rel ** 2

def lp(x, fc, order=2):
    b, a = signal.butter(order, min(fc, SR * 0.45) / (SR / 2)); return signal.lfilter(b, a, x)
def hp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), 'high'); return signal.lfilter(b, a, x)

def piano(f, dur, vel=1.0):
    """felt piano: inharmonic partials with frequency-dependent decay + soft hammer thump."""
    n = int((dur + 2.5) * SR); t = np.arange(n) / SR
    y = np.zeros(n); B = 0.0004
    for k in range(1, 11):
        fk = f * k * np.sqrt(1 + B * k * k)
        if fk > 9000: break
        amp = (1.0 / k ** 1.25) * (0.6 + 0.4 * np.cos(k * 0.9)) ** 2
        y += amp * np.exp(-t * (0.9 + 0.35 * k) * (f / 261.6) ** 0.35) * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6.28))
    y *= np.minimum(t / 0.006, 1.0)
    th = lp(rng.normal(size=int(0.03 * SR)), 900) * np.exp(-np.arange(int(0.03 * SR)) / (0.006 * SR))
    y[:len(th)] += th * 0.5
    y *= np.clip((dur + 1.6 - t) / 1.6, 0, 1) ** 2
    return lp(y, 2600 + 2400 * vel) * vel

def strings(f, dur, vel=1.0, bright=2600, attack=0.5, release=0.9, vib=0.0):
    """ensemble strings: 7 detuned saws per side, low-passed, slow bow attack."""
    n = int((dur + release) * SR); t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for ch in range(2):
        y = np.zeros(n)
        for d in np.linspace(-1, 1, 7):
            det = 1 + d * 0.006 + rng.normal() * 0.0008
            ph = 2 * np.pi * f * det * t + rng.uniform(0, 6.28)
            if vib: ph += vib * np.sin(2 * np.pi * (5.2 + d * 0.3) * t + rng.uniform(0, 6.28))
            y += signal.sawtooth(ph)
        out[:, ch] = lp(y / 7, bright, 2)
    e = env(n, attack, 1.0, 0.85, release, dur)
    return out * e[:, None] * vel

def violin(f, dur, vel=1.0):
    """solo lead: saw + body formants, delayed vibrato."""
    n = int((dur + 0.5) * SR); t = np.arange(n) / SR
    vib = 0.9 * np.clip((t - 0.18) / 0.35, 0, 1) * np.sin(2 * np.pi * 5.6 * t)
    ph = 2 * np.pi * f * t + vib * (f / 440) ** 0 * 1.0
    y = signal.sawtooth(ph) * 0.6 + 0.4 * signal.sawtooth(ph * 1.002 + 1)
    body = sum(g * signal.lfilter(*signal.iirpeak(fc / (SR / 2), Q), y) for fc, Q, g in ((480, 4, 0.9), (1150, 5, 0.7), (2700, 4, 0.55)))
    y = lp(0.35 * y + body, 4200, 2)
    e = env(n, 0.09, 0.6, 0.8, 0.45, dur) * (1 + 0.12 * np.sin(2 * np.pi * 5.6 * t) * np.clip((t - 0.2) / 0.4, 0, 1))
    return y * e * vel * 0.5

def pluck(f, dur=1.2, vel=1.0):
    """pizzicato / harp via Karplus-Strong."""
    n = int(dur * SR); p = int(SR / f)
    buf = lp(rng.uniform(-1, 1, p), 3500)
    y = np.zeros(n)
    for i in range(n):
        y[i] = buf[i % p]
        buf[i % p] = 0.996 * 0.5 * (buf[i % p] + buf[(i + 1) % p])
    return y * vel * np.minimum(np.arange(n) / 40.0, 1)

def bass(f, dur, vel=1.0):
    n = int((dur + 0.5) * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * np.sin(2 * np.pi * 3 * f * t)
    return y * env(n, 0.04, 1.5, 0.75, 0.45, dur) * vel

def drum(f0=95, f1=42, dur=1.6, vel=1.0):
    """orchestral bass drum / timpani-ish hit."""
    n = int(dur * SR); t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.05)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.45)
    y += lp(rng.normal(size=n), 400) * np.exp(-t / 0.03) * 0.6
    return y * vel

def cymbal(dur, vel=1.0, swell=False):
    n = int(dur * SR); t = np.arange(n) / SR
    y = hp(rng.normal(size=n), 5200) + 0.5 * hp(rng.normal(size=n), 9000)
    e = (t / dur) ** 2.6 if swell else np.exp(-t / (dur * 0.28)) * np.minimum(t / 0.004, 1)
    return y * e * vel * 0.25

def shimmer(f, dur, vel=1.0):
    n = int((dur + 2) * SR); t = np.arange(n) / SR
    y = sum(np.sin(2 * np.pi * f * k * t + rng.uniform(0, 6.28)) * np.exp(-t * (1.2 + k)) / k for k in (1, 2.76, 5.4))
    return y * vel * np.minimum(t / 0.002, 1)

# ------------------------------------------------------------------ arrangement
CH = [  # bass, pad voicing
    ('D2', ['D3', 'A3', 'E4', 'F#4']), ('B1', ['B2', 'F#3', 'A3', 'D4']),
    ('G1', ['G2', 'D3', 'F#3', 'B3']), ('A1', ['A2', 'E3', 'A3', 'D4']),
    ('E2', ['E3', 'G3', 'B3', 'D4']),  ('D2', ['D3', 'A3', 'D4', 'F#4', 'A4']),
    ('G1', ['G2', 'D3', 'G3', 'B3', 'D4']), ('D2', ['D3', 'A3', 'D4', 'F#4', 'A4'])]
ARP = [['D4', 'A4', 'E5', 'F#5', 'A5', 'F#5', 'E5', 'A4'], ['B3', 'F#4', 'A4', 'D5', 'F#5', 'D5', 'A4', 'F#4'],
       ['G3', 'D4', 'F#4', 'B4', 'D5', 'B4', 'F#4', 'D4'], ['A3', 'E4', 'A4', 'D5', 'E5', 'C#5', 'A4', 'E4']]
for b in range(4):                                   # bars 1-4: felt piano arpeggio
    for i, nn in enumerate(ARP[b]):
        v = (0.55 + 0.12 * b) * (1.0 if i % 4 == 0 else 0.72)
        s = piano(hz(nn), BEAT * 0.9, v)
        put(dry, s, b * BAR + i * BEAT / 2 + rng.normal() * 0.004, pan=-0.25 + 0.5 * (i % 3) / 2, gain=0.5)
        put(wet, s, b * BAR + i * BEAT / 2, gain=0.22)
# bar 5: rising run into the reveal
run = ['E4', 'G4', 'B4', 'D5', 'E5', 'G5', 'B5', 'D6', 'A4', 'C#5', 'E5', 'A5', 'C#6', 'E6', 'A6', 'C#7']
for i, nn in enumerate(run):
    s = piano(hz(nn), 0.25, 0.6 + 0.03 * i)
    put(dry, s, 4 * BAR + i * BEAT / 4, pan=-0.5 + i / 15, gain=0.36); put(wet, s, 4 * BAR + i * BEAT / 4, gain=0.2)

for b, (bn, pad) in enumerate(CH):                   # pad strings + bass
    big = b >= 5
    t0 = b * BAR
    vel = [0.16, 0.2, 0.3, 0.36, 0.46, 0.8, 0.8, 0.74][b]
    for j, nn in enumerate(pad):
        s = strings(hz(nn), BAR * (1.0 if b < 7 else 1.0), vel, bright=2200 + 500 * b + (1800 if big else 0), attack=0.6 if not big else 0.12, release=1.2 if b < 7 else 2.6)
        put(dry, s[:, 0], t0, pan=-0.8 + 1.6 * j / max(1, len(pad) - 1), gain=0.26); put(wet, s[:, 1], t0, pan=0.8 - 1.6 * j / max(1, len(pad) - 1), gain=0.3)
    if big:                                           # octave-doubled high strings for the bloom
        for nn in pad[-3:]:
            s = strings(hz(nn) * 2, BAR, 0.42, bright=5200, attack=0.1, release=1.2 if b < 7 else 2.6, vib=0.5)
            put(dry, s[:, 0], t0, pan=-0.5, gain=0.2); put(wet, s[:, 1], t0, pan=0.5, gain=0.3)
    if b >= 1:
        s = bass(hz(bn), BAR * 0.98, 0.5 if not big else 0.95)
        put(dry, s, t0, gain=0.2 if not big else 0.3)
        if big: put(dry, bass(hz(bn) * 2, BAR * 0.98, 0.5), t0, gain=0.2)
# bar 5 second half: dominant (A) lift
for nn in ('A2', 'E3', 'A3', 'C#4', 'E4'):
    s = strings(hz(nn), BAR / 2, 0.55, bright=3600, attack=0.25, release=0.5)
    put(dry, s[:, 0], 4.5 * BAR, pan=-0.4, gain=0.26); put(wet, s[:, 1], 4.5 * BAR, pan=0.4, gain=0.3)
put(dry, bass(hz('A1'), BAR / 2, 0.8), 4.5 * BAR, gain=0.24)

# pizzicato pulse, bars 3-5; driving staccato eighths in the bloom
for b in range(2, 5):
    root = [None, None, 'G3', 'A3', 'E3'][b]
    for i in range(8):
        nn = hz(root) * (1.5 if i % 4 == 2 else (2 if i % 4 == 3 else 1))
        s = pluck(nn, 0.9, 0.5 + 0.1 * (b - 2))
        put(dry, s, b * BAR + i * BEAT / 2, pan=0.35, gain=0.3); put(wet, s, b * BAR + i * BEAT / 2, gain=0.15)
for b in range(5, 8):
    root = ['D3', 'G3', 'D3'][b - 5]
    for i in range(8 if b < 7 else 4):
        s = strings(hz(root) * (2 if i % 2 else 1), BEAT * 0.22, 0.55 if i % 4 == 0 else 0.38, bright=3800, attack=0.02, release=0.12)
        put(dry, s[:, 0], b * BAR + i * BEAT / 2, pan=0.3, gain=0.3); put(wet, s[:, 1], b * BAR + i * BEAT / 2, pan=-0.3, gain=0.12)

# solo violin melody (enters bar 3), doubled an octave up by shimmer bells in the bloom
MEL = [(2, 0, 'B4', 1), (2, 1, 'D5', 1), (2, 2, 'F#5', 2),
       (3, 0, 'E5', 2), (3, 2, 'C#5', 1), (3, 3, 'E5', 1),
       (4, 0, 'G5', 2), (4, 2, 'A5', 1.5), (4, 3.5, 'C#6', 0.5),
       (5, 0, 'D6', 1.5), (5, 1.5, 'C#6', 0.5), (5, 2, 'A5', 2),
       (6, 0, 'B5', 1.5), (6, 1.5, 'A5', 0.5), (6, 2, 'G5', 1), (6, 3, 'A5', 1),
       (7, 0, 'F#5', 3.6)]
for b, bt, nn, ln in MEL:
    t0 = b * BAR + bt * BEAT
    v = 0.55 if b < 5 else 0.85
    s = violin(hz(nn), ln * BEAT * 0.96, v)
    put(dry, s, t0, pan=-0.12, gain=0.5); put(wet, s, t0, pan=0.1, gain=0.42)
    if b >= 5:
        s2 = strings(hz(nn), ln * BEAT, 0.5, bright=4800, attack=0.06, release=0.5, vib=0.6)
        put(dry, s2[:, 0], t0, pan=0.4, gain=0.22); put(wet, s2[:, 1], t0, pan=-0.4, gain=0.26)
        sh = shimmer(hz(nn) * 2, 1.0, 0.25); put(wet, sh, t0, pan=0.5, gain=0.2); put(dry, sh, t0, pan=-0.5, gain=0.08)

# percussion + swell into the reveal
REV = 5 * BAR
put(dry, cymbal(2.3, 1.0, swell=True), REV - 2.3, gain=0.5); put(wet, cymbal(2.3, 1.0, swell=True), REV - 2.3, gain=0.3)
roll_t = np.arange(REV - 1.25, REV - 0.02, BEAT / 8)
for i, tt in enumerate(roll_t):
    put(dry, drum(80, 55, 0.5, 0.12 + 0.5 * (i / len(roll_t)) ** 2), tt, gain=0.32)
for tt, v in ((REV, 1.0), (REV + BAR, 0.75), (REV + 2 * BAR, 0.85), (REV + BAR * 0.75, 0.4), (REV + BAR * 1.75, 0.45)):
    d = drum(vel=v); put(dry, d, tt, gain=0.6); put(wet, d, tt, gain=0.2)
put(dry, cymbal(3.0, 1.0), REV, gain=0.42); put(wet, cymbal(3.0, 1.0), REV, gain=0.45)
put(wet, cymbal(2.5, 0.6), REV + 2 * BAR, gain=0.4)
# soft heartbeat pulse in bars 3-5
for b in range(2, 5):
    for bt in (0, 2):
        put(dry, drum(70, 40, 0.8, 0.28 + 0.08 * (b - 2)), b * BAR + bt * BEAT, gain=0.3)
# opening air: leaves rustling in a light breeze
nz = rng.normal(size=int(7 * SR)); t = np.arange(len(nz)) / SR
rust = signal.lfilter(*signal.butter(2, [1800 / (SR / 2), 7000 / (SR / 2)], 'band'), nz)
rust *= (0.5 + 0.5 * np.sin(2 * np.pi * 0.23 * t + 1)) ** 2 * np.clip(t / 0.8, 0, 1) * np.clip((7 - t) / 3.5, 0, 1)
put(dry, rust, 0.0, pan=-0.4, gain=0.035); put(dry, np.roll(rust, 9000), 0.0, pan=0.5, gain=0.03)

# ------------------------------------------------------------------ reverb + master
irn = int(3.2 * SR); ti = np.arange(irn) / SR
ir = rng.normal(size=(irn, 2)) * np.exp(-ti / 0.62)[:, None] * np.clip(ti / 0.012, 0, 1)[:, None]
ir[:, 0] = lp(ir[:, 0], 6500); ir[:, 1] = lp(ir[:, 1], 6500)
ir /= np.sqrt((ir ** 2).sum(0))
rev = np.stack([signal.fftconvolve(wet[:, c], ir[:, c])[:N] for c in range(2)], 1)
mix = dry + 0.9 * rev
mix = np.stack([hp(mix[:, c], 38) for c in range(2)], 1)
n20 = int(DUR * SR); mix = mix[:n20]
t = np.arange(n20) / SR
mix *= (np.clip(t / 0.04, 0, 1) * np.clip((DUR - t) / 1.6, 0, 1) ** 1.5)[:, None]
# soft limiter only: keep the quiet-to-bloom dynamic arc
pk = np.percentile(np.abs(mix), 99.97)
mix = np.tanh(mix / pk * 1.1) * 0.93
out = sys.argv[1] if len(sys.argv) > 1 else 'out/music.wav'
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype('<i2').tobytes())
lr = [np.sqrt((mix[int(a * SR):int(b * SR)] ** 2).mean()) for a, b in ((0, 5), (5, 10), (10, 12.5), (12.5, 17.5), (17.5, 20))]
print('wrote', out, 'peak %.2f' % np.abs(mix).max(), 'rms by section', np.round(20 * np.log10(np.array(lr) + 1e-9), 1))

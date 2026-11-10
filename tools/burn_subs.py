"""Burn subtitles + an elegant opening title (hook) + optional ending-title fix.

Opening title style: Noto Serif SC Black, antique metallic gold (multi-stop
gradient with a soft horizon highlight), thin dark-bronze outline, soft drop
shadow, one slow light sweep. Fades in with a slight rise - no bounce, no red
stroke, no candy colours.

subs.json: [{"start": 4.6, "end": 6.1, "text": "...", "who": "树哥"}, ...]
("who" is optional and only used by --check to print who says what, when.)
"""
import subprocess, json, argparse, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
p = argparse.ArgumentParser()
p.add_argument("video"); p.add_argument("out"); p.add_argument("subs")
p.add_argument("--hook", default="")              # "small line|BIG LINE"
p.add_argument("--hook-end", type=float, default=3.8)
p.add_argument("--fix-title", default="")         # "line1|line2"
p.add_argument("--title-start", type=float, default=0)
p.add_argument("--preview", default="")           # "1.0,2.5,7.3" -> write PNG frames only
p.add_argument("--check", action="store_true")    # print subtitle timeline with speakers and exit
a = p.parse_args()

SANS = os.path.join(HERE, "fonts/NotoSansSC-Bold.ttf")
SERIF = os.path.join(HERE, "fonts/NotoSerifSC-Black.ttf")
if not os.path.exists(SANS): SANS = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
if not os.path.exists(SERIF): SERIF = SANS
F = lambda path, s: ImageFont.truetype(path, s)

SUBS = json.load(open(a.subs, encoding="utf-8"))
if a.check:
    for s in SUBS: print(f'{s["start"]:6.2f}-{s["end"]:6.2f}  [{s.get("who","?")}]  {s["text"]}')
    raise SystemExit

probe = json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","json",a.video]))
W, H = probe["streams"][0]["width"], probe["streams"][0]["height"]; FPS = 30
S = W / 1280
clamp = lambda x: max(0.0, min(1.0, x))
ease = lambda x: 1 - (1 - clamp(x)) ** 3

# ---------- metallic gold text ----------
GOLD_STOPS = [(0.00, (255, 248, 222)), (0.30, (241, 214, 140)), (0.48, (204, 158, 62)),
              (0.52, (250, 232, 170)), (0.75, (190, 138, 48)), (1.00, (120, 78, 22))]
def gold_fill(h):
    ys = np.linspace(0, 1, h); col = np.zeros((h, 3), np.float32)
    for (p0, c0), (p1, c1) in zip(GOLD_STOPS, GOLD_STOPS[1:]):
        m = (ys >= p0) & (ys <= p1); k = ((ys[m] - p0) / (p1 - p0))[:, None]
        col[m] = np.array(c0) * (1 - k) + np.array(c1) * k
    return col

def gold_text(lines, sizes, gap, pad=40):
    """lines/sizes: list; returns RGBA layer + per-line masks union (for sweep)."""
    fonts = [F(SERIF, int(s * S)) for s in sizes]
    boxes = [ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), t, font=f, anchor="lt") for t, f in zip(lines, fonts)]
    w = max(b[2] - b[0] for b in boxes) + 2 * pad; h = sum(b[3] - b[1] for b in boxes) + int(gap * S) * (len(lines) - 1) + 2 * pad
    mask = Image.new("L", (w, h), 0); fill = np.zeros((h, w, 3), np.float32); y = pad
    for (t, f, b) in zip(lines, fonts, boxes):
        lh = b[3] - b[1]; m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).text((w // 2, y - b[1]), t, font=f, fill=255, anchor="mt")
        fill[y:y + lh] = gold_fill(lh)[:, None, :]
        mask = Image.fromarray(np.maximum(np.array(mask), np.array(m))); y += lh + int(gap * S)
    shadow = Image.new("RGBA", (w, h), (20, 10, 0, 0)); shadow.putalpha(mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(10 * S)).point(lambda v: int(v * .75)))
    halo = Image.new("RGBA", (w, h), (255, 200, 110, 0)); halo.putalpha(mask.filter(ImageFilter.GaussianBlur(16 * S)).point(lambda v: int(v * .35)))
    stroke = Image.new("RGBA", (w, h), (58, 32, 8, 0)); stroke.putalpha(mask.filter(ImageFilter.MaxFilter(5)))
    gold = Image.fromarray(fill.clip(0, 255).astype(np.uint8)).convert("RGBA"); gold.putalpha(mask)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0)); sh.alpha_composite(shadow, (0, 0))
    out.alpha_composite(sh.transform(sh.size, Image.AFFINE, (1, 0, 0, 0, 1, -int(5 * S))))
    for l in (halo, stroke, gold): out.alpha_composite(l)
    return out, mask

def sweep(layer, mask, k):
    """one soft diagonal light band moving across the glyphs, k in 0..1"""
    if k <= 0 or k >= 1: return layer
    w, h = layer.size; xs = np.arange(w)[None, :] + np.arange(h)[:, None] * 0.35
    c = -0.2 * w + k * 1.5 * w; band = np.exp(-((xs - c) / (0.06 * w)) ** 2) * 0.55
    a = np.array(mask, np.float32) / 255 * band
    hl = Image.new("RGBA", (w, h), (255, 252, 235, 0)); hl.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    out = layer.copy(); out.alpha_composite(hl); return out

# ---------- opening title ----------
hook = None
if a.hook:
    l1, l2 = a.hook.split("|")
    hook, hook_mask = gold_text([l1, l2], [56, 96], gap=14)
    shade = np.zeros((H, W), np.float32); yy = np.arange(H)[:, None] / H
    shade[:] = (np.clip(1 - yy / 0.5, 0, 1) ** 1.6) * 0.45            # soft top darkening for legibility
    shade = shade[..., None]

# ---------- subtitles ----------
fsub = F(SANS, int(46 * S))
def mk_sub(t):
    im = Image.new("RGBA", (W, int(130 * S)), (0, 0, 0, 0)); sh = im.copy()
    ImageDraw.Draw(sh).text((W // 2, int(68 * S)), t, font=fsub, fill=(0, 0, 0, 160), anchor="mm", stroke_width=int(7 * S), stroke_fill=(0, 0, 0, 160))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(im).text((W // 2, int(64 * S)), t, font=fsub, fill=(255, 255, 255), anchor="mm", stroke_width=int(4 * S), stroke_fill=(28, 18, 10))
    return im
sub_imgs = [mk_sub(s["text"]) for s in SUBS]

# ---------- ending title fix ----------
title = None
if a.fix_title:
    l1, l2 = a.fix_title.split("|")
    title, title_mask = gold_text([l1, l2], [80, 80], gap=40)
    cover = Image.new("L", (W, H), 0)
    ImageDraw.Draw(cover).rounded_rectangle([int(W * .12), int(H * .2), int(W * .88), int(H * .78)], int(130 * S), fill=255)
    cover = np.array(cover.filter(ImageFilter.GaussianBlur(40)), np.float32)[..., None] / 255

def fade(im, al):
    im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * al))); return im

def process(rgb, t):
    if hook is not None and t <= a.hook_end:
        al = min(clamp(t / 0.35), clamp((a.hook_end - t) / 0.4))
        rgb = (rgb.astype(np.float32) * (1 - shade * al)).clip(0, 255).astype(np.uint8)
    if title is not None and t >= a.title_start:
        k = clamp((t - a.title_start) / 0.25)
        bl = np.array(Image.fromarray(rgb).filter(ImageFilter.GaussianBlur(40)), np.float32) * 0.5
        rgb = (rgb.astype(np.float32) * (1 - cover * k) + bl * cover * k).clip(0, 255).astype(np.uint8)
    fr = Image.fromarray(rgb).convert("RGBA")
    if hook is not None and t <= a.hook_end:
        k = ease(t / 0.6); al = min(k, clamp((a.hook_end - t) / 0.4))
        im = sweep(hook, hook_mask, (t - 0.7) / 1.4)
        fr.alpha_composite(fade(im, al), ((W - im.width) // 2, int(36 * S + (1 - k) * 18 * S)))
    if title is not None and t >= a.title_start + 0.2:
        k = ease((t - a.title_start - 0.2) / 0.8)
        im = sweep(title, title_mask, (t - a.title_start - 1.0) / 1.6)
        fr.alpha_composite(fade(im, k), ((W - im.width) // 2, (H - im.height) // 2))
    for s, im in zip(SUBS, sub_imgs):
        if s["start"] <= t <= s["end"]:
            al = min(clamp((t - s["start"]) / 0.12), clamp((s["end"] - t) / 0.12))
            fr.alpha_composite(fade(im, al), (0, H - int(124 * S)))
    return fr.convert("RGB")

if a.preview:
    for ts in a.preview.split(","):
        t = float(ts); raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", ts, "-i", a.video, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
        process(np.frombuffer(raw, np.uint8).reshape(H, W, 3).copy(), t).save(f"{a.out}_{ts}.png")
    raise SystemExit

dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", a.video, "-f", "rawvideo", "-pix_fmt", "rgb24", "-r", str(FPS), "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", a.video,
    "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", a.out], stdin=subprocess.PIPE)
n = 0
while True:
    raw = dec.stdout.read(W * H * 3)
    if len(raw) < W * H * 3: break
    enc.stdin.write(process(np.frombuffer(raw, np.uint8).reshape(H, W, 3).copy(), n / FPS).tobytes()); n += 1
enc.stdin.close(); enc.wait(); print("frames", n)

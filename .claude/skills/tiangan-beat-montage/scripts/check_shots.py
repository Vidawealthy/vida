#!/usr/bin/env python3
"""Catch repeated or near-identical shots before the user does.

Usage:
  python3 check_shots.py PLAN_JSON                # plan only: reused clips, adjacent same subject, missing fields
  python3 check_shots.py PLAN_JSON SEG_DIR SHEET  # also compare the rendered segments' frames and write a labeled sheet

Exits 1 if anything fails. Why this exists: in the 乙木 v3 cut, two different Mixkit clips of
"looking up into a green forest" sat next to each other and read as the same shot twice. The user
caught it. Different source files are not enough; the adjacent pictures must look different.
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

plan = json.load(open(sys.argv[1])); S = plan['shots']
errors = []

# 1. plan-level checks
seen = {}
for i, sh in enumerate(S):
    c = sh['clip']
    if c == 'black': continue
    if c in seen: errors.append(f'shot {i} reuses {c} (already shot {seen[c]})')
    seen[c] = i
    if i >= 2 and not (sh.get('subject') and sh.get('why')):
        errors.append(f'shot {i} ({c}) needs "subject" and "why" (why it belongs to this 天干)')
for i in range(3, len(S)):
    a, b = S[i - 1].get('subject', ''), S[i].get('subject', '')
    if a and a == b: errors.append(f'shots {i - 1} and {i} have the same subject "{a}"')

# 2. frame-level checks on rendered segments
def frames(path, k=3):
    """k evenly spaced frames as small RGB arrays."""
    n = int(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
                                     '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', path]))
    out = []
    for j in range(k):
        idx = int((j + 1) * n / (k + 1))
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'select=eq(n\\,{idx}),scale=64:36',
                              '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
        out.append(np.frombuffer(raw, np.uint8).reshape(36, 64, 3).astype(float))
    return out

def hist(img):
    """Hue/saturation histogram of the lit pixels only. The grade crushes shadows to black, so
    counting dark pixels would make every pair look alike."""
    im = Image.fromarray(img.astype(np.uint8)).convert('HSV'); hsv = np.asarray(im, float)
    m = hsv[..., 2] > 50
    if m.sum() < 50: return None  # almost black frame: no color to compare
    h, _, _ = np.histogram2d(hsv[..., 0][m], hsv[..., 1][m], bins=[12, 4], range=[[0, 256], [0, 256]])
    h = h.flatten(); return h / h.sum()

def struct(img):
    """16x9 grayscale layout, mean-removed and unit-length: dot product = layout correlation."""
    g = np.asarray(Image.fromarray(img.astype(np.uint8)).convert('L').resize((16, 9), Image.BILINEAR), float).flatten()
    g = g - g.mean(); n = np.linalg.norm(g)
    return g / n if n > 0 else g

def similar(fa, fb):
    """Highest layout correlation and highest hue-histogram correlation over all frame pairs."""
    hd = max(float(struct(x) @ struct(y)) for x in fa for y in fb)
    hc = max([float(np.corrcoef(hx, hy)[0, 1]) for hx in map(hist, fa) for hy in map(hist, fb)
              if hx is not None and hy is not None] or [0.0])
    return hd, hc

if len(sys.argv) > 2:
    seg_dir, sheet = sys.argv[2], sys.argv[3]
    segs = [os.path.join(seg_dir, f'{i:02d}.mp4') for i in range(len(S))]
    F = [frames(p) for p in segs]
    for i in range(3, len(S)):
        hd, hc = similar(F[i - 1], F[i])
        # A repeat is the same layout AND the same colors. Calibrated on real cases:
        #   repeats: 乙木 v3 green look-up forests (layout 0.96, color 0.79), 丙火 two orange plumes on a
        #   dark sky (0.83, 0.86). Not repeats: same color segment with different pictures (sun surface
        #   vs sun disk: 0.58, 1.00), same horizon layout in different colors (0.85, 0.05).
        if hd >= 0.9 or (hd >= 0.75 and hc >= 0.5):
            errors.append(f'shots {i - 1} ({S[i - 1]["clip"]}) and {i} ({S[i]["clip"]}) look alike: '
                          f'layout correlation {hd:.2f}, color correlation {hc:.2f}')
    W, H, cols = 384, 216, 6
    rows = (len(S) + cols - 1) // cols
    im = Image.new('RGB', (W * cols, (H + 22) * rows)); dr = ImageDraw.Draw(im)
    for i, f in enumerate(F):
        x, y = (i % cols) * W, (i // cols) * (H + 22)
        im.paste(Image.fromarray(f[1].astype(np.uint8)).resize((W, H)), (x, y))
        dr.text((x + 4, y + H + 4), f'{i:02d} {S[i]["clip"]}  {S[i].get("subject", "")}'[:60], fill='yellow')
    im.save(sheet, quality=85)
    print('sheet', sheet, '(open it and check every subject against tiangan_imagery.md)')

if errors:
    print('FAIL'); print('\n'.join('  - ' + e for e in errors)); sys.exit(1)
print('OK: no reused clips, no adjacent look-alikes')

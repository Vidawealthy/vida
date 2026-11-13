#!/usr/bin/env python3
"""Cut, grade and assemble the montage from a plan.json.

Usage: python3 render.py PLAN_JSON TITLES_DIR WORK_DIR OUT_MP4

plan.json:
{
  "bgm": "/path/bgm.mp3", "clips_dir": "/path/clips",
  "cuts": [0, 1.643, 3.692, ...],      # from beats.py; len(cuts) == len(shots) + 1
  "text_off": 3.45,
  "shots": [
    {"clip": "hook.mp4", "in": 1.6, "subject": "手心浇灌小苗", "why": "乙木最小的样子"},
    {"clip": "black"},
    {"clip": "k12440.mp4", "in": null, "vig": "PI/4.5", "subject": "睡莲特写", "why": "草本花，乙木"},
    ...
  ]
}
"in": seconds into the clip (null = 35% in). "vig": vignette angle or null.
Shot 0 is the hook, shot 1 the black title card. Run check_shots.py first.
"""
import json, os, subprocess, sys

FPS = 30
plan_path, titles, work, out = sys.argv[1:5]
P = json.load(open(plan_path))
C, S = P['cuts'], P['shots']
assert len(C) == len(S) + 1, f'{len(C) - 1} segments in cuts but {len(S)} shots'
assert S[1]['clip'] == 'black', 'shot 1 must be the black title card'
F = [round(t * FPS) for t in C]
seg = os.path.join(work, 'seg'); os.makedirs(seg, exist_ok=True)
GRADE = ("scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,setsar=1,fps=30,"
         "unsharp=5:5:0.7:5:5:0,eq=contrast=1.10:saturation=1.38,"
         "curves=master='0/0 0.07/0 0.25/0.19 0.5/0.48 0.85/0.87 1/0.96'")

def dur(p):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))

for i, sh in enumerate(S):
    n = F[i + 1] - F[i]; o = os.path.join(seg, f'{i:02d}.mp4')
    if sh['clip'] == 'black':
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=black:s=1920x1080:r={FPS}', '-frames:v', str(n),
                        '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-crf', '14', o], check=True)
        continue
    p = os.path.join(P['clips_dir'], sh['clip']); d = dur(p); sd = n / FPS
    inp = sh.get('in')
    if inp is None: inp = max(0, min(d * 0.35, d - sd - 0.15))
    assert inp + sd <= d + 0.01, f'shot {i}: {sh["clip"]} is {d:.2f}s, cannot take {sd:.2f}s from {inp:.2f}s'
    vf = GRADE + (f",vignette=angle={sh['vig']}" if sh.get('vig') else '')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{inp:.3f}', '-i', p, '-vf', vf, '-frames:v', str(n), '-an',
                    '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-crf', '14', '-preset', 'fast', o], check=True)
    print(f'{i:02d} {sh["clip"]:<16} in {inp:6.2f}  {n:3d} frames  {sh.get("subject", "")}', flush=True)

lst = os.path.join(seg, 'list.txt')
open(lst, 'w').write(''.join(f"file '{i:02d}.mp4'\n" for i in range(len(S))))
body = os.path.join(seg, 'body.mp4')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', body], check=True)

# Title timing uses t (seconds), not frame numbers: with looped image inputs, n-based enables leak 1-2 frames.
nrev = int(open(os.path.join(titles, 'reveal_frames.txt')).read())
f1 = F[1]; r0 = f1 + 2; rend = round(P['text_off'] * FPS)
fc = (f"[0][1]overlay=enable='lt(t,{f1 / FPS - 0.001:.4f})'[a];"
      f"[2]setpts=PTS-STARTPTS+{r0}/TB/{FPS}[r];"
      f"[a][r]overlay=eof_action=pass:enable='between(t,{(r0 - 0.5) / FPS:.4f},{(r0 + nrev - 0.5) / FPS:.4f})'[b];"
      f"[b][3]overlay=enable='between(t,{(r0 + nrev - 0.5) / FPS:.4f},{(rend - 0.5) / FPS:.4f})'[c];[c][4]overlay[v]")
last = os.path.join(titles, f'real_{nrev - 1:03d}.png')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', body, '-loop', '1', '-i', os.path.join(titles, 'hook.png'),
                '-framerate', '30', '-i', os.path.join(titles, 'real_%03d.png'), '-loop', '1', '-i', last,
                '-loop', '1', '-i', os.path.join(titles, 'overlay.png'), '-i', P['bgm'],
                '-filter_complex', fc, '-map', '[v]', '-map', '5:a', '-t', f'{C[-1]:.3f}',
                '-c:v', 'libx264', '-crf', '16', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-r', '30',
                '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', out], check=True)
print('wrote', out)

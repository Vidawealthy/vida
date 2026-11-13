#!/usr/bin/env python3
"""Check every cut in the finished video against the drum hits in its own audio track.

Usage: python3 verify_sync.py OUT_MP4 PLAN_JSON

Detects cuts from frame differences (so it checks what was rendered, not what was planned),
finds the strongest percussive onset within ±80ms of each, and reports the offset.
Pass = every planned cut found, no extra cuts, every |offset| <= 17ms (half a frame at 30fps).
"""
import json, os, subprocess, sys, tempfile
import numpy as np
import librosa

video, plan = sys.argv[1], json.load(open(sys.argv[2]))
cuts = plan['cuts'][1:-1]
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', video, '-vf', 'scale=96:54,format=gray', '-f', 'rawvideo', '-'],
                     capture_output=True).stdout
b = np.frombuffer(raw, np.uint8).reshape(-1, 54, 96).astype(float)
d = np.abs(np.diff(b, axis=0)).mean(axis=(1, 2))
det = [(i + 1) / 30 for i in range(len(d)) if d[i] > 10 and d[i] > 3 * np.median(d[max(0, i - 6):i + 7])]

wav = os.path.join(tempfile.mkdtemp(), 'a.wav')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-ac', '1', '-ar', '44100', wav], check=True)
y, sr = librosa.load(wav, sr=None); hop = 256
pe = librosa.onset.onset_strength(y=librosa.effects.percussive(y), sr=sr, hop_length=hop)
ft = librosa.frames_to_time(np.arange(len(pe)), sr=sr, hop_length=hop)

ok, worst = True, 0
for t in cuts:
    near = [x for x in det if abs(x - t) < 0.1]
    if not near:
        print(f'{t:7.3f}  MISSING: planned cut not found in video'); ok = False; continue
    vc = near[0]
    m = (ft > vc - 0.08) & (ft < vc + 0.08); k = int(np.argmax(np.where(m, pe, -1)))
    err = (vc - ft[k]) * 1000; worst = max(worst, abs(err))
    flag = '' if abs(err) <= 17 else '  <-- OFF BEAT'
    if flag: ok = False
    print(f'cut {vc:7.3f}s  drum {ft[k]:7.3f}s  {err:+5.0f}ms  strength {pe[k]:4.1f}{flag}')
extra = [round(x, 2) for x in det if all(abs(x - t) >= 0.1 for t in cuts)]
if extra:
    print('extra cuts not in plan (a clip with a hard cut inside it?):', extra); ok = False
print(f'{len(cuts)} planned, {len(det)} detected, worst {worst:.0f}ms ->', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)

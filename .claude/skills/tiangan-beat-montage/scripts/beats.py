#!/usr/bin/env python3
"""Analyze a BGM and propose beat-synced cut points.

Usage: python3 beats.py BGM_FILE OUT_PLAN_JSON [--hook-window 1.5 2.2]

Writes a plan skeleton (cuts, text_off, beat table) and prints every beat with its
strength so you can see where holds go. Cuts land only on strong beats; weak beats are
skipped so the previous shot holds. A gap longer than 2.5 beats gets the strongest hit inside
it when that hit is strong (off-beat accents); quiet breaks keep their long hold.
"""
import argparse, json, os, subprocess, sys, tempfile
import numpy as np
import librosa

ap = argparse.ArgumentParser()
ap.add_argument('bgm'); ap.add_argument('out')
ap.add_argument('--hook-window', nargs=2, type=float, default=[1.5, 2.2])
ap.add_argument('--weak-ratio', type=float, default=0.6,
                help='beat counts as strong if strength >= ratio * median strength after the drop')
a = ap.parse_args()

# Decode with ffmpeg: some "mp3" uploads are really other containers and libsndfile chokes.
wav = os.path.join(tempfile.mkdtemp(), 'bgm.wav')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a.bgm, '-ac', '1', '-ar', '44100', wav], check=True)
y, sr = librosa.load(wav, sr=None)
dur = len(y) / sr
hop = 256
pe = librosa.onset.onset_strength(y=librosa.effects.percussive(y), sr=sr, hop_length=hop)
ft = librosa.frames_to_time(np.arange(len(pe)), sr=sr, hop_length=hop)
rms = librosa.feature.rms(y=y, hop_length=hop)[0]
tempo, bf = librosa.beat.beat_track(onset_envelope=pe, sr=sr, hop_length=hop, tightness=200)
tempo = float(np.atleast_1d(tempo)[0]); P = 60 / tempo

def snap(t, w=0.06):
    m = (ft > t - w) & (ft < t + w)
    i = int(np.argmax(np.where(m, pe, -1)))
    return float(ft[i]), float(pe[i])

def rms_between(t0, t1):
    i0, i1 = librosa.time_to_frames([t0, t1], sr=sr, hop_length=hop)
    return float(rms[i0:max(i1, i0 + 1)].mean())

beats = [snap(t) for t in librosa.frames_to_time(bf, sr=sr, hop_length=hop)]

# Drop = first beat after 2s where loudness of the next beat is >1.8x the previous two beats.
drop = None
for t, s in beats:
    if t < 2.0: continue
    if rms_between(t, t + P) > 1.8 * rms_between(t - 2 * P, t):
        drop = t; break
if drop is None:
    sys.exit('no drop found; set cuts by hand')

# Hook end = strongest onset in the hook window.
m = (ft > a.hook_window[0]) & (ft < a.hook_window[1])
hook_end = float(ft[int(np.argmax(np.where(m, pe, -1)))])

post = [(t, s) for t, s in beats if t >= drop - 1e-3]
med = float(np.median([s for _, s in post]))
cuts = [0.0, round(hook_end, 3), round(drop, 3)]
last = drop
for t, s in post[1:]:
    if dur - t < 0.3: break  # too close to the end for a new shot
    if s >= a.weak_ratio * med:
        if t - last > 2.5 * P:  # long gap: fill with the strongest hit inside it, if it is a real hit
            mm = (ft > last + 0.6 * P) & (ft < t - 0.6 * P)
            if mm.any():
                k = int(np.argmax(np.where(mm, pe, -1)))
                # a quiet break (weak hits only) keeps its long hold on purpose
                if pe[k] >= a.weak_ratio * med:
                    cuts.append(round(float(ft[k]), 3))
        cuts.append(round(t, 3)); last = t
cuts.append(round(dur, 3))

print(f'tempo {tempo:.1f} BPM, beat {P:.3f}s, duration {dur:.2f}s')
print(f'hook end {hook_end:.3f}s, drop {drop:.3f}s, text_off {drop - 0.25:.3f}s')
print(f'median strength after drop {med:.1f}; strong >= {a.weak_ratio * med:.1f}')
for t, s in beats:
    tag = 'CUT' if any(abs(t - c) < 1e-3 for c in cuts) else ('weak, hold' if t >= drop else 'pre-drop')
    print(f'  {t:7.3f}  strength {s:5.1f}  rms {rms_between(t, t + P):.3f}  {tag}')
print(f'{len(cuts) - 1} segments ({len(cuts) - 3} shots after the hook and black card)')

plan = dict(bgm=os.path.abspath(a.bgm), tempo=round(tempo, 2), cuts=cuts,
            text_off=round(drop - 0.25, 3), shots=[], beats=[[round(t, 3), round(s, 1)] for t, s in beats])
json.dump(plan, open(a.out, 'w'), ensure_ascii=False, indent=1)
print('wrote', a.out)

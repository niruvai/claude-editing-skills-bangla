#!/usr/bin/env python3
"""full-reel: the WHOLE clip as one finished reel. Bangla (or any) captions run from the first word to the last,
an optional hook title sits on top for the first seconds, and short effect segments made with the other skills
(/explainer, /split-screen, /storytelling, /ranking-list, /behind-the-person) are dropped in at the moments
they belong to. Only the parts between the effects are rendered here, so it stays quick.

    <kit>/.venv/bin/python build.py prep <video> [--fit pad|blur|crop]   # non-9:16 clip -> <stem>.916.mp4
    <kit>/.venv/bin/python build.py <spec.json>

Spec (see SKILL.md):
  video, out
  hook: {"text": "একটা *কৌশল*", "until": 3.0}      optional title for the first seconds (*word* turns yellow)
  keys: ["কৌশল", "ভিউ"]                             caption words to turn yellow
  caption_top: 1380
  inserts: [{"file": "clip.explainer.mp4", "start": 21.12}, ...]   effect renders; start = its spec "start"
"""
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'kit'))
from reel import Job, Comp, FPS, W, H, duration, rich, run, sheet, word_caps  # noqa: E402

PLAIN = 1.0      # gaps shorter than this are cut straight from the clip, no captions (a breath between effects)
ASPECT_TOL = 0.02


def size(video):
    out = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                   'stream=width,height:stream_side_data=rotation', '-of', 'json', str(video)])
    s = json.loads(out)['streams'][0]
    w, h = int(s['width']), int(s['height'])
    rot = next((abs(int(d.get('rotation', 0))) for d in s.get('side_data_list', []) if 'rotation' in d), 0)
    return (h, w) if rot in (90, 270) else (w, h)


def prep(video, fit='pad'):
    """a 9:16 copy of a square or landscape clip, with the same timing, so every skill sees the same frame.
    pad: the clip sits a bit above the middle on a dark backdrop (best for cutout skills),
    blur: the same over a blurred, darkened copy of itself, crop: fill the frame (faces get very big)."""
    video = Path(video).resolve()
    w, h = size(video)
    if abs(w / h - W / H) < ASPECT_TOL:
        print(f'{video.name} is already 9:16, use it as it is')
        return video
    out = video.with_name(video.stem + '.916.mp4')
    fg = f'scale={W}:-2' if w / h > W / H else f'scale=-2:{H}'
    ytop = f'max(0\\,(H-h)/2-120)'
    if fit == 'crop':
        vf = f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}'
    elif fit == 'blur':
        vf = (f'split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:6,'
              f'eq=brightness=-0.18[bg];[b]{fg}[f];[bg][f]overlay=(W-w)/2:{ytop},setsar=1,fps={FPS}')
    else:
        vf = (f'{fg}[f];color=c=0x111214:s={W}x{H}:r={FPS}[bg];[bg][f]overlay=(W-w)/2:{ytop}:shortest=1,'
              f'setsar=1,fps={FPS}')
    run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-filter_complex', vf, '-c:v', 'libx264', '-preset', 'fast',
         '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out])
    tr = video.with_name(video.stem + '.transcript.json')
    if tr.exists():
        shutil.copy(tr, out.with_name(out.stem + '.transcript.json'))   # same timing, no need to transcribe again
    print(f'wrote {out}  ({w}x{h} -> {W}x{H}, fit={fit}). Use this file for every skill from now on.')
    return out


def plain(video, a, b, out):
    run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{a:.3f}', '-i', video, '-t', f'{b - a:.3f}',
         '-vf', f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}',
         '-c:v', 'libx264', '-preset', 'fast', '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ar', '48000', out])


def captioned(spec, a, b, n):
    """one rendered stretch of the clip, a..b in source seconds: full-frame video, captions, hook if it falls here"""
    sub = dict(video=str(spec['_video']), start=a, end=b, out=str(spec['_work'] / f'part{n:02d}.mp4'))
    if spec.get('transcript'):
        sub['transcript'] = str(spec['_base'] / spec['transcript'])
    sf = spec['_work'] / f'part{n:02d}.json'
    sf.write_text(json.dumps(sub, ensure_ascii=False))
    j = Job(sf, 'full-reel')
    c = Comp(j)
    top = int(spec.get('caption_top', 1380))
    c.body.append(c.video(j.clip, f'position:absolute;left:0;top:0;width:{W}px;height:{H}px', 'bg'))
    hook = spec.get('hook') or {}
    until = float(hook.get('until', 3.0)) - a
    if hook.get('text') and until > 0.2:
        t = rich(hook['text']).replace('<em>', '<span style="color:#FFD400">').replace('</em>', '</span>')
        c.css.append('''#hook{position:absolute;left:70px;right:70px;top:260px;text-align:center;font:900 92px/1.12 'Archivo Black';
color:#fff;-webkit-text-stroke:10px #000;paint-order:stroke fill;text-shadow:0 6px 16px rgba(0,0,0,.45)}''')
        c.body.append(f'<div id="hook">{t}</div>')
        c.js.append(f'tl.fromTo("#hook",{{scale:.7,autoAlpha:0}},{{scale:1,autoAlpha:1,duration:.3,ease:"back.out(1.8)"}},0.02);')
        c.js.append(f'tl.to("#hook",{{autoAlpha:0,duration:.2}},{min(until, j.dur) - 0.2:.3f});')
    css = f'''.tk{{position:absolute;left:0;width:{W}px;top:{top}px;text-align:center;visibility:hidden;font:800 76px/1.15 'TikTok Sans';
color:#fff;-webkit-text-stroke:9px #000;paint-order:stroke fill;text-shadow:0 5px 12px rgba(0,0,0,.35)}}
.tk span.k{{color:#FFD400}}'''
    word_caps(c, j.words, 'tk', css, maxw=3, maxc=16, keys=spec.get('keys') or [], pop=(0.82, 0.18))
    c.write()
    c.render(j.out)
    return j.out


def build(spec_path):
    spec_path = Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text())
    base = spec_path.parent
    video = (base / spec['video']).resolve()
    if not video.exists():
        sys.exit(f'video not found: {video}')
    w, h = size(video)
    if abs(w / h - W / H) >= ASPECT_TOL:
        sys.exit(f'{video.name} is {w}x{h}, not 9:16. Run "build.py prep {video.name}" and use the .916.mp4 it writes.')
    total = duration(video)
    out = (base / (spec.get('out') or f'{video.stem}.full-reel.mp4')).resolve()
    work = out.parent / '.work' / out.stem
    work.mkdir(parents=True, exist_ok=True)
    spec.update(_video=video, _work=work, _base=base)

    ins = []
    for k in spec.get('inserts') or []:
        f = (base / k['file']).resolve()
        if not f.exists():
            sys.exit(f'insert not found: {f} (render it with its own skill first)')
        a = float(k['start'])
        ins.append((a, a + duration(f), f))
    ins.sort()
    for (a1, b1, f1), (a2, b2, f2) in zip(ins, ins[1:]):
        if a2 < b1 - 0.05:
            sys.exit(f'{f1.name} ({a1:.2f}-{b1:.2f}) and {f2.name} ({a2:.2f}-{b2:.2f}) overlap')
    if ins and ins[-1][1] > total + 0.1:
        sys.exit(f'{ins[-1][2].name} runs past the end of the clip ({ins[-1][1]:.2f} > {total:.2f})')

    parts, t, n = [], 0.0, 0
    for a, b, f in ins + [(total, total, None)]:
        if a - t > 0.04:
            n += 1
            seg = work / f'part{n:02d}.mp4'
            if a - t < PLAIN:
                plain(video, t, a, seg)
            else:
                captioned(spec, t, a, n)
            parts.append(seg)
        if f:
            parts.append(f)
        t = max(t, b)

    print(f'joining {len(parts)} parts ...', flush=True)
    inputs, chains = [], []
    for i, p in enumerate(parts):
        inputs += ['-i', str(p)]
        chains.append(f'[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},format=yuv420p[v{i}];'
                      f'[{i}:a]aresample=48000,aformat=channel_layouts=stereo[a{i}]')
    fc = ';'.join(chains) + ';' + ''.join(f'[v{i}][a{i}]' for i in range(len(parts))) + f'concat=n={len(parts)}:v=1:a=1[v][a]'
    run(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', fc, '-map', '[v]', '-map', '[a]', '-c:v', 'libx264',
         '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out])
    sh = out.with_name(out.stem + '.sheet.jpg')
    sheet(out, sh, n=12)
    print(f'\nDONE  {out}  ({duration(out):.1f} s of {total:.1f} s)\ncheck {sh}  (red = covered by the Instagram UI)')


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'prep':
        fit = sys.argv[sys.argv.index('--fit') + 1] if '--fit' in sys.argv else 'pad'
        prep(sys.argv[2], fit)
    elif len(sys.argv) == 2:
        build(sys.argv[1])
    else:
        sys.exit(__doc__)

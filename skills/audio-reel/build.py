#!/usr/bin/env python3
"""audio-reel: a full-length 9:16 reel from AUDIO ONLY (a voice memo, podcast clip, WhatsApp voice note) plus whatever
the user sends with it: photos, short video clips, a logo, an avatar. Pictures change on the words they belong to with
a slow zoom, big karaoke captions sit in the middle, an equalizer moves with the voice, and a hook title opens it.

    <kit>/.venv/bin/python build.py prep <audio or video>     # -> <stem>.voice.mp4 (the audio on a blank 9:16 frame)
    <kit>/.venv/bin/python build.py <spec.json>

Spec (see SKILL.md):
  video: "memo.voice.mp4" (the file prep wrote), out
  scenes: [{"src": "a.jpg", "at": 0}, {"src": "b.mp4", "at": "ঢাকার"}, ...]   images or clips, each from `at` to the next
  layout: "full" | "card"          full-bleed pictures, or a rounded card on a blurred copy
  theme: {"bg": "#101418", "accent": "#FFD400"}
  hook: {"text": "একটা *কৌশল*", "until": 3.0}
  speaker: {"name": "নিরব", "handle": "@niruvai", "avatar": "me.jpg"}
  logo: "logo.png"
  keys: ["কৌশল"]                   caption words in the accent colour
  caption_top: 1060, waveform: true (the equalizer)
"""
import html
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'kit'))
from reel import Job, Comp, FPS, W, H, duration, rich, run, word_caps  # noqa: E402

VIDEO_EXT = {'.mp4', '.mov', '.m4v', '.webm', '.mkv'}


def prep(src):
    """the audio of any file on a blank 1080x1920 frame, so the shared kit (transcript, words, render) can use it"""
    src = Path(src).resolve()
    out = src.with_name(src.stem + '.voice.mp4')
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c=black:s={W}x{H}:r={FPS}', '-i', src,
         '-map', '0:v', '-map', '1:a:0', '-shortest', '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'stillimage',
         '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', out])
    print(f'wrote {out}  ({duration(out):.1f} s). Run words on it, then write the spec with "video": "{out.name}".')
    return out


BARS = 28


def levels(clip, bars=BARS):
    """per video frame, the loudness of `bars` frequency bands (0-9), as one string per frame"""
    import numpy as np
    sr = 16000
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(clip), '-vn', '-ac', '1', '-ar', str(sr), '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768
    hop, win = sr // FPS, 1024
    edges = np.geomspace(90, 5000, bars + 1)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    idx = [(freqs >= lo) & (freqs < hi) for lo, hi in zip(edges, edges[1:])]
    rows, wnd = [], np.hanning(win)
    for f in range(int(len(x) / hop)):
        seg = x[f * hop: f * hop + win]
        if len(seg) < win:
            seg = np.pad(seg, (0, win - len(seg)))
        mag = np.abs(np.fft.rfft(seg * wnd))
        rows.append([float(mag[m].mean()) if m.any() else 0.0 for m in idx])
    a = np.log1p(np.array(rows) * 4)
    a = a / (np.percentile(a, 99) or 1)
    q = np.clip(np.round(a * 9), 0, 9).astype(int)
    return [''.join(map(str, r)) for r in q]


def eq_html(c, clip, colour, top=1250, width=880, height=150):
    """an equalizer of BARS bars that follows the voice; driven from the timeline so every rendered frame is exact"""
    rows = levels(clip, BARS // 2)   # mirrored: low voices in the middle, highs at the edges
    bw = width / BARS
    c.css.append(f'''#eq{{position:absolute;left:{(W - width) / 2:.0f}px;top:{top}px;width:{width}px;height:{height}px;display:flex;
align-items:center;justify-content:space-between}}
#eq i{{display:block;width:{bw * .56:.1f}px;height:8px;border-radius:{bw:.0f}px;background:{colour};box-shadow:0 0 18px {colour}66}}''')
    c.body.append('<div id="eq">' + '<i></i>' * BARS + '</div>')
    c.js.append(f'''(function(){{const L={rows!r};const bars=document.querySelectorAll("#eq i");
tl.eventCallback("onUpdate",function(){{const r=L[Math.min(L.length-1,Math.max(0,Math.round(tl.time()*{FPS})))]||"";
for(let k=0;k<bars.length;k++){{const v=+(r[Math.floor(Math.abs(k-(bars.length-1)/2))]||0);bars[k].style.height=(8+v*{(height - 8) / 9:.1f})+"px";}}}});}})();''')


def scene_html(c, j, i, src, a, b, layout):
    d = max(0.1, b - a)
    is_video = src.suffix.lower() in VIDEO_EXT
    if is_video:
        media = c.video(src, 'position:absolute;inset:0;width:100%;height:100%;object-fit:cover', f'sv{i}', start=a, dur=d)
    else:
        media = f'<img src="{c.asset(src)}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover">'
    if layout == 'card':
        back = (f'<img src="{c.asset(src)}" style="position:absolute;inset:-60px;width:calc(100% + 120px);height:calc(100% + 120px);'
                f'object-fit:cover;filter:blur(38px) brightness(.55)">' if not is_video else '')
        el = (f'<div class="sc" id="s{i}">{back}<div class="cd" id="k{i}">{media}</div></div>')
    else:
        el = f'<div class="sc" id="s{i}"><div class="kb" id="k{i}">{media}</div></div>'
    c.body.append(el)
    fade = 0.0 if i == 0 else 0.3
    c.js.append(f'tl.set("#s{i}",{{autoAlpha:1}},{max(0, a - fade):.3f});')
    if fade:
        c.js.append(f'tl.fromTo("#s{i}",{{autoAlpha:0}},{{autoAlpha:1,duration:{fade}}},{a - fade:.3f});')
    c.js.append(f'tl.set("#s{i}",{{autoAlpha:0}},{b + 0.35:.3f});')
    zoom = (1.0, 1.12) if i % 2 == 0 else (1.12, 1.0)
    c.js.append(f'tl.fromTo("#k{i}",{{scale:{zoom[0]}}},{{scale:{zoom[1]},duration:{d + 0.35:.3f},ease:"none"}},{max(0, a - fade):.3f});')


def build(spec_path):
    j = Job(spec_path, 'audio-reel')
    c = Comp(j)
    th = {'bg': '#101418', 'accent': '#FFD400', **(j.get('theme') or {})}
    acc = th['accent']
    layout = j.get('layout', 'full')
    top = int(j.get('caption_top', 1060))

    c.css.append(f'''
#root{{background:{th['bg']}}}
#grad{{position:absolute;inset:0;background:radial-gradient(120% 70% at 50% 35%,{th['bg']}00 0%,{th['bg']} 85%),
  linear-gradient(160deg,{acc}22,{th['bg']} 60%)}}
.sc{{position:absolute;inset:0;overflow:hidden;visibility:hidden}}
.kb{{position:absolute;inset:0;transform-origin:50% 40%}}
.cd{{position:absolute;left:90px;right:90px;top:250px;height:720px;border-radius:36px;overflow:hidden;
  box-shadow:0 30px 70px rgba(0,0,0,.5);transform-origin:50% 50%}}
#shade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.45) 0%,rgba(0,0,0,0) 22%,rgba(0,0,0,0) 42%,
  rgba(0,0,0,.72) 62%,rgba(0,0,0,.82) 100%)}}
#hook{{position:absolute;left:70px;right:70px;top:300px;text-align:center;font:900 96px/1.12 'Archivo Black';color:#fff;
  -webkit-text-stroke:10px #000;paint-order:stroke fill;text-shadow:0 6px 18px rgba(0,0,0,.5)}}
#who{{position:absolute;left:0;width:{W}px;top:1440px;display:flex;justify-content:center;align-items:center;gap:16px;
  font:700 34px 'Inter';color:#fff}}
#who img{{width:64px;height:64px;border-radius:50%;object-fit:cover;border:3px solid #fff}}
#who .h{{font:500 28px 'Inter';color:rgba(255,255,255,.75)}}
#logo{{position:absolute;right:60px;top:240px;width:120px;height:120px;object-fit:contain;opacity:.92}}
.ak{{position:absolute;left:60px;width:960px;top:{top}px;text-align:center;visibility:hidden;font:800 88px/1.18 'TikTok Sans';
  color:#fff;-webkit-text-stroke:9px #000;paint-order:stroke fill;text-shadow:0 6px 16px rgba(0,0,0,.45)}}
.ak span.k{{color:{acc}}}
''')
    c.body.append('<div id="grad"></div>')

    scenes = j.get('scenes') or []
    if scenes:
        times = [j.t(s.get('at'), 0) for s in scenes]
        order = sorted(range(len(scenes)), key=lambda i: times[i])
        for n, i in enumerate(order):
            src = j.path(scenes[i]['src'])
            if not src.exists():
                sys.exit(f'scene not found: {src}')
            a = times[i]
            b = times[order[n + 1]] if n + 1 < len(order) else j.dur
            scene_html(c, j, n, src, a, b, layout)
        c.body.append('<div id="shade"></div>')

    hook = j.get('hook') or {}
    if hook.get('text'):
        t = rich(hook['text']).replace('<em>', f'<span style="color:{acc}">').replace('</em>', '</span>')
        until = min(float(hook.get('until', 3.0)), j.dur)
        c.body.append(f'<div id="hook">{t}</div>')
        c.js.append('tl.fromTo("#hook",{scale:.7,autoAlpha:0},{scale:1,autoAlpha:1,duration:.32,ease:"back.out(1.8)"},0.02);')
        c.js.append(f'tl.to("#hook",{{autoAlpha:0,y:-30,duration:.25}},{max(0.4, until - 0.25):.3f});')

    if j.get('logo'):
        c.body.append(f'<img id="logo" src="{c.asset(j.path(j.get("logo")))}">')

    if j.get('waveform', True):
        eq_html(c, j.clip, acc)

    sp = j.get('speaker') or {}
    if sp.get('name'):
        av = f'<img src="{c.asset(j.path(sp["avatar"]))}">' if sp.get('avatar') else ''
        hd = f'<span class="h">{html.escape(sp.get("handle", ""))}</span>' if sp.get('handle') else ''
        c.body.append(f'<div id="who">{av}<span>{html.escape(sp["name"])}</span>{hd}</div>')

    word_caps(c, j.words, 'ak', '', maxw=3, maxc=16, keys=j.get('keys') or [], pop=(0.8, 0.18),
              karaoke_dim='rgba(255,255,255,.55)')
    c.css.append(f'.ak span.w span.k, .ak span.k{{color:{acc}}}')
    j.finish(c)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'prep':
        prep(sys.argv[2])
    elif len(sys.argv) == 2:
        build(sys.argv[1])
    else:
        sys.exit(__doc__)

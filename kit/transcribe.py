#!/usr/bin/env python3
"""Transcribe a clip with Groq Whisper, keeping word-level timestamps.

    python kit/transcribe.py <video> [--out file.json] [--language en]

Writes <video dir>/<stem>.transcript.json (Groq's verbose_json: segments + words, times in seconds from the
start of the video). Needs GROQ_API_KEY (free at console.groq.com). Long videos are sent in 10-minute chunks.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

MODEL = 'whisper-large-v3'
CHUNK = 600
# a messy priming prompt keeps Whisper verbatim (repeats and fillers stay, so the word times stay honest)
PROMPT = 'Um, so, uh, the the thing is, wait, okay. So, like, verbatim.'


def duration(video):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                          '-of', 'default=nw=1:nk=1', str(video)]))


def audio(video, dst, start, dur):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(start), '-i', str(video), '-t', str(dur),
                    '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'flac', str(dst)], check=True)


def call(client, path, language):
    kw = dict(file=(path.name, path.read_bytes()), model=MODEL, response_format='verbose_json',
              timestamp_granularities=['word', 'segment'], temperature=0.0, prompt=PROMPT)
    if language:
        kw['language'] = language
    if language == 'bn':
        # an English priming prompt pushes Whisper to translate; prime it with messy spoken Bangla instead
        kw['prompt'] = 'আচ্ছা, তো, মানে, এই এই ব্যাপারটা হলো, দাঁড়াও, ঠিক আছে। তো, মানে, হুবহু।'
    r = client.audio.transcriptions.create(**kw)
    return r.model_dump() if hasattr(r, 'model_dump') else dict(r)


GAP = 3.0        # a hole this long between words is checked for missed speech
SPEECH = 1.5     # re-transcribe it if at least this many seconds of it are not silent


def voiced(video, start, end):
    """seconds of non-silent audio between start and end (ffmpeg silencedetect)"""
    r = subprocess.run(['ffmpeg', '-v', 'info', '-hide_banner', '-nostats', '-ss', f'{start:.3f}', '-i', str(video),
                        '-t', f'{end - start:.3f}', '-vn', '-af', 'silencedetect=noise=-35dB:d=0.4', '-f', 'null', '-'],
                       capture_output=True, text=True)
    silent = sum(float(x.split('silence_duration:')[1].split()[0]) for x in r.stderr.splitlines() if 'silence_duration:' in x)
    return max(0.0, (end - start) - silent)


def fill_gaps(client, video, words, segments, total, language, tmp):
    """Whisper sometimes skips 10-30 s of speech (often after a pause or with music under it).
    Find long holes that still have voice in them and transcribe each hole on its own."""
    edges = [0.0] + [x for w in words for x in (w['start'], w['end'])] + [total]
    holes = [(edges[i], edges[i + 1]) for i in range(0, len(edges) - 1, 2) if edges[i + 1] - edges[i] >= GAP]
    added = 0
    for a, b in holes:
        if voiced(video, a, b) < SPEECH:
            continue
        s0, s1 = max(0.0, a - 0.2), min(total, b + 0.2)
        f = Path(tmp) / f'gap{int(s0 * 100)}.flac'
        audio(video, f, s0, s1 - s0)
        r = call(client, f, language)
        new = [dict(word=w['word'], start=round(w['start'] + s0, 3), end=round(w['end'] + s0, 3))
               for w in r.get('words') or [] if a - 0.05 <= w['start'] + s0 < b]
        if new:
            print(f'  filled a skipped stretch {a:.1f}-{b:.1f} s ({len(new)} words)', flush=True)
            words.extend(new)
            segments.extend(dict(start=round(x['start'] + s0, 3), end=round(x['end'] + s0, 3), text=x['text'])
                            for x in r.get('segments') or [] if a - 0.05 <= x['start'] + s0 < b)
            added += len(new)
    words.sort(key=lambda w: w['start'])
    segments.sort(key=lambda x: x['start'])
    return added


def transcribe(video, out=None, language=None):
    from groq import Groq
    if not os.environ.get('GROQ_API_KEY'):
        sys.exit('GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys and export it.')
    video = Path(video).resolve()
    out = Path(out) if out else video.with_name(video.stem + '.transcript.json')
    client = Groq()
    total = duration(video)
    words, segments, text = [], [], []
    with tempfile.TemporaryDirectory() as tmp:
        t = 0.0
        while t < total - 0.05:
            dur = min(CHUNK, total - t)
            a = Path(tmp) / f'chunk{int(t)}.flac'
            audio(video, a, t, dur)
            r = call(client, a, language)
            for w in r.get('words') or []:
                words.append(dict(word=w['word'], start=round(w['start'] + t, 3), end=round(w['end'] + t, 3)))
            for s in r.get('segments') or []:
                segments.append(dict(start=round(s['start'] + t, 3), end=round(s['end'] + t, 3), text=s['text']))
            text.append(r.get('text', ''))
            t += dur
        if fill_gaps(client, video, words, segments, total, language, tmp):
            text = [' '.join(w['word'].strip() for w in words)]
    data = dict(text=' '.join(x.strip() for x in text), segments=segments, words=words, duration=total, model=MODEL)
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('--out')
    ap.add_argument('--language')
    a = ap.parse_args()
    p = transcribe(a.video, a.out, a.language or os.environ.get('REEL_LANGUAGE') or None)
    d = json.loads(p.read_text())
    print(f'wrote {p}  ({len(d["words"])} words)')
    for s in d['segments']:
        print(f'{s["start"]:7.2f}-{s["end"]:7.2f}  {s["text"].strip()}')

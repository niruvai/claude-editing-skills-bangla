---
name: audio-reel
description: Makes a full-length 9:16 reel from AUDIO ONLY (a voice memo, podcast clip, WhatsApp voice note, or the sound of any video) plus the user's photos, short clips, logo and avatar. Pictures change on the words they belong to, big Bangla karaoke captions, a voice equalizer, a hook title. Use when the user runs /audio-reel or sends audio and wants a reel.
---

# /audio-reel

```
┌──────────────┐  photos / clips change on the words they belong to (slow zoom)
│ HOOK TITLE  ●│  ← logo
│   (photo)    │
│ বড় ক্যাপশন   │  ← karaoke: each word lights up as it is said, key words in the accent colour
│ ▁▃▇█▇▃▁ ---  │  ← equalizer that follows the voice
│ (o) নাম @handle│
└──────────────┘
```

## First use
This skill's folder is the "Base directory" Claude Code shows when it loads it.
```bash
SKILL_DIR="<base directory of this skill>"
KIT=$(python3 -c 'import os,sys;print(os.path.realpath(os.path.join(sys.argv[1],"..","..","kit")))' "$SKILL_DIR")
PY="$KIT/.venv/bin/python"; [ -x "$PY" ] || bash "$KIT/setup.sh"
```
`GROQ_API_KEY` must be set to transcribe. For Bangla set `REEL_LANGUAGE=bn` and write all on-screen text in Bangla.

## Steps
1. **Gather.** Find everything the user sent: the audio (m4a, mp3, wav, ogg/opus, or a video whose sound to use), photos, short video clips (B-roll), a logo, an avatar, a name or @handle. Copy them into one working folder outside any repo. Never invent pictures, logos, numbers or names; if the user sent no pictures, the reel uses the theme background only. Ask once for a name/handle only if the user seems to want it.
2. **Prep.** `"$PY" "$SKILL_DIR/build.py" prep <audio>` writes `<stem>.voice.mp4` (the audio on a blank 9:16 frame).
3. **Words.** `"$PY" "$KIT/reel.py" words <stem>.voice.mp4`. Whisper often misspells Bangla: fix wrong words in `<stem>.voice.transcript.json` (change only `word`, keep times) and run `words` again. If a long stretch is missing, delete the transcript and run `words` again.
4. **Look at the pictures** (open each image; for a clip, `"$PY" "$KIT/reel.py" frame <clip> 1 f.jpg`). Match each one to the sentence it illustrates best. Order follows the talk, not the file names.
5. **Spec.** Write `<stem>.audio-reel.json` (below). Each scene starts on the first word of its sentence and lasts until the next scene. 3 to 6 s per picture feels right; reuse a picture rather than rush. Put the strongest picture first.
6. **Build.** `"$PY" "$SKILL_DIR/build.py" <spec.json>`.
7. **Check** the sheet: the hook clears the top 220 px, the captions never cover a face in a picture (move `caption_top` or use `"layout": "card"`), the name row stays above 1500. Send the user the mp4 and the sheet.

## Spec
```json
{
  "video": "memo.voice.mp4",
  "out": "memo.audio-reel.mp4",
  "scenes": [
    {"src": "photo1.jpg", "at": 0},
    {"src": "street.mp4", "at": "ঢাকার"},
    {"src": "photo2.jpg", "at": "চলো"}
  ],
  "layout": "full",
  "theme": {"bg": "#101418", "accent": "#FFD400"},
  "hook": {"text": "একটা *জরুরি* কথা", "until": 2.9},
  "speaker": {"name": "নিরব", "handle": "@niruvai", "avatar": "me.jpg"},
  "logo": "logo.png",
  "keys": ["যানজট", "সমাধান"],
  "caption_top": 1060
}
```
- `scenes[].at`: seconds, or a spoken word (`"ঢাকার"`, `"ঢাকার#2"`, `"ঢাকার+0.2"`). Clips play muted from their start; keep them at least as long as their scene.
- `layout`: `full` (pictures fill the frame, darkened at the bottom for the captions) or `card` (a rounded picture in the top half on a blurred copy of itself; best for screenshots, posters and pictures with faces or text).
- `theme.accent` colours the key words, the hook accent and the equalizer. Match it to the user's brand or logo if they have one.
- `hook.text`: 2 to 5 words, `*word*` in the accent colour; `until` is the end of the first sentence.
- `speaker`, `logo`, `scenes` are all optional. `"waveform": false` hides the equalizer.

## Taste
- The voice is the star: pictures support the sentence being said, they never fight it.
- No stock-looking filler. Fewer real pictures shown longer beat many random ones.
- Key words are the 2 to 5 that carry the meaning, not every noun.

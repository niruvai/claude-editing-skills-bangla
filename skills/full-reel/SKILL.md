---
name: full-reel
description: Turns a WHOLE talking-head clip (any length, any aspect) into one finished full-length reel. Captions run through the entire clip, a hook title opens it, and at the 1 to 3 strongest moments an effect segment made with /explainer, /split-screen, /storytelling, /ranking-list or /behind-the-person is dropped in. Use when the user runs /full-reel, or wants the full video edited rather than a short 3 to 8 second cut.
---

# /full-reel

```
 0s ─────────── hook ───────── captions ──┬── EFFECT (explainer…) ──┬── captions ───── end
 │ big title for the first seconds         │ made by its own skill   │ to the last word │
```
The other skills each make ONE short moment (3 to 8 s). This one keeps the whole clip: captions everywhere, and those moments placed where they belong. The result is as long as the clip.

## First use
This skill's folder is the "Base directory" Claude Code shows when it loads it.
```bash
SKILL_DIR="<base directory of this skill>"
KIT=$(python3 -c 'import os,sys;print(os.path.realpath(os.path.join(sys.argv[1],"..","..","kit")))' "$SKILL_DIR")
PY="$KIT/.venv/bin/python"; [ -x "$PY" ] || bash "$KIT/setup.sh" --cutout
```
`GROQ_API_KEY` must be set to transcribe. Needs ffmpeg and Node. For Bangla clips set `REEL_LANGUAGE=bn` and write all on-screen text in Bangla.

## Steps
1. **Shape.** If the clip is not 9:16 (a square phone video, a landscape one), run `"$PY" "$SKILL_DIR/build.py" prep <video>` once. It writes `<stem>.916.mp4` (the clip a little above the middle on a dark backdrop, which keeps cutouts clean; `--fit blur` uses a blurred copy instead). Use that file for EVERY step below, including the effect skills, so all parts share one frame.
2. **Words.** Run `"$PY" "$KIT/reel.py" words <video>`. Read the whole transcript.
   - Whisper often misspells Bangla. Fix wrong words in `<video stem>.transcript.json` (change only `word`, keep `start`/`end`) and run `words` again.
   - If a long stretch of speech is missing, delete the transcript and run `words` again; the transcriber re-checks skipped stretches.
3. **Plan.** Split the talk into its beats and pick 1 to 3 moments for effects (at most one per 10 to 15 s, never back to back). Each moment is whole sentences, 3 to 8 s, and suits one skill:
   - a before/after, a comparison or a short list → `/explainer`
   - a step being shown, a tool or a screen → `/split-screen`
   - proof or a small story with pictures → `/storytelling`
   - things being ranked → `/ranking-list`
   - a number or result about the speaker → `/behind-the-person`
   Everything else stays as the captioned clip. Tell the user the plan in one or two lines.
4. **Effects.** For each moment, load that skill and follow its SKILL.md on the same video, with `start` and `end` set to the moment (source seconds from `words`) and `out` set to `<stem>.fx1.mp4`, `<stem>.fx2.mp4` and so on. Check each sheet as that skill says.
5. **Spec.** Write `<stem>.full-reel.json` (below).
6. **Build.** Run `"$PY" "$SKILL_DIR/build.py" <spec.json>`. It renders only the stretches between the effects (captions and hook), then joins everything in order with the original voice. Rendering takes about as long as the captioned stretches on a laptop, two to four times that in a cloud session.
7. **Check** `<out>.sheet.jpg`: the hook clears the top 220 px, captions sit under the face and above 1500, nothing jumps at the joins. Send the user the mp4 and the sheet.

## Spec
```json
{
  "video": "my-clip.916.mp4",
  "out": "my-clip.full-reel.mp4",
  "hook": {"text": "প্রকৌশলী থেকে *নেতা*", "until": 3.0},
  "keys": ["লন্ডনে", "মেয়র", "পরিবর্তন"],
  "caption_top": 1380,
  "inserts": [
    {"file": "my-clip.fx1.mp4", "start": 21.12},
    {"file": "my-clip.fx2.mp4", "start": 30.40}
  ]
}
```
- `inserts[].start` is the `start` of that effect's own spec (source seconds). Its length is read from the file, so the voice continues without a gap or a repeat. Inserts must not overlap.
- `hook.text`: 2 to 5 words, the promise of the video. `*word*` turns yellow. `until` is when it leaves (end of the first sentence is good).
- `keys`: 2 to 5 caption words to turn yellow, the ones that carry the meaning.
- `caption_top`: 1380 by default. For a `prep`ped square clip that is just under the picture; for a real 9:16 clip put it under the mouth and keep it under 1500 − 90.
- No `inserts` is fine: the whole clip with a hook and captions.

## Taste
- Fewer, better effects. One strong effect in a 30 s reel beats three weak ones.
- Effects land on the sentence that makes the point, not on the intro.
- Keep the closing question or call to action as plain captioned clip; it should feel personal.

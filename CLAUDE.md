# Bangla editing skills

The skills live in `skills/` and are linked into `.claude/skills/`, so `/full-reel` (the whole clip as one reel), `/trial-reels`, `/explainer`, `/split-screen`, `/storytelling`, `/ranking-list`, `/behind-the-person` and the five photographic styles work in this repo, including cloud sessions (the Claude app's Code tab).

- Clips are Bangla by default: if `REEL_LANGUAGE` is not set, run with `REEL_LANGUAGE=bn`. Write all on-screen text in Bangla.
- A video the user attached in the app is an uploaded file; find it by name (often under `/mnt/user-data/uploads/`) and copy it into a working folder outside the repo before building, so outputs never land in the repo.
- In a cloud session, send every finished `.mp4` (and its `.sheet.jpg`) back to the user; they cannot see the session's disk.
- If transcription fails with a connection error, `api.groq.com` is not allowed in the cloud environment, or `GROQ_API_KEY` is missing. Tell the user to add both in the environment settings (see the README), and do not commit anything to work around it.
- Never commit rendered videos, transcripts or the user's media.
- When the user wants their whole video edited (not one short moment), use `/full-reel`.

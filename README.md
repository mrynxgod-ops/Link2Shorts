# Link2Shorts

Turn an authorized, publicly accessible video URL into vertical Shorts using GitHub Actions.

## Run it

1. Open the repository's **Actions** tab.
2. Select **Link2Shorts** → **Run workflow**.
3. Paste a public video URL that you own or are authorized to reuse.
4. Choose 1–8 clips and a Whisper model, then run.
5. When the workflow finishes, download the `link2shorts-clips` artifact from the run page.

## What it does

- Downloads one video (playlists are disabled) with yt-dlp.
- Transcribes speech with faster-whisper.
- Ranks 22–45 second transcript windows using a simple hook/wording heuristic.
- Renders 1080×1920 MP4 clips with burned-in captions and source audio.
- Saves a `manifest.json` with timestamps and transcript excerpts.

## Important limitations

- Use only media you own or have explicit permission to reuse. This project does not bypass DRM, sign-in, age gates, geo-restrictions, paywalls, or other access controls.
- A YouTube URL may fail to download because of availability, platform changes, rate limits, or access restrictions. Only publicly accessible content is supported.
- Clip selection is transcript-based; it does not understand the visual scene, track a speaker, or guarantee views/virality.
- The vertical render uses a centered crop, so subjects near the edges may be cut off.
- GitHub-hosted runners are temporary batch workers, not an always-on server. Artifacts are retained for 7 days.
- Long/high-resolution videos may exceed runner time, memory, or disk limits. The `small` Whisper model is slower and uses more resources.

## Local use

Install FFmpeg and Python 3.11+, then:

```bash
pip install -r requirements.txt
python clipper.py --url "YOUR_AUTHORIZED_VIDEO_URL" --count 3 --model base
```

Outputs are written to `output/`.

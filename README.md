# Link2Shorts

Turn an authorized video URL into vertical Shorts. **No Termux is required.** The easiest phone-friendly route is the Google Colab notebook: processing runs in Colab's temporary cloud runtime, so your Android phone does not do the video rendering.

## Recommended: Google Colab (no Termux)

1. Open the notebook: [Link2Shorts_Colab.ipynb](https://github.com/mrynxgod-ops/Link2Shorts/blob/main/Link2Shorts_Colab.ipynb).
2. Tap **Open in Colab** (or download the notebook and upload it to [Google Colab](https://colab.research.google.com/)).
3. Run the setup cell, then the next cell.
4. Enter a video URL you own or are authorized to process, choose 1–8 clips and a Whisper model.
5. Run the final cell to download a ZIP containing the generated MP4 Shorts.

Start with the **tiny** Whisper model for a lighter/faster run. Colab free sessions have resource, time and availability limits; this is not unlimited cloud processing. Keep the notebook tab open while processing.

## Alternative: GitHub Actions

1. Open the repository's **Actions** tab.
2. Select **Link2Shorts** → **Run workflow**.
3. Enter a public video URL that you own or are authorized to reuse.
4. Choose 1–8 clips and a Whisper model.
5. When the workflow finishes, download the `link2shorts-clips` artifact.

GitHub-hosted runners may be blocked by YouTube's bot checks. A failed download is not necessarily a code problem.

## Optional: Android Termux

Termux is an optional local-processing route, not a requirement. It uses the phone's CPU, memory, battery and storage. See `termux_clipper.py` if you specifically want on-device processing.

## What it does

- Retrieves one video with yt-dlp (playlists are disabled).
- Transcribes speech with faster-whisper in Colab/GitHub Actions or whisper.cpp in Termux.
- Ranks 22–45 second transcript windows using a simple hook/wording heuristic.
- Renders 1080×1920 MP4 clips with burned-in captions and source audio.
- Saves a `manifest.json` with timestamps and transcript excerpts.

## Important limitations

- **A URL is not guaranteed to work.** YouTube can block hosted cloud IPs or require sign-in. If the log says "Sign in to confirm you're not a bot", this cloud route cannot promise to retrieve that video.
- This project does not bypass DRM, sign-in, age gates, geo-restrictions, paywalls or other access controls. Use only content you own or have permission to process.
- If YouTube blocks a URL, use a permitted direct media URL or a video file you are authorized to process; do not attempt to bypass platform restrictions.
- Colab free runtimes can disconnect, impose usage limits or become unavailable. GitHub Actions also has usage limits and artifacts are retained for 7 days.
- Clip selection is transcript-based; it does not understand visual context, track speakers, or guarantee virality.
- The vertical render uses a centered crop, so subjects near the edges may be cut off.
- Long/high-resolution videos can take a long time and require substantial temporary storage.

## Desktop local use

Install FFmpeg and Python 3.11+, then:

```bash
pip install -r requirements.txt
python clipper.py --url "YOUR_AUTHORIZED_VIDEO_URL" --count 3 --model tiny
```

Outputs are written to `output/`.

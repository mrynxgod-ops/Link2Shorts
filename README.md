# Link2Shorts

Turn an authorized video URL into vertical Shorts. The project has two execution modes:

- **GitHub Actions:** temporary hosted runner; YouTube may block requests from hosted IPs.
- **Android Termux:** free on-device worker. Processing happens on your phone; no paid cloud server or API is required.

## Android Termux setup (₹0)

These commands build the open-source whisper.cpp speech recognizer locally. Run them in Termux:

```bash
pkg update -y && pkg upgrade -y
pkg install -y python ffmpeg git cmake clang make pkg-config curl
python -m pip install --upgrade pip
python -m pip install -U yt-dlp

cd ~
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j 2
cp build/bin/whisper-cli $PREFIX/bin/

cd ~
if [ ! -d Link2Shorts ]; then
  git clone https://github.com/mrynxgod-ops/Link2Shorts.git
fi
mkdir -p ~/Link2Shorts/models
cd ~/Link2Shorts
curl -L 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin' -o models/ggml-base.bin
```

Then run the worker:

```bash
cd ~/Link2Shorts
python termux_clipper.py --url "YOUR_AUTHORIZED_VIDEO_URL" --count 3
```

Generated MP4 files and a manifest are saved in `~/Link2Shorts/output/`. Use `--count 1` through `--count 8`. The default Whisper base model is a reasonable starting point for an 8 GB phone. Keep the phone plugged in, close heavy apps, and allow storage space for the source video, temporary WAV audio, model and output clips.

### If you need a smaller model

Download the tiny model and use it to reduce memory and processing time:

```bash
cd ~/Link2Shorts
curl -L 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin' -o models/ggml-tiny.bin
python termux_clipper.py --url "YOUR_AUTHORIZED_VIDEO_URL" --count 3 --model models/ggml-tiny.bin
```

## GitHub Actions mode

1. Open the repository's **Actions** tab.
2. Select **Link2Shorts** → **Run workflow**.
3. Enter a public video URL that you own or are authorized to reuse.
4. Choose 1–8 clips and a Whisper model.
5. When the workflow finishes, download the `link2shorts-clips` artifact.

## What it does

- Retrieves one video with yt-dlp (playlists are disabled).
- Transcribes speech with faster-whisper in Actions or whisper.cpp on Termux.
- Ranks 22–45 second transcript windows using a simple hook/wording heuristic.
- Renders 1080×1920 MP4 clips with burned-in captions and source audio.
- Saves a `manifest.json` with timestamps and transcript excerpts.

## Important limitations

- **Free does not mean unlimited:** your phone does the Termux processing, so speed depends on CPU, free RAM, battery, storage and video length.
- A YouTube URL can still fail if YouTube blocks the request, requires sign-in, or restricts access. This tool does not bypass DRM, sign-in, age gates, geo-restrictions, paywalls or other access controls. Use only content you own or have permission to process.
- If YouTube blocks a URL on your phone, do not try to bypass access controls. Use a permitted direct media URL or a source you are authorized to download.
- Clip selection is transcript-based; it does not understand visual context, track speakers, or guarantee virality.
- The vertical render uses a centered crop, so subjects near the edges may be cut off.
- GitHub-hosted runners are temporary and have usage limits; artifacts are retained for 7 days.
- Long/high-resolution videos can take a long time and require substantial temporary storage. Delete old files from `work/` and `output/` when finished.

## Desktop local use

Install FFmpeg and Python 3.11+, then:

```bash
pip install -r requirements.txt
python clipper.py --url "YOUR_AUTHORIZED_VIDEO_URL" --count 3 --model base
```

Outputs are written to `output/`.

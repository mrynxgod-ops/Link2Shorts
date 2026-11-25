#!/usr/bin/env python3
"""Termux-friendly URL-to-Shorts worker using yt-dlp, FFmpeg and whisper.cpp."""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

WORK = Path("work")
OUT = Path("output")
HOOK_WORDS = {
    "secret", "insane", "crazy", "never", "impossible", "mistake", "truth",
    "shocking", "suddenly", "finally", "danger", "survived", "biggest",
    "worst", "best", "million", "billion", "destroyed", "caught"
}


def run(command):
    print("+", " ".join(map(str, command)), flush=True)
    subprocess.run(command, check=True)


def require(name):
    if not shutil.which(name):
        raise SystemExit(f"Missing command: {name}. Install it first in Termux.")


def download(url):
    WORK.mkdir(exist_ok=True)
    template = str(WORK / "source.%(ext)s")
    run([
        "yt-dlp", "--no-playlist", "--retries", "3", "--fragment-retries", "3",
        "-f", "best[height<=1080]/best", "--merge-output-format", "mp4",
        "-o", template, url
    ])
    files = [p for p in WORK.glob("source.*")
             if p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}]
    if not files:
        raise RuntimeError("No downloaded video found. Check URL access and yt-dlp output.")
    return max(files, key=lambda p: p.stat().st_size)


def parse_srt(path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r"\n\s*\n", raw.strip())
    rows = []
    def seconds(stamp):
        h, m, rest = stamp.split(":")
        s, ms = rest.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
    for block in blocks:
        lines = block.strip().splitlines()
        timing = next((line for line in lines if "-->" in line), None)
        if not timing:
            continue
        left, right = [x.strip().split()[0] for x in timing.split("-->")]
        idx = lines.index(timing)
        text = re.sub(r"\s+", " ", " ".join(lines[idx + 1:])).strip()
        text = re.sub(r"<[^>]+>", "", text)
        if text:
            rows.append({"start": seconds(left), "end": seconds(right), "text": text})
    return rows


def score_window(rows, start, end):
    chosen = [r for r in rows if r["end"] > start and r["start"] < end]
    text = " ".join(r["text"] for r in chosen)
    words = re.findall(r"\b[\w']+\b", text.lower())
    if len(words) < 18:
        return None
    score = min(len(words), 110) * 0.12
    score += sum(1.8 for w in words if w in HOOK_WORDS)
    score += min(sum(1 for w in words if w.isdigit()), 5) * 0.5
    score += text.count("?") * 0.8 + text.count("!") * 0.6
    if re.search(r"\b(i|we|my|our)\b", text.lower()):
        score += 1.0
    fillers = sum(words.count(w) for w in ("um", "uh", "like", "you", "know"))
    score -= min(fillers, 12) * 0.12
    return {"start": start, "end": end, "score": round(score, 2), "text": text}


def choose_clips(rows, count):
    first, last = min(r["start"] for r in rows), max(r["end"] for r in rows)
    candidates = []
    start = max(0.0, first - 2)
    while start + 22 <= last:
        item = score_window(rows, start, min(start + 45.0, last))
        if item:
            candidates.append(item)
        start += 12.0
    candidates.sort(key=lambda x: x["score"], reverse=True)
    selected = []
    for item in candidates:
        if all(item["end"] <= s["start"] or item["start"] >= s["end"] for s in selected):
            selected.append(item)
        if len(selected) >= count:
            break
    return sorted(selected, key=lambda x: x["start"])


def make_srt(rows, start, end, path):
    selected = [r for r in rows if r["end"] > start and r["start"] < end]
    def stamp(value):
        ms = int(round(max(0, value) * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    with path.open("w", encoding="utf-8") as f:
        for i, row in enumerate(selected, 1):
            a = max(0.0, row["start"] - start)
            b = max(a + 0.25, min(end - start, row["end"] - start))
            f.write(f"{i}\n{stamp(a)} --> {stamp(b)}\n{row['text']}\n\n")


def render(video, item, rows, index):
    OUT.mkdir(exist_ok=True)
    srt = WORK / f"clip_{index:02}.srt"
    target = OUT / f"short_{index:02}.mp4"
    make_srt(rows, item["start"], item["end"], srt)
    # FFmpeg subtitles filter uses the SRT file path; escape drive/special chars if paths are changed.
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        f"subtitles={srt.as_posix()}:force_style='FontName=Arial,FontSize=16,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,"
        "Outline=3,Shadow=1,Alignment=2,MarginV=120'"
    )
    run([
        "ffmpeg", "-y", "-ss", f"{item['start']:.3f}", "-i", str(video),
        "-t", f"{item['end'] - item['start']:.3f}", "-vf", vf,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        "-shortest", str(target)
    ])
    return target


def main():
    parser = argparse.ArgumentParser(description="Free on-device Link2Shorts worker for Termux")
    parser.add_argument("--url", required=True, help="Video URL you own or are authorized to reuse")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--model", default="models/ggml-base.bin")
    args = parser.parse_args()
    if not 1 <= args.count <= 8:
        parser.error("--count must be between 1 and 8")
    for command in ("yt-dlp", "ffmpeg", "whisper-cli"):
        require(command)
    model = Path(args.model)
    if not model.is_file():
        raise SystemExit(f"Whisper model not found: {model}. See Termux setup in README.")
    WORK.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    video = download(args.url)
    audio = WORK / "audio.wav"
    run(["ffmpeg", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(audio)])
    prefix = WORK / "transcript"
    run(["whisper-cli", "-m", str(model), "-f", str(audio), "-osrt", "-of", str(prefix)])
    srt_path = Path(str(prefix) + ".srt")
    if not srt_path.exists():
        raise RuntimeError("whisper.cpp did not create an SRT transcript.")
    rows = parse_srt(srt_path)
    if not rows:
        raise RuntimeError("No speech detected in this video.")
    clips = choose_clips(rows, args.count)
    if not clips:
        raise RuntimeError("Could not find enough speech-rich moments. Try a longer video.")
    manifest = {
        "source_file": video.name,
        "selection_note": "Transcript heuristic only; it does not inspect visuals or guarantee virality.",
        "clips": []
    }
    for i, item in enumerate(clips, 1):
        target = render(video, item, rows, i)
        manifest["clips"].append({**item, "file": target.name})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"SUCCESS: Created {len(clips)} Shorts in {OUT.resolve()}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Create transcript-ranked vertical clips from an authorized public video URL."""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

from faster_whisper import WhisperModel

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


def download(url):
    WORK.mkdir(exist_ok=True)
    template = str(WORK / "source.%(ext)s")
    run([
        "yt-dlp", "--no-playlist", "--no-warnings",
        "-f", "bv*+ba/b", "--merge-output-format", "mp4",
        "-o", template, url
    ])
    candidates = sorted(WORK.glob("source.*"), key=lambda p: p.stat().st_size, reverse=True)
    candidates = [p for p in candidates if p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}]
    if not candidates:
        raise RuntimeError("Download completed but no supported video file was found.")
    return candidates[0]


def transcribe(video, model_name):
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(video), vad_filter=True, word_timestamps=False)
    rows = []
    for seg in segments:
        text = re.sub(r"\s+", " ", seg.text).strip()
        if text:
            rows.append({"start": float(seg.start), "end": float(seg.end), "text": text})
    if not rows:
        raise RuntimeError("No speech was detected. Try another video or model.")
    return rows, info.language


def score_window(rows, start, end):
    chosen = [r for r in rows if r["end"] > start and r["start"] < end]
    text = " ".join(r["text"] for r in chosen)
    words = re.findall(r"\b[\w']+\b", text.lower())
    if len(words) < 18:
        return None
    score = 0.0
    score += min(len(words), 110) * 0.12
    score += sum(1.8 for w in words if w in HOOK_WORDS)
    score += min(sum(1 for w in words if w.isdigit()), 5) * 0.5
    score += text.count("?") * 0.8 + text.count("!") * 0.6
    if re.search(r"\b(i|we|my|our)\b", text.lower()):
        score += 1.0
    fillers = sum(words.count(w) for w in ("um", "uh", "like", "you", "know"))
    score -= min(fillers, 12) * 0.12
    return {"start": start, "end": end, "score": round(score, 2), "text": text}


def choose_clips(rows, count):
    first = min(r["start"] for r in rows)
    last = max(r["end"] for r in rows)
    duration = 45.0
    step = 12.0
    candidates = []
    start = max(0.0, first - 2)
    while start + 22 <= last:
        end = min(start + duration, last)
        item = score_window(rows, start, end)
        if item:
            candidates.append(item)
        start += step
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
    # Center crop to a 9:16 frame; this does not perform AI subject tracking.
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
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
        "-shortest", str(target)
    ])
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--model", choices=["tiny", "base", "small"], default="base")
    args = parser.parse_args()
    if not 1 <= args.count <= 8:
        parser.error("--count must be between 1 and 8")
    WORK.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    video = download(args.url)
    rows, language = transcribe(video, args.model)
    clips = choose_clips(rows, args.count)
    if not clips:
        raise RuntimeError("Could not find enough speech-rich clip windows.")
    manifest = {"source_file": video.name, "language": language, "selection_note": "Transcript heuristic only; not a guarantee of virality and does not inspect visual context.", "clips": []}
    for i, item in enumerate(clips, 1):
        target = render(video, item, rows, i)
        manifest["clips"].append({**item, "file": target.name})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Created {len(clips)} clip(s) in {OUT}/")


if __name__ == "__main__":
    main()

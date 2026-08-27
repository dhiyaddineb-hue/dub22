#!/usr/bin/env python3
"""Generate Arabic dubbed segments with Coqui XTTS v2 and mux them into a video.

XTTS v2 is loaded locally. The original audio is used only as a speaker reference;
the output video uses the generated Arabic track and does not retain the source speech.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def load_tts(device: str):
    try:
        from TTS.api import TTS
    except ImportError as exc:
        raise SystemExit("XTTS is not installed. Run: python3 -m pip install -r requirements-xtts.txt") from exc
    model = os.getenv("XTTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
    print(f"Loading {model} on {device} ...")
    return TTS(model_name=model, progress_bar=False).to(device)


def make_silence(path: Path, duration: float, sample_rate: int = 24000) -> None:
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r={sample_rate}:cl=mono", "-t", f"{duration:.3f}", str(path)])


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def tempo_filter(actual: float, budget: float) -> str:
    if actual <= budget or budget <= 0:
        return ""
    factor = actual / budget
    filters: list[str] = []
    while factor > 2.0:
        filters.append("atempo=2.0")
        factor /= 2.0
    filters.append(f"atempo={factor:.6f}")
    return ",".join(filters)


def mux_segments(video: Path, rendered: list[tuple[float, float, Path]], output: Path, duration: float) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="xtts_mix_") as temp:
        bed = Path(temp) / "bed.wav"
        make_silence(bed, duration)
        inputs = [video, bed, *[path for _, _, path in rendered]]
        filters = ["[1:a]anull[a0]"]
        labels = ["[a0]"]
        for index, (start, source_end, path) in enumerate(rendered, start=2):
            delay_ms = round(start * 1000)
            budget = max(0.05, source_end - start)
            actual = probe_duration(path)
            tempo = tempo_filter(actual, budget)
            label = f"a{index}"
            chain = f"[{index}:a]"
            if tempo:
                chain += tempo + ","
            chain += f"atrim=duration={budget:.3f},asetpts=PTS-STARTPTS,adelay={delay_ms}:all=1[{label}]"
            filters.append(chain)
            labels.append(f"[{label}]")
        filters.append("".join(labels) + f"amix=inputs={len(labels)}:duration=first:dropout_transition=0:normalize=0[aout]")
        command = ["ffmpeg", "-y"]
        for item in inputs:
            command += ["-i", str(item)]
        command += ["-filter_complex", ";".join(filters), "-map", "0:v:0", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output)]
        run(command)


def main() -> int:
    parser = argparse.ArgumentParser(description="Arabic XTTS v2 dubbing")
    parser.add_argument("--input", default="assets/input/source.mp4")
    parser.add_argument("--manifest", default="manifests/dialogue_ar.json")
    parser.add_argument("--output", default="outputs/arabic_dub_xtts_v2.mp4")
    parser.add_argument("--workdir", default="assets/xtts_segments")
    parser.add_argument("--device", default=os.getenv("XTTS_DEVICE", "cpu"), choices=("cpu", "cuda"))
    parser.add_argument("--duration", type=float, default=24.842)
    parser.add_argument("--temperature", type=float, default=0.65)
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()

    if args.device == "cuda":
        try:
            import torch
            if not torch.cuda.is_available():
                raise SystemExit("CUDA was requested but no CUDA device is available. Use --device cpu.")
        except ImportError as exc:
            raise SystemExit("PyTorch is required for XTTS v2.") from exc

    input_video = Path(args.input)
    manifest_path = Path(args.manifest)
    workdir = Path(args.workdir)
    if not input_video.is_file():
        raise SystemExit(f"Missing input video: {input_video}")
    if not manifest_path.is_file():
        raise SystemExit(f"Missing manifest: {manifest_path}")

    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    tts = load_tts(args.device)
    workdir.mkdir(parents=True, exist_ok=True)
    rendered: list[tuple[float, float, Path]] = []
    for segment in manifest["segments"]:
        reference = Path(segment["reference_audio"])
        if not reference.is_file():
            raise SystemExit(f"Missing reference audio for {segment['id']}: {reference}")
        output = workdir / f"{segment['id']}.wav"
        print(f"Generating {segment['id']} ({segment['speaker']}) ...")
        tts.tts_to_file(
            text=segment["text"],
            speaker_wav=str(reference),
            language="ar",
            file_path=str(output),
            split_sentences=False,
            temperature=args.temperature,
            length_penalty=1.0,
            repetition_penalty=2.0,
            top_k=50,
            top_p=0.85,
            speed=args.speed,
        )
        rendered.append((float(segment["start"]), float(segment.get("source_end", args.duration)), output))

    mux_segments(input_video, rendered, Path(args.output), args.duration)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Arabic dubbing with Chatterbox Multilingual V3.

The model performs zero-shot reference-voice conditioning for Arabic. This
script generates one clip per manifest segment, fits clips to their source
windows, and muxes a silent-bed Arabic track into the original video.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def load_model(device: str):
    try:
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    except ImportError as exc:
        raise SystemExit("Chatterbox is not installed. Run: python3 -m pip install -r requirements-chatterbox.txt") from exc
    import torch

    if device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA was requested but no CUDA device is available. Use --device cpu.")
    print(f"Loading Chatterbox Multilingual V3 on {device} ...")
    return ChatterboxMultilingualTTS.from_pretrained(device=device, t3_model="v3")


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def tempo_chain(actual: float, budget: float) -> str:
    if actual <= budget:
        return ""
    factor = actual / budget
    filters: list[str] = []
    while factor > 2.0:
        filters.append("atempo=2.0")
        factor /= 2.0
    filters.append(f"atempo={factor:.6f}")
    return ",".join(filters) + ","


def mux(video: Path, clips: list[tuple[float, float, Path]], output: Path, duration: float) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="chatterbox_mix_") as temp:
        bed = Path(temp) / "bed.wav"
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{duration:.3f}", str(bed)])
        inputs = [video, bed, *[path for _, _, path in clips]]
        filters = ["[1:a]anull[bed]"]
        labels = ["[bed]"]
        for index, (start, end, path) in enumerate(clips, start=2):
            budget = max(0.05, end - start)
            filter_text = f"[{index}:a]" + tempo_chain(probe_duration(path), budget)
            filter_text += f"atrim=duration={budget:.3f},asetpts=PTS-STARTPTS,adelay={round(start * 1000)}:all=1[a{index}]"
            filters.append(filter_text)
            labels.append(f"[a{index}]")
        filters.append("".join(labels) + f"amix=inputs={len(labels)}:duration=first:dropout_transition=0:normalize=0[aout]")
        command = ["ffmpeg", "-y"]
        for item in inputs:
            command += ["-i", str(item)]
        command += ["-filter_complex", ";".join(filters), "-map", "0:v:0", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output)]
        run(command)


def main() -> int:
    parser = argparse.ArgumentParser(description="Arabic Chatterbox Multilingual V3 dubbing")
    parser.add_argument("--input", default="assets/input/source.mp4")
    parser.add_argument("--manifest", default="manifests/dialogue_ar_grouped.json")
    parser.add_argument("--output", default="outputs/arabic_dub_chatterbox_v3.mp4")
    parser.add_argument("--workdir", default="assets/chatterbox_segments")
    parser.add_argument("--device", default=os.getenv("CHATTERBOX_DEVICE", "cpu"), choices=("cpu", "cuda"))
    parser.add_argument("--duration", type=float, default=24.842)
    parser.add_argument("--exaggeration", type=float, default=0.55)
    parser.add_argument("--cfg-weight", type=float, default=0.35)
    parser.add_argument("--temperature", type=float, default=0.75)
    parser.add_argument("--top-p", type=float, default=0.90)
    args = parser.parse_args()

    input_video = Path(args.input)
    manifest_path = Path(args.manifest)
    workdir = Path(args.workdir)
    if not input_video.is_file():
        raise SystemExit(f"Missing input video: {input_video}")
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    model = load_model(args.device)
    import torchaudio as ta

    workdir.mkdir(parents=True, exist_ok=True)
    clips: list[tuple[float, float, Path]] = []
    for segment in manifest["segments"]:
        reference = Path(segment["reference_audio"])
        if not reference.is_file():
            raise SystemExit(f"Missing reference audio for {segment['id']}: {reference}")
        output = workdir / f"{segment['id']}.wav"
        print(f"Generating {segment['id']} in Arabic ...")
        wav = model.generate(
            segment["text"],
            language_id="ar",
            audio_prompt_path=str(reference),
            exaggeration=args.exaggeration,
            cfg_weight=args.cfg_weight,
            temperature=args.temperature,
            repetition_penalty=2.0,
            top_p=args.top_p,
        )
        ta.save(str(output), wav.cpu(), model.sr)
        clips.append((float(segment["start"]), float(segment.get("source_end", args.duration)), output))

    mux(input_video, clips, Path(args.output), args.duration)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

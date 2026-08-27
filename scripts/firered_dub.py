#!/usr/bin/env python3
"""Arabic dubbing with FireRedTTS3 zero-shot voice cloning."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


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
    parts: list[str] = []
    while factor > 2.0:
        parts.append("atempo=2.0")
        factor /= 2.0
    parts.append(f"atempo={factor:.6f}")
    return ",".join(parts)


def mux(video: Path, clips: list[tuple[float, float, Path]], output: Path, duration: float) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="firered_mix_") as temp:
        bed = Path(temp) / "bed.wav"
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{duration:.3f}", str(bed)])
        inputs = [video, bed, *[path for _, _, path in clips]]
        filters = ["[1:a]anull[bed]"]
        labels = ["[bed]"]
        for index, (start, end, path) in enumerate(clips, start=2):
            budget = max(0.05, end - start)
            tempo = tempo_filter(probe_duration(path), budget)
            chain = f"[{index}:a]"
            if tempo:
                chain += tempo + ","
            chain += f"atrim=duration={budget:.3f},asetpts=PTS-STARTPTS,adelay={round(start * 1000)}:all=1[a{index}]"
            filters.append(chain)
            labels.append(f"[a{index}]")
        filters.append("".join(labels) + f"amix=inputs={len(labels)}:duration=first:dropout_transition=0:normalize=0[mix]")
        command = ["ffmpeg", "-y"]
        for item in inputs:
            command += ["-i", str(item)]
        command += ["-filter_complex", ";".join(filters), "-map", "0:v:0", "-map", "[mix]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output)]
        run(command)


def main() -> int:
    parser = argparse.ArgumentParser(description="FireRedTTS3 Arabic dubbing")
    parser.add_argument("--input", default="assets/input/new_job/source.mp4")
    parser.add_argument("--manifest", default="manifests/new_job/dialogue_ar_fish_s2.json")
    parser.add_argument("--source-root", default="vendor/FireRedTTS3")
    parser.add_argument("--model-dir", default="vendor/FireRedTTS3/pretrained_models")
    parser.add_argument("--output", default="outputs/new_job/arabic_dub_fireredtts3.mp4")
    parser.add_argument("--workdir", default="assets/fireredtts3/new_job")
    parser.add_argument("--duration", type=float, default=59.4)
    parser.add_argument("--timesteps", type=int, default=10)
    parser.add_argument("--cfg", type=float, default=2.0)
    args = parser.parse_args()

    source_root = Path(args.source_root).resolve()
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))
    try:
        import torch
        import torchaudio
        from fireredtts3.core import FireRedTTS3
    except ImportError as exc:
        raise SystemExit("FireRedTTS3 dependencies are missing. Install requirements-fireredtts3.txt and the official model source.") from exc
    if not torch.cuda.is_available():
        raise SystemExit("FireRedTTS3 requires a CUDA GPU for practical inference. Select a GPU runtime in Colab.")

    model_dir = Path(args.model_dir).resolve()
    input_video = Path(args.input).resolve()
    manifest_path = Path(args.manifest).resolve()
    workdir = Path(args.workdir).resolve()
    output = Path(args.output).resolve()
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    model = FireRedTTS3(str(model_dir), use_fasttext=False, use_llm_tn=False, use_wetext=False)
    workdir.mkdir(parents=True, exist_ok=True)
    clips: list[tuple[float, float, Path]] = []
    for idx, segment in enumerate(manifest["segments"]):
        reference = Path(segment["reference_audio"])
        if not reference.is_absolute():
            reference = (Path.cwd() / reference).resolve()
        prompt_audio, prompt_sr = torchaudio.load(str(reference))
        if prompt_audio.shape[0] > 1:
            prompt_audio = prompt_audio.mean(dim=0, keepdim=True)
        clip_path = workdir / f"{segment['id']}.wav"
        print(f"Generating {segment['id']} ({segment['speaker']}) ...")
        audio, sample_rate = model.generate(
            text=segment["text"],
            language="Arabic",
            prompt_text=segment["reference_text"],
            prompt_audio=prompt_audio,
            prompt_audio_sr=prompt_sr,
            stop_threshold=0.5,
            n_timesteps=args.timesteps,
            inference_cfg=args.cfg,
            seed=1234 + idx,
            do_clean=True,
            do_tn=False,
            do_split=False,
        )
        torchaudio.save(str(clip_path), audio.cpu(), sample_rate)
        clips.append((float(segment["start"]), float(segment.get("source_end", args.duration)), clip_path))

    mux(input_video, clips, output, args.duration)
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

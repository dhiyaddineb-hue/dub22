"""Arabic dubbing with SILMA TTS v1 zero-shot voice cloning.

SILMA's code is MIT and its model weights are Apache-2.0. Use only
reference voices for which the project has explicit permission.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True)


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        check=True, capture_output=True, text=True,
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
    with tempfile.TemporaryDirectory(prefix="silma_mix_") as temp:
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
        command += [
            "-filter_complex", ";".join(filters),
            "-map", "0:v:0", "-map", "[mix]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(output),
        ]
        run(command)


def resolve_reference(value: str) -> Path:
    reference = Path(value)
    if not reference.is_absolute():
        reference = (Path.cwd() / reference).resolve()
    return reference


def main() -> int:
    parser = argparse.ArgumentParser(description="SILMA TTS Arabic dubbing")
    parser.add_argument("--input", default="assets/input/new_job/source.mp4")
    parser.add_argument("--manifest", default="manifests/new_job/dialogue_ar_fireredtts3.json")
    parser.add_argument("--output", default="outputs/new_job/arabic_dub_silma.mp4")
    parser.add_argument("--workdir", default="assets/silma/new_job")
    parser.add_argument("--duration", type=float, default=59.4)
    parser.add_argument("--limit-segments", type=int, default=0, help="Generate only the first N segments; 0 means all")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--nfe-step", type=int, default=16)
    parser.add_argument("--cfg-strength", type=float, default=2.0)
    parser.add_argument("--device", default=None)
    parser.add_argument("--enable-normalizer", action="store_true", help="Enable NeMo text normalization")
    parser.add_argument("--force-tashkeel", action="store_true", help="Enable automatic Arabic diacritization")
    args = parser.parse_args()

    try:
        import torch
        from silma_tts.api import SilmaTTS
    except ImportError as exc:
        raise SystemExit("SILMA dependencies are missing. Install silma-tts and its runtime dependencies.") from exc
    if not torch.cuda.is_available() and (args.device or "cuda") == "cuda":
        raise SystemExit("SILMA is being asked to use CUDA, but CUDA is unavailable. Select a GPU runtime or pass --device cpu.")

    input_video = Path(args.input).resolve()
    manifest_path = Path(args.manifest).resolve()
    output = Path(args.output).resolve()
    workdir = Path(args.workdir).resolve()
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    segments = manifest["segments"]
    if args.limit_segments > 0:
        segments = segments[: args.limit_segments]

    print("Loading SILMA TTS v1...", flush=True)
    model = SilmaTTS(
        device=args.device,
        enable_normalizer=args.enable_normalizer,
        force_tashkeel=args.force_tashkeel,
    )
    workdir.mkdir(parents=True, exist_ok=True)
    clips: list[tuple[float, float, Path]] = []
    for idx, segment in enumerate(segments):
        reference = resolve_reference(segment["reference_audio"])
        if not reference.exists():
            raise FileNotFoundError(reference)
        clip_path = workdir / f"{segment['id']}.wav"
        print(f"Generating {segment['id']} ({segment['speaker']}) ...", flush=True)
        model.infer(
            ref_file=str(reference),
            ref_text=segment.get("reference_text"),
            gen_text=segment["text"],
            file_wave=str(clip_path),
            seed=1234 + idx,
            speed=args.speed,
            nfe_step=args.nfe_step,
            cfg_strength=args.cfg_strength,
            normalize_numbers=args.enable_normalizer,
            force_tashkeel=args.force_tashkeel,
        )
        clips.append((float(segment["start"]), float(segment.get("source_end", args.duration)), clip_path))

    if not clips:
        raise RuntimeError("No segments were generated.")
    mux(input_video, clips, output, args.duration)
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

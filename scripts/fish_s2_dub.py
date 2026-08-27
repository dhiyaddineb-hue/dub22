#!/usr/bin/env python3
"""Fish Audio S2 Pro Arabic dubbing pipeline.

This wrapper uses the official Fish Speech CLI in two stages: encode speaker
reference audio into VQ tokens, then generate one Arabic multi-speaker track
from a dialogue script. It intentionally requires an explicit GPU unless
--allow-cpu is provided because S2 Pro is a 4B model whose official guidance
recommends about 24 GB VRAM.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def run(command: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, cwd=str(cwd) if cwd else None)


def duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def tempo_chain(actual: float, target: float) -> str:
    if actual <= target or target <= 0:
        return ""
    factor = actual / target
    filters: list[str] = []
    while factor > 2.0:
        filters.append("atempo=2.0")
        factor /= 2.0
    filters.append(f"atempo={factor:.6f}")
    return ",".join(filters)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fish Audio S2 Pro Arabic dubbing")
    parser.add_argument("--input", default="assets/input/new_job/source.mp4")
    parser.add_argument("--manifest", default="manifests/new_job/dialogue_ar.json")
    parser.add_argument("--output", default="outputs/new_job/arabic_dub_fish_s2_pro.mp4")
    parser.add_argument("--fish-root", default="vendor/fish-speech")
    parser.add_argument("--python", default=os.getenv("FISH_PYTHON", "vendor/fish-speech/.venv/bin/python"))
    parser.add_argument("--checkpoint", default="checkpoints/s2-pro")
    parser.add_argument("--workdir", default="assets/fish_s2/new_job")
    parser.add_argument("--device", default="cuda", choices=("cuda", "cpu"))
    parser.add_argument("--allow-cpu", action="store_true")
    parser.add_argument("--half", action="store_true")
    parser.add_argument("--compile", action="store_true")
    parser.add_argument("--max-new-tokens", type=int, default=0)
    parser.add_argument("--temperature", type=float, default=0.75)
    parser.add_argument("--top-p", type=float, default=0.85)
    args = parser.parse_args()

    fish_root = Path(args.fish_root).resolve()
    fish_python_arg = Path(args.python)
    fish_python = fish_python_arg if fish_python_arg.is_absolute() else Path(os.path.abspath(args.python))
    checkpoint = Path(args.checkpoint)
    if not checkpoint.is_absolute():
        checkpoint = (fish_root / checkpoint).resolve()
    input_video = Path(args.input).resolve()
    manifest_path = Path(args.manifest).resolve()
    workdir = Path(args.workdir).resolve()
    output = Path(args.output).resolve()

    if not fish_python.exists():
        raise SystemExit(f"Fish Python environment is missing: {fish_python}. Run: cd {fish_root} && uv sync --extra cpu")
    if not input_video.is_file() or not manifest_path.is_file():
        raise SystemExit("Input video or manifest is missing")
    if not checkpoint.is_dir():
        raise SystemExit(f"Fish S2 Pro checkpoint is missing: {checkpoint}. Download fishaudio/s2-pro into this directory first.")
    if args.device == "cpu" and not args.allow_cpu:
        raise SystemExit("Fish S2 Pro requires explicit --allow-cpu on CPU; official guidance recommends a 24GB GPU.")

    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    segments = manifest["segments"]
    speakers: dict[str, dict[str, str]] = {}
    for segment in segments:
        speakers.setdefault(segment["speaker"], {
            "audio": segment["reference_audio"],
            "text": segment.get("reference_text", ""),
        })
    if any(not item["text"] for item in speakers.values()):
        raise SystemExit("Each speaker must include reference_text matching the reference_audio.")

    workdir.mkdir(parents=True, exist_ok=True)
    token_paths: dict[str, Path] = {}
    dac_script = fish_root / "fish_speech/models/dac/inference.py"
    semantic_script = fish_root / "fish_speech/models/text2semantic/inference.py"
    for index, (speaker, info) in enumerate(speakers.items()):
        ref_dir = workdir / f"reference_{index}"
        ref_dir.mkdir(parents=True, exist_ok=True)
        ref_audio = Path(info["audio"])
        if not ref_audio.is_absolute():
            ref_audio = (Path.cwd() / ref_audio).resolve()
        run([str(fish_python), str(dac_script), "-i", str(ref_audio), "--checkpoint-path", str(checkpoint / "codec.pth"), "--device", args.device], cwd=ref_dir)
        npy = ref_dir / "fake.npy"
        if not npy.exists():
            candidates = list(ref_dir.glob("*.npy"))
            if not candidates:
                raise SystemExit(f"Fish codec did not create prompt tokens for {speaker}")
            npy = candidates[0]
        token_paths[speaker] = npy

    dialogue_parts: list[str] = []
    for segment in segments:
        speaker_index = list(speakers).index(segment["speaker"])
        dialogue_parts.append(f"<|speaker:{speaker_index}|>{segment['text']}")
    dialogue = " ".join(dialogue_parts)
    output_audio = workdir / "dialogue_fish_s2.wav"
    semantic_cmd = [
        str(fish_python), str(semantic_script),
        "--text", dialogue,
        "--checkpoint-path", str(checkpoint),
        "--device", args.device,
        "--temperature", str(args.temperature),
        "--top-p", str(args.top_p),
        "--output", str(output_audio),
        "--output-dir", str(workdir),
    ]
    for speaker, info in speakers.items():
        semantic_cmd += ["--prompt-text", info["text"], "--prompt-tokens", str(token_paths[speaker])]
    if args.max_new_tokens:
        semantic_cmd += ["--max-new-tokens", str(args.max_new_tokens)]
    semantic_cmd += ["--compile" if args.compile else "--no-compile", "--half" if args.half else "--no-half"]
    run(semantic_cmd, cwd=fish_root)
    if not output_audio.exists():
        raise SystemExit(f"Fish S2 Pro did not create {output_audio}")

    start = min(float(s["start"]) for s in segments)
    end = max(float(s["source_end"]) for s in segments)
    target = end - start
    with tempfile.TemporaryDirectory(prefix="fish_s2_mux_") as temp:
        bed = Path(temp) / "bed.wav"
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{duration(input_video):.3f}", str(bed)])
        tempo = tempo_chain(duration(output_audio), target)
        audio_filter = (tempo + "," if tempo else "") + f"adelay={round(start * 1000)}:all=1,apad=whole_dur={duration(input_video):.3f},atrim=duration={duration(input_video):.3f}[aout]"
        output.parent.mkdir(parents=True, exist_ok=True)
        run([
            "ffmpeg", "-y", "-i", str(input_video), "-i", str(bed), "-i", str(output_audio),
            "-filter_complex", f"[1:a]anull[bed];[2:a]{audio_filter};[bed][aout]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mix]",
            "-map", "0:v:0", "-map", "[mix]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output),
        ])
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

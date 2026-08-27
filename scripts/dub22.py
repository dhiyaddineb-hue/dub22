#!/usr/bin/env python3
"""Professional dubbing CLI for dub22.

The client intentionally keeps credentials outside the repository and uses the
verified ElevenLabs Dubbing API. It supports project creation, Arabic target
creation, polling, output discovery, and download.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import requests

API_ROOT = "https://api.elevenlabs.io/v1"
DEFAULT_MODEL = "dubbing_v2"


class ApiError(RuntimeError):
    pass


def api_key() -> str:
    key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise ApiError("ELEVENLABS_API_KEY is not set. Export it in the shell; never put it in git.")
    return key


def request(method: str, path: str, **kwargs: Any) -> requests.Response:
    headers = kwargs.pop("headers", {})
    headers["xi-api-key"] = api_key()
    headers.setdefault("Accept", "application/json")
    response = requests.request(method, API_ROOT + path, headers=headers, timeout=120, **kwargs)
    if not response.ok:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text[:1000]
        raise ApiError(f"ElevenLabs API {response.status_code}: {detail}")
    return response


def create_project(args: argparse.Namespace) -> dict[str, Any]:
    source = Path(args.input)
    if not source.is_file():
        raise ApiError(f"Input file does not exist: {source}")
    data: dict[str, str] = {
        "reference": args.reference or source.stem,
        "model_id": args.model_id,
    }
    if args.source_language:
        data["source_language"] = args.source_language
    with source.open("rb") as handle:
        response = request(
            "POST",
            "/dubbing/project",
            files={"file": (source.name, handle, "application/octet-stream")},
            data=data,
        )
    project = response.json()
    print(json.dumps(project, ensure_ascii=False, indent=2))
    return project


def create_target(project_id: str, args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {"target_language": args.target_language}
    if args.cloning_strength is not None:
        payload["voice_settings"] = {"cloning_strength": args.cloning_strength}
    response = request("POST", f"/dubbing/project/{project_id}/language", json=payload)
    target = response.json()
    print(json.dumps(target, ensure_ascii=False, indent=2))
    return target


def get_project(project_id: str) -> dict[str, Any]:
    return request("GET", f"/dubbing/project/{project_id}").json()


def get_target(project_id: str, language_id: str) -> dict[str, Any]:
    return request("GET", f"/dubbing/project/{project_id}/language/{language_id}").json()


def find_urls(value: Any) -> list[str]:
    """Recursively collect signed URLs from the provider response."""
    urls: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str) and item.startswith(("https://", "http://")) and ("url" in key.lower() or "download" in key.lower()):
                urls.append(item)
            else:
                urls.extend(find_urls(item))
    elif isinstance(value, list):
        for item in value:
            urls.extend(find_urls(item))
    return list(dict.fromkeys(urls))


def poll(project_id: str, language_id: str, interval: int, timeout: int) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while True:
        project = get_project(project_id)
        target = get_target(project_id, language_id)
        project_status = project.get("status")
        target_status = target.get("status")
        print(f"project={project_status} target={target_status}")
        if project_status == "failed":
            raise ApiError(json.dumps(project.get("error"), ensure_ascii=False))
        if target_status == "failed":
            raise ApiError(json.dumps(target.get("error"), ensure_ascii=False))
        if target_status == "completed":
            return target
        if time.monotonic() >= deadline:
            raise ApiError(f"Timed out after {timeout}s; project={project_id}, language={language_id}")
        time.sleep(interval)


def download(target: dict[str, Any], output: str) -> Path:
    urls = find_urls(target.get("outputs"))
    if not urls:
        urls = find_urls(target)
    if not urls:
        raise ApiError("The target is completed but no signed output URL was returned.")
    # Prefer a video URL when multiple output representations are returned.
    urls.sort(key=lambda url: (0 if any(ext in url.lower() for ext in (".mp4", ".mov", ".webm")) else 1, len(url)))
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(urls[0], stream=True, timeout=120) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    print(f"Downloaded {destination}")
    return destination


def doctor(_: argparse.Namespace) -> int:
    ffmpeg = shutil.which("ffmpeg")
    print(json.dumps({"ffmpeg": ffmpeg or False, "api_key_present": bool(os.getenv("ELEVENLABS_API_KEY"))}, indent=2))
    return 0 if ffmpeg and os.getenv("ELEVENLABS_API_KEY") else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dub22", description="Professional video dubbing CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor_parser = sub.add_parser("doctor", help="Check local prerequisites")
    doctor_parser.set_defaults(func=doctor)

    create_parser = sub.add_parser("create", help="Create a dubbing project and Arabic target")
    create_parser.add_argument("--input", required=True)
    create_parser.add_argument("--source-language", default=None)
    create_parser.add_argument("--target-language", default="ar")
    create_parser.add_argument("--reference", default=None)
    create_parser.add_argument("--model-id", default=DEFAULT_MODEL)
    create_parser.add_argument("--cloning-strength", type=int, choices=range(0, 11), default=7)
    create_parser.set_defaults(func=cmd_create)

    status_parser = sub.add_parser("status", help="Print project and target status")
    status_parser.add_argument("--project-id", required=True)
    status_parser.add_argument("--language-id", required=True)
    status_parser.set_defaults(func=cmd_status)

    run_parser = sub.add_parser("run", help="Create, poll, and download a completed Arabic dub")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--output", default="outputs/arabic_dub_elevenlabs.mp4")
    run_parser.add_argument("--source-language", default=None)
    run_parser.add_argument("--target-language", default="ar")
    run_parser.add_argument("--reference", default=None)
    run_parser.add_argument("--model-id", default=DEFAULT_MODEL)
    run_parser.add_argument("--cloning-strength", type=int, choices=range(0, 11), default=7)
    run_parser.add_argument("--poll-interval", type=int, default=10)
    run_parser.add_argument("--timeout", type=int, default=3600)
    run_parser.set_defaults(func=cmd_run)
    return parser


def cmd_create(args: argparse.Namespace) -> int:
    project = create_project(args)
    project_id = project.get("project_id")
    if not project_id:
        raise ApiError("Create project response did not contain project_id")
    create_target(project_id, args)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    print(json.dumps({"project": get_project(args.project_id), "target": get_target(args.project_id, args.language_id)}, ensure_ascii=False, indent=2))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    project = create_project(args)
    project_id = project.get("project_id")
    if not project_id:
        raise ApiError("Create project response did not contain project_id")
    target = create_target(project_id, args)
    language_id = target.get("language_id")
    if not language_id:
        raise ApiError("Create language target response did not contain language_id")
    completed = poll(project_id, language_id, args.poll_interval, args.timeout)
    download(completed, args.output)
    print(json.dumps({"project_id": project_id, "language_id": language_id, "output": args.output}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    try:
        args = build_parser().parse_args()
        return args.func(args)
    except ApiError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

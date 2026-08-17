#!/usr/bin/env python3
"""Probe media, detect candidate cuts, and render shot-analysis records."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path
from typing import Any


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def require_tool(name: str) -> str:
    value = shutil.which(name)
    if not value:
        raise RuntimeError(f"required media tool is unavailable: {name}")
    return value


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")


def parse_rate(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        return None


def probe_media(path: Path) -> dict[str, Any]:
    command = [
        require_tool("ffprobe"), "-v", "error", "-show_entries",
        "format=format_name,duration:stream=index,codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate,nb_frames,duration",
        "-of", "json", str(path),
    ]
    raw = json.loads(run(command).stdout)
    streams = raw.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), {})
    duration_value = raw.get("format", {}).get("duration") or video.get("duration")
    duration_ms = round(float(duration_value) * 1000) if duration_value not in {None, "N/A"} else None
    fps = parse_rate(video.get("avg_frame_rate")) or parse_rate(video.get("r_frame_rate"))
    frames = video.get("nb_frames")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {
        "sha256": digest.hexdigest(),
        "container": raw.get("format", {}).get("format_name"),
        "duration_ms": duration_ms,
        "fps": fps,
        "frame_count": int(frames) if isinstance(frames, str) and frames.isdigit() else None,
        "width": video.get("width"),
        "height": video.get("height"),
        "video_codec": video.get("codec_name"),
        "has_audio": any(item.get("codec_type") == "audio" for item in streams),
        "audio_codecs": [item.get("codec_name") for item in streams if item.get("codec_type") == "audio"],
    }


def detect_candidate_cuts(path: Path, threshold: float) -> list[int]:
    if not 0 < threshold < 1:
        raise ValueError("threshold must be between 0 and 1")
    command = [
        require_tool("ffmpeg"), "-hide_banner", "-i", str(path), "-filter:v",
        f"select=gt(scene\\,{threshold:g}),showinfo", "-an", "-f", "null", "-",
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg cut detection failed")
    values = [round(float(value) * 1000) for value in re.findall(r"pts_time:([0-9.]+)", result.stderr)]
    return sorted(set(values))


def build_analysis(path: Path, threshold: float) -> dict[str, Any]:
    media = probe_media(path)
    if media["duration_ms"] is None:
        raise RuntimeError("media duration is unavailable")
    cuts = [value for value in detect_candidate_cuts(path, threshold) if 0 < value < media["duration_ms"]]
    boundaries = [0, *cuts, media["duration_ms"]]
    shots = []
    for index, (start, end) in enumerate(zip(boundaries, boundaries[1:]), start=1):
        unknown = {"level": "unknown", "text": "pending source inspection"}
        shots.append({
            "shot_id": f"SHOT-{index:03d}",
            "start_ms": start,
            "end_ms": end,
            "boundary_evidence": "inferred",
            "transition": "candidate-cut",
            "scene_id": None,
            "asset_ids": [],
            "visual": dict(unknown),
            "performance": dict(unknown),
            "camera": dict(unknown),
            "composition": dict(unknown),
            "light": dict(unknown),
            "dialogue": dict(unknown),
            "sound": dict(unknown),
            "notes": dict(unknown),
        })
    return {
        "schema_version": "1.0",
        "source": {"path": str(path.resolve()), **media},
        "detection": {"threshold": threshold, "status": "candidate-boundaries-require-frame-review"},
        "shots": shots,
    }


def validate_analysis(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["analysis must be an object"]
    scripts_dir = Path(__file__).resolve().parent
    schemas_dir = scripts_dir.parent / "schemas"
    if str(scripts_dir) not in __import__("sys").path:
        __import__("sys").path.insert(0, str(scripts_dir))
    from schema_validator import validate_file  # pylint: disable=import-outside-toplevel
    errors.extend(validate_file(data, schemas_dir / "shot-analysis.schema.json", "shot-analysis"))
    if set(data) != {"schema_version", "source", "detection", "shots"}:
        errors.append("analysis must contain only schema_version, source, detection, and shots")
    if data.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    source = data.get("source")
    source_keys = {
        "path", "sha256", "container", "duration_ms", "fps", "frame_count", "width", "height",
        "video_codec", "has_audio", "audio_codecs",
    }
    if not isinstance(source, dict):
        errors.append("source must be an object")
        source = {}
    elif set(source) != source_keys:
        errors.append(f"source keys must be {sorted(source_keys)}")
    if not isinstance(source.get("duration_ms"), int) or source.get("duration_ms", 0) < 1:
        errors.append("source.duration_ms must be a positive integer")
        duration = None
    else:
        duration = source["duration_ms"]
    if not isinstance(source.get("sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", source.get("sha256", "")):
        errors.append("source.sha256 must be lowercase SHA-256")
    detection = data.get("detection")
    if not isinstance(detection, dict) or set(detection) != {"threshold", "status"}:
        errors.append("detection must contain threshold and status")
    elif (not isinstance(detection["threshold"], (int, float)) or isinstance(detection["threshold"], bool)
          or not 0 < detection["threshold"] < 1
          or detection["status"] != "candidate-boundaries-require-frame-review"):
        errors.append("detection is invalid")
    shots = data.get("shots")
    if not isinstance(shots, list) or not shots:
        errors.append("shots must be a non-empty array")
        return errors
    cursor = 0
    seen: set[str] = set()
    for index, shot in enumerate(shots, start=1):
        if not isinstance(shot, dict):
            errors.append(f"shot {index} must be an object")
            continue
        shot_keys = {
            "shot_id", "start_ms", "end_ms", "boundary_evidence", "transition", "scene_id", "asset_ids",
            "visual", "performance", "camera", "composition", "light", "dialogue", "sound", "notes",
        }
        if set(shot) != shot_keys:
            errors.append(f"shot {index} keys must be {sorted(shot_keys)}")
        shot_id = shot.get("shot_id")
        if not isinstance(shot_id, str) or not re.fullmatch(r"SHOT-\d{3}", shot_id) or shot_id in seen:
            errors.append(f"invalid or duplicate shot_id: {shot_id}")
        else:
            seen.add(shot_id)
        if shot.get("start_ms") != cursor or not isinstance(shot.get("end_ms"), int) or shot["end_ms"] <= cursor:
            errors.append(f"shot {shot_id or index} has invalid timing")
        else:
            cursor = shot["end_ms"]
        if shot.get("boundary_evidence") not in {"confirmed", "inferred", "unknown"}:
            errors.append(f"shot {shot_id or index} has invalid boundary evidence")
        scene_id = shot.get("scene_id")
        if scene_id is not None and (not isinstance(scene_id, str) or not re.fullmatch(r"SCENE-\d{3}(?:-V\d{2})?", scene_id)):
            errors.append(f"shot {shot_id or index} has invalid scene_id")
        asset_ids = shot.get("asset_ids")
        if not isinstance(asset_ids, list) or any(
            not isinstance(item, str) or not re.fullmatch(r"(?:CHAR|SCENE|PROP|MOTIF|COSTUME|BG)-\d{3}(?:-V\d{2})?", item)
            for item in asset_ids
        ) or len(asset_ids) != len(set(asset_ids)):
            errors.append(f"shot {shot_id or index} has invalid asset_ids")
        for key in ("visual", "performance", "camera", "composition", "light", "dialogue", "sound", "notes"):
            value = shot.get(key)
            if (not isinstance(value, dict) or set(value) != {"level", "text"}
                    or value.get("level") not in {"confirmed", "inferred", "unknown"}
                    or not isinstance(value.get("text"), str)):
                errors.append(f"shot {shot_id or index} has invalid {key} evidence")
    if duration is not None and cursor != duration:
        errors.append(f"analysis ends at {cursor}, source duration is {duration}")
    return errors


def clock(milliseconds: int) -> str:
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def render_markdown(data: dict[str, Any]) -> str:
    errors = validate_analysis(data)
    if errors:
        raise ValueError("; ".join(errors))
    source = data["source"]
    rows = [
        "# Shot Analysis", "", f"Source: `{source['path']}`", "",
        f"Duration: {source['duration_ms']} ms | FPS: {source.get('fps')} | "
        f"Size: {source.get('width')}x{source.get('height')} | Audio: {source.get('has_audio')}", "",
    ]
    for shot in data["shots"]:
        scene = shot["scene_id"] or "unassigned"
        assets = ", ".join(shot["asset_ids"]) if shot["asset_ids"] else "none"
        rows.extend([
            f"## {shot['shot_id']} | {clock(shot['start_ms'])}-{clock(shot['end_ms'])}", "",
            f"- Scene asset: {scene}",
            f"- Referenced assets: {assets}",
            f"- Boundary: {shot['boundary_evidence']} | {shot.get('transition', '')}",
            f"- Visual: {shot['visual']['level']} | {shot['visual']['text']}",
            f"- Performance: {shot['performance']['level']} | {shot['performance']['text']}",
            f"- Camera: {shot['camera']['level']} | {shot['camera']['text']}",
            f"- Composition: {shot['composition']['level']} | {shot['composition']['text']}",
            f"- Light: {shot['light']['level']} | {shot['light']['text']}",
            f"- Dialogue: {shot['dialogue']['level']} | {shot['dialogue']['text']}",
            f"- Sound: {shot['sound']['level']} | {shot['sound']['text']}", "",
            f"- Notes: {shot['notes']['level']} | {shot['notes']['text']}", "",
        ])
    return "\n".join(rows)


def _remove_path(path: Path) -> None:
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    except FileNotFoundError:
        pass


def extract_review_frames(video_path: Path, data: dict[str, Any], output_dir: Path) -> list[dict[str, Any]]:
    errors = validate_analysis(data)
    if errors:
        raise ValueError("; ".join(errors))
    output_dir.mkdir(parents=True, exist_ok=True)
    fps = data["source"].get("fps")
    frame_ms = max(1, round(1000 / fps)) if isinstance(fps, (int, float)) and fps > 0 else 40
    records: list[dict[str, Any]] = []
    destinations: list[Path] = []
    for shot in data["shots"]:
        start = shot["start_ms"]
        end = shot["end_ms"]
        times = {
            "start": min(end - 1, start + frame_ms),
            "middle": start + (end - start) // 2,
            "end": max(start, end - frame_ms),
        }
        for position, at_ms in times.items():
            output = output_dir / f"{shot['shot_id']}-{position}.png"
            if output.exists():
                raise FileExistsError(f"refusing to overwrite review frame: {output}")
            destinations.append(output)
            records.append({"shot_id": shot["shot_id"], "position": position, "at_ms": at_ms, "path": str(output)})

    staging_dir = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.frames-", dir=output_dir.parent))
    installed: list[Path] = []
    try:
        for record, output in zip(records, destinations):
            staged = staging_dir / output.name
            command = [
                require_tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-ss", f"{record['at_ms'] / 1000:.3f}",
                "-i", str(video_path), "-frames:v", "1", "-an", str(staged),
            ]
            run(command)
            if not staged.is_file():
                raise RuntimeError(f"ffmpeg did not produce review frame: {output}")
        for output in destinations:
            os.replace(staging_dir / output.name, output)
            installed.append(output)
    except Exception:
        for output in installed:
            _remove_path(output)
        raise
    finally:
        _remove_path(staging_dir)
    return records


def extract_audio(video_path: Path, output_path: Path) -> None:
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite audio file: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{output_path.name}.", suffix=output_path.suffix, dir=output_path.parent)
    os.close(handle)
    staged = Path(temp_name)
    staged.unlink()
    try:
        command = [
            require_tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-i", str(video_path),
            "-vn", "-acodec", "pcm_s16le", str(staged),
        ]
        run(command)
        if not staged.is_file():
            raise RuntimeError(f"ffmpeg did not produce audio: {output_path}")
        os.replace(staged, output_path)
    except Exception:
        _remove_path(staged)
        raise


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    probe = sub.add_parser("probe")
    probe.add_argument("--input", required=True)
    probe.add_argument("--output")
    cuts = sub.add_parser("detect-cuts")
    cuts.add_argument("--input", required=True)
    cuts.add_argument("--threshold", type=float, default=0.1)
    cuts.add_argument("--output")
    analyze = sub.add_parser("analyze")
    analyze.add_argument("--input", required=True)
    analyze.add_argument("--threshold", type=float, default=0.1)
    analyze.add_argument("--output", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--input", required=True)
    render = sub.add_parser("render")
    render.add_argument("--input", required=True)
    render.add_argument("--output", required=True)
    frames = sub.add_parser("extract-frames")
    frames.add_argument("--input", required=True)
    frames.add_argument("--analysis", required=True)
    frames.add_argument("--output-dir", required=True)
    audio = sub.add_parser("extract-audio")
    audio.add_argument("--input", required=True)
    audio.add_argument("--output", required=True)
    args = parser.parse_args()
    input_path = Path(args.input)
    if args.command == "probe":
        value = probe_media(input_path)
        output = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        atomic_write(Path(args.output), output) if args.output else print(output, end="")
    elif args.command == "detect-cuts":
        value = {"candidate_cut_ms": detect_candidate_cuts(input_path, args.threshold)}
        output = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        atomic_write(Path(args.output), output) if args.output else print(output, end="")
    elif args.command == "analyze":
        write_json(Path(args.output), build_analysis(input_path, args.threshold))
    elif args.command == "extract-audio":
        extract_audio(input_path, Path(args.output))
        print(args.output)
    elif args.command == "extract-frames":
        data = json.loads(Path(args.analysis).read_text(encoding="utf-8"))
        records = extract_review_frames(input_path, data, Path(args.output_dir))
        print(json.dumps({"frames": records}, ensure_ascii=False, indent=2))
    else:
        data = json.loads(input_path.read_text(encoding="utf-8"))
        if args.command == "validate":
            errors = validate_analysis(data)
            if errors:
                for error in errors:
                    print(f"ERROR: {error}")
                return 1
            print("PASS: shot analysis is structurally valid")
        else:
            atomic_write(Path(args.output), render_markdown(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

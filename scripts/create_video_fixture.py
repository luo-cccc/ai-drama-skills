#!/usr/bin/env python3
"""Create a deterministic synthetic video fixture for reverse analysis."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def create(output: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is not available")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=white:s=320x180:d=1:r=25",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=320x180:d=1:r=25",
        "-f",
        "lavfi",
        "-i",
        "color=c=white:s=320x180:d=1:r=25",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=3:sample_rate=48000",
        "-filter_complex",
        "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]",
        "-map",
        "[v]",
        "-map",
        "3:a",
        "-c:v",
        "libx264",
        "-g",
        "25",
        "-keyint_min",
        "25",
        "-sc_threshold",
        "0",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(output),
    ]
    subprocess.run(command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    create(Path(args.output).resolve())
    print(Path(args.output).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

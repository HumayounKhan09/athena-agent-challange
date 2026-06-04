#!/usr/bin/env python3
"""Build demo/athena-agent-demo.mp4 from captured terminal transcripts."""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "demo"
CAPTURES = DEMO / "captures"
OUTPUT = DEMO / "athena-agent-demo.mp4"
FFMPEG = None


def ffmpeg_exe() -> str:
    global FFMPEG
    if FFMPEG:
        return FFMPEG
    try:
        import imageio_ffmpeg

        FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
        return FFMPEG
    except ImportError:
        pass
    for candidate in ("ffmpeg", "/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"):
        try:
            subprocess.run([candidate, "-version"], capture_output=True, check=True)
            FFMPEG = candidate
            return FFMPEG
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    raise RuntimeError("ffmpeg not found; install ffmpeg or pip install imageio-ffmpeg")


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.dfont",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def wrap_lines(text: str, width: int = 92) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        if not raw.strip():
            lines.append("")
            continue
        lines.extend(textwrap.wrap(raw, width=width, replace_whitespace=False) or [""])
    return lines


def render_terminal_frame(
    title: str,
    body: str,
    *,
    width: int = 1280,
    height: int = 720,
    bg: tuple[int, int, int] = (18, 18, 18),
    fg: tuple[int, int, int] = (230, 230, 230),
    accent: tuple[int, int, int] = (120, 200, 120),
) -> Image.Image:
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)
    title_font = load_font(28)
    body_font = load_font(18)

    draw.text((40, 28), title, fill=accent, font=title_font)
    y = 80
    for line in wrap_lines(body, width=110):
        draw.text((40, y), line, fill=fg, font=body_font)
        y += 24
        if y > height - 40:
            draw.text((40, y), "... (truncated)", fill=(150, 150, 150), font=body_font)
            break
    return img


def render_title_card(
    heading: str,
    subheading: str,
    *,
    width: int = 1280,
    height: int = 720,
) -> Image.Image:
    img = Image.new("RGB", (width, height), (12, 18, 32))
    draw = ImageDraw.Draw(img)
    h_font = load_font(42)
    s_font = load_font(24)
    draw.text((80, height // 2 - 60), heading, fill=(255, 255, 255), font=h_font)
    for idx, line in enumerate(wrap_lines(subheading, width=70)):
        draw.text((80, height // 2 + 10 + idx * 34), line, fill=(180, 200, 230), font=s_font)
    return img


def save_frames(frames: list[Image.Image], fps: int, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = CAPTURES / "frames"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    for old in tmp_dir.glob("frame_*.png"):
        old.unlink()

    paths: list[Path] = []
    hold = max(1, int(fps * 0.04))  # ~40ms per duplicate for timing
    idx = 0
    for frame in frames:
        repeats = 30 if frame.width == 1280 and frame.height == 720 else 15
        for _ in range(repeats):
            path = tmp_dir / f"frame_{idx:05d}.png"
            frame.save(path)
            paths.append(path)
            idx += 1

    list_file = CAPTURES / "frames.txt"
    with list_file.open("w", encoding="utf-8") as fh:
        for path in paths:
            fh.write(f"file '{path}'\n")
            fh.write(f"duration {1 / fps:.6f}\n")
        if paths:
            fh.write(f"file '{paths[-1]}'\n")

    ffmpeg = ffmpeg_exe()
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-vf",
        "format=yuv420p",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)


def read_capture(name: str) -> str:
    path = CAPTURES / name
    return path.read_text(encoding="utf-8") if path.exists() else f"(missing capture: {name})"


def main() -> int:
    CAPTURES.mkdir(parents=True, exist_ok=True)

    frames: list[Image.Image] = []
    frames.append(
        render_title_card(
            "Athena MCP Agent Demo",
            "Tests, local MCP server, MCP Inspector curl session, and Athena manual setup notes.",
        )
    )

    frames.append(
        render_terminal_frame(
            "1/4 — pytest (24 passed)",
            read_capture("01-pytest.txt"),
        )
    )
    frames.append(
        render_terminal_frame(
            "2/4 — Server health + MCP initialize",
            read_capture("02-server-mcp.txt"),
        )
    )
    frames.append(
        render_terminal_frame(
            "3/4 — MCP tools/list + fetch_data",
            read_capture("03-mcp-tools.txt"),
        )
    )

    athena_note = read_capture("04-athena-notes.txt")
    athena_img = CAPTURES / "athena-screenshot.png"
    if athena_img.exists():
        shot = Image.open(athena_img).convert("RGB")
        shot = shot.resize((1280, 720))
        frames.append(shot)
    frames.append(
        render_terminal_frame(
            "4/4 — Athena agent (manual steps)",
            athena_note,
        )
    )
    frames.append(
        render_title_card(
            "Reproduce locally",
            "source .venv/bin/activate && pytest -v\npython server.py\n./demo/record-demo.sh",
        )
    )

    save_frames(frames, fps=30, out_path=OUTPUT)
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

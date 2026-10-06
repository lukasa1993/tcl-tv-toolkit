#!/usr/bin/env python3
"""Build neutral example boot artwork, or package your own frame directories."""
import argparse
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
from zipfile import ZipFile, ZIP_STORED
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def sample_frame(index, count, intro=False):
    image = Image.new("RGB", (640, 180), "black")
    draw = ImageDraw.Draw(image)
    phase = index / count * math.tau
    scale = min(1, (index + 1) / count) if intro else 1
    # Neutral geometry, no personal logo, text, identifiers or imported artwork.
    draw.ellipse((280, 50, 360, 130), outline=(38, 90, 125), width=3)
    for n in range(12):
        angle = phase + n * math.tau / 12
        x, y = 320 + math.cos(angle) * 56, 90 + math.sin(angle) * 56
        color = tuple(int(v * scale) for v in (60, 170, 220))
        draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=color)
    return image


def png(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def package(parts, output, fps=30, display=(1920, 1080)):
    width, height = display
    if fps <= 0 or width <= 0 or height <= 0 or not all(parts):
        raise ValueError("Need nonempty frame parts and positive dimensions/FPS")
    # Trims describe drawing bounds; smaller textures reduce decoded memory.
    dimensions = {image.size for part in parts for image in part}
    if len(dimensions) != 1:
        raise ValueError("Every frame must have the same dimensions")
    iw, ih = next(iter(dimensions))
    draw_height = round(ih * width / iw)
    if draw_height > height:
        raise ValueError("Frame aspect ratio exceeds display height")
    trim = f"{width}x{draw_height}+0+{(height-draw_height)//2}\n"
    with ZipFile(output, "w", compression=ZIP_STORED) as archive:
        archive.writestr("desc.txt", f"{width} {height} {fps}\np 1 0 part0 #000000\np 0 0 part1 #000000\n")
        for n, part in enumerate(parts):
            for i, image in enumerate(part):
                archive.writestr(f"part{n}/{i:04d}.png", png(image.convert("RGB")))
            archive.writestr(f"part{n}/trim.txt", trim * len(part))
    return {"texture": [iw, ih], "display": [width, height], "fps": fps,
            "frames": [len(part) for part in parts],
            "decoded_loop_mib": iw * ih * 4 * len(parts[1]) / 1024**2,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


def module(animation, output):
    with ZipFile(output, "w", compression=ZIP_STORED) as archive:
        archive.writestr("module.prop", "id=tv_sample_art\nname=Sample TV boot animation\nversion=1.0\nversionCode=1\nauthor=TV Toolkit\ndescription=Neutral example animation; no scripts or SELinux rules\n")
        archive.writestr("system.prop", "ro.feature.bootanim_cust=false\n")
        archive.write(animation, "system/media/bootanimation.zip")


def yuyv(image):
    """Full-range BT.601 YUYV422. Caller must verify target format and dimensions."""
    image = image.convert("RGB")
    if image.width % 2:
        raise ValueError("YUYV requires an even width")
    result = bytearray()
    pixels = image.tobytes()
    def channels(pixel):
        r, g, b = pixel
        return (.299*r+.587*g+.114*b, 128-.168736*r-.331264*g+.5*b,
                128+.5*r-.418688*g-.081312*b)
    def q(value):
        return max(0, min(255, round(value)))
    for i in range(0, len(pixels), 6):
        a, b = channels(pixels[i:i+3]), channels(pixels[i+3:i+6])
        result.extend((q(a[0]), q((a[1]+b[1])/2), q(b[0]), q((a[2]+b[2])/2)))
    return bytes(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=Path, help="Directory containing part0/*.png and part1/*.png")
    parser.add_argument("--raw-source", type=Path, help="Optional image to encode at its existing dimensions")
    parser.add_argument("--output", type=Path, default=ROOT / ".local" / "sample-art")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.frames:
        parts = [[Image.open(path).convert("RGB") for path in sorted((args.frames/part).glob("*.png"))] for part in ("part0", "part1")]
    else:
        parts = [[sample_frame(i, 30, True) for i in range(30)], [sample_frame(i, 60) for i in range(60)]]
    animation = args.output / "bootanimation.zip"
    metadata = package(parts, animation)
    module(animation, args.output / "sample-module.zip")
    parts[0][-1].save(args.output / "preview.png")
    if args.raw_source:
        image = Image.open(args.raw_source)
        raw = yuyv(image)
        (args.output / "sample.raw").write_bytes(raw)
        metadata["raw"] = {"dimensions": list(image.size), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    (args.output / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print("Built local artwork; no TV was contacted. " + json.dumps(metadata))


if __name__ == "__main__":
    main()

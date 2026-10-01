#!/usr/bin/env python3
"""Grade the original films: monochrome imagery, selective cyan/violet neon."""
import argparse
import colorsys
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets/studio/videos"
SOURCES = {
    "graphite-art": "codehouse-graphite-art.mp4",
    "typing-hands": "codehouse-typing-hands-fluid.mp4",
    "eye-code": "codehouse-eye-code.mp4",
    "graphite-shading": "codehouse-graphite-shading.mp4",
    "visual-studio": "codehouse-visual-studio.mp4",
    "pencil-grip": "codehouse-pencil-grip.mp4",
}


def smooth(low, high, value):
    t = max(0.0, min(1.0, (value - low) / (high - low)))
    return t * t * (3.0 - 2.0 * t)


def make_lut(path):
    size = 33
    with path.open("w") as file:
        file.write(f'TITLE "Monochrome with neon light"\nLUT_3D_SIZE {size}\n')
        for blue in range(size):
            for green in range(size):
                for red in range(size):
                    r, g, b = [v / (size - 1) for v in (red, green, blue)]
                    hue, saturation, value = colorsys.rgb_to_hsv(r, g, b)
                    degrees = hue * 360
                    # Retain only saturated cyan/violet light. Paper, hands,
                    # clothing and ordinary warm lighting become monochrome.
                    neon = (smooth(150, 175, degrees)
                            * (1 - smooth(305, 330, degrees))
                            * smooth(.18, .38, saturation)
                            * smooth(.08, .24, value))
                    gray = .2126 * r + .7152 * g + .0722 * b
                    file.write(" ".join(f"{gray + neon * (c - gray):.6f}"
                                        for c in (r, g, b)) + "\n")


def encode(source, target, lut, codec):
    # Keep the typing contact surface outside the frame. A prompt alone can
    # reintroduce visible keys, so the final camera crop enforces the framing.
    crops = {
        "typing-hands": "crop=iw*0.62:ih*0.62:0:ih*0.12",
        "eye-code": "crop=iw*0.80:ih*0.80:iw*0.075:ih*0.10",
        # Track the editor's slight leftward camera drift, keeping only code
        # inside the frame (no programmer, monitor bezel or editor sidebars).
        "visual-studio": "crop=iw*0.40:ih*0.40:iw*(0.465-0.04*t/6):ih*0.15",
    }
    framing = (crops[target.stem] + ",scale=1920:1080:flags=lanczos,"
               if target.stem in crops else "")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(source),
                    "-t", "6", "-an", "-vf", f"{framing}lut3d=file='{lut}'",
                    *codec, str(target)], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=tuple(SOURCES), nargs="+")
    args = parser.parse_args()
    selected = {name: filename for name, filename in SOURCES.items()
                if not args.only or name in args.only}
    for filename in selected.values():
        source = ROOT / "attached_assets/generated_videos" / filename
        if not source.is_file():
            raise FileNotFoundError(f"Missing original film: {source}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="codehouse-neon-") as temp:
        lut = Path(temp) / "neon.cube"
        make_lut(lut)
        for name, filename in selected.items():
            source = ROOT / "attached_assets/generated_videos" / filename
            encode(source, OUTPUT / f"{name}.mp4", lut,
                   ["-c:v", "libx264", "-preset", "fast", "-threads", "2",
                    "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart"])
            encode(source, OUTPUT / f"{name}.webm", lut,
                   ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "32",
                    "-row-mt", "1", "-threads", "4", "-deadline", "realtime",
                    "-cpu-used", "6", "-pix_fmt", "yuv420p"])
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0.3",
                            "-i", str(OUTPUT / f"{name}.mp4"), "-frames:v", "1",
                            "-c:v", "libwebp", "-quality", "85",
                            str(OUTPUT / f"{name}.webp")], check=True)
            sandbox = ROOT / "artifacts/mockup-sandbox/public/videos"
            if sandbox.is_dir():
                for extension in ("mp4", "webm", "webp"):
                    shutil.copy2(OUTPUT / f"{name}.{extension}", sandbox)
            print(f"Graded {name}: monochrome + neon, 1920×1080, 6 seconds", flush=True)


if __name__ == "__main__":
    main()
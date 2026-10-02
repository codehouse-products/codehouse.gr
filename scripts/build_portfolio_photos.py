#!/usr/bin/env python3
"""Composite real client landing-page captures into the reference campaign photos.

Development-only asset preparation. The source portraits stay untouched.
The finished website uses static WebP files, not this Python script.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "assets/studio/images"
PORTRAITS = (
    ("highhope", "highhopeathens.gr", "assets/studio/images/project-highhope.webp",
     ((274, 160), (558, 200), (502, 810), (214, 772)), None, "project-highhope-live.webp"),
    ("gerakos", "gerakos.gr", "attached_assets/generated_images/pose-gerakos.png",
     ((242, 145), (460, 168), (410, 655), (196, 636)), (40, 0, 859, 1024), "project-gerakos.webp"),
    ("kc-travel", "kctravel.gr", "attached_assets/generated_images/pose-kc-travel.png",
     ((468, 371), (598, 371), (597, 654), (468, 654)), (80, 0, 899, 1024), "project-kc-travel.webp"),
    ("akri", "akriprojects.gr", "attached_assets/generated_images/pose-akri.png",
     ((285, 218), (400, 218), (400, 459), (285, 459)), (80, 0, 899, 1024), "project-akri.webp"),
)

# Only the handset is taken from the edited photo. The original portrait remains
# pixel-identical outside this small region; actual website captures go on top.
PHONE_EDITS = {
    "highhope": (
        "attached_assets/generated_images/iphone17pro-max-highhope.png",
        ((253, 107), (507, 143), (451, 705), (197, 670)),
        ((258, 144), (575, 184), (519, 831), (193, 794)),
    ),
    "gerakos": (
        "attached_assets/generated_images/iphone17pro-max-gerakos.png",
        ((242, 145), (460, 168), (410, 655), (196, 636)),
        ((227, 130), (476, 155), (424, 673), (180, 650)),
    ),
    "kc-travel": (
        "attached_assets/generated_images/iphone17pro-max-kc-travel.png",
        ((468, 371), (598, 371), (597, 654), (468, 654)),
        ((459, 363), (606, 363), (605, 662), (459, 662)),
    ),
    "akri": (
        "attached_assets/generated_images/iphone17pro-max-akri.png",
        ((285, 218), (400, 218), (400, 459), (285, 459)),
        ((277, 210), (407, 210), (407, 467), (277, 467)),
    ),
}


def solve(rows, values):
    """Small Gaussian elimination, avoiding another development dependency."""
    matrix = [list(row) + [value] for row, value in zip(rows, values)]
    for column in range(len(values)):
        pivot = max(range(column, len(values)), key=lambda r: abs(matrix[r][column]))
        matrix[column], matrix[pivot] = matrix[pivot], matrix[column]
        scale = matrix[column][column]
        if abs(scale) < 1e-10:
            raise ValueError("Degenerate phone-screen quadrilateral")
        matrix[column] = [value / scale for value in matrix[column]]
        for row in range(len(values)):
            if row != column:
                scale = matrix[row][column]
                matrix[row] = [a - scale * b for a, b in zip(matrix[row], matrix[column])]
    return tuple(row[-1] for row in matrix)


def perspective(quad, width, height, source_quad=None):
    rows, values = [], []
    source_quad = source_quad or ((0, 0), (width, 0), (width, height), (0, height))
    for (x, y), (u, v) in zip(quad, source_quad):
        rows.extend(((x, y, 1, 0, 0, 0, -u*x, -u*y),
                     (0, 0, 0, x, y, 1, -v*x, -v*y)))
        values.extend((u, v))
    return solve(rows, values)


def replace_handset(photo, slug, quad):
    source, source_quad, outline = PHONE_EDITS[slug]
    edited = Image.open(ROOT / source).convert("RGBA")
    aligned = edited.transform(
        photo.size, Image.Transform.PERSPECTIVE,
        perspective(quad, *edited.size, source_quad=source_quad),
        Image.Resampling.BICUBIC,
    )
    mask = Image.new("L", photo.size)
    ImageDraw.Draw(mask).polygon(outline, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(0.75))
    return Image.composite(aligned, photo, mask)


def phone_screen(capture, domain):
    """Actual page pixels, surrounded only by a neutral mobile browser chrome."""
    screen = Image.new("RGBA", (780, 1688), "#f7f7f8")
    draw = ImageDraw.Draw(screen)
    font = ImageFont.load_default(size=25)
    draw.text((62, 15), "9:41", font=font, fill="#101015")
    draw.rounded_rectangle((294, 12, 478, 52), radius=21, fill="#060608")
    for index, bar in enumerate((10, 17, 24, 31)):
        draw.rectangle((635+index*10, 47-bar, 641+index*10, 47), fill="#101015")
    draw.rounded_rectangle((687, 22, 736, 47), radius=5, outline="#101015", width=3)
    draw.rectangle((693, 28, 727, 41), fill="#101015")
    draw.rectangle((738, 30, 742, 39), fill="#101015")
    draw.rounded_rectangle((25, 64, 755, 130), radius=19, fill="#e5e5e9")
    draw.text((390, 96), domain, font=font, fill="#16161a", anchor="mm")
    # The capture is a 390×740 CSS-pixel viewport; no invented website content.
    screen.alpha_composite(capture.convert("RGBA").resize((780, 1480), Image.Resampling.LANCZOS), (0, 140))
    draw = ImageDraw.Draw(screen)
    draw.rectangle((0, 1620, 780, 1688), fill="#16171d")
    draw.line((67, 1640, 54, 1653, 67, 1666), fill="#8aadd0", width=4)
    draw.line((160, 1640, 173, 1653, 160, 1666), fill="#8aadd0", width=4)
    draw.rectangle((325, 1646, 350, 1668), outline="#8aadd0", width=3)
    draw.line((338, 1660, 338, 1634), fill="#8aadd0", width=3)
    draw.line((330, 1641, 338, 1633, 346, 1641), fill="#8aadd0", width=3)
    draw.rectangle((502, 1641, 527, 1666), outline="#8aadd0", width=3)
    draw.rectangle((619, 1646, 644, 1670), outline="#8aadd0", width=3)
    draw.line((623, 1640, 650, 1640, 650, 1664), fill="#8aadd0", width=3)
    mask = Image.new("L", screen.size)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 779, 1687), radius=62, fill=255)
    screen.putalpha(mask)
    return screen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-dir", type=Path, help="Optional fresh browser PNG captures")
    args = parser.parse_args()
    for slug, domain, source, quad, crop, output in PORTRAITS:
        mobile = IMAGES / (f"{slug}-mobile.webp" if slug in ("gerakos", "akri") else f"{slug}-landing-mobile.webp")
        if args.capture_dir:
            capture = Image.open(args.capture_dir / f"{slug}-screen.png").convert("RGB")
            capture.resize((390, 740), Image.Resampling.LANCZOS).save(mobile, quality=96, method=6)
            if slug in ("gerakos", "akri"):
                desktop = Image.open(args.capture_dir / f"{slug}-desktop.png").convert("RGB")
                desktop.resize((1440, 1000), Image.Resampling.LANCZOS).save(IMAGES / f"{slug}-desktop.webp", quality=90, method=6)
        page = Image.open(mobile)
        photo = Image.open(ROOT / source).convert("RGBA")
        photo = replace_handset(photo, slug, quad)
        screen = phone_screen(page, domain)
        layer = screen.transform(photo.size, Image.Transform.PERSPECTIVE,
                                 perspective(quad, *screen.size), Image.Resampling.BICUBIC)
        finished = Image.alpha_composite(photo, layer).convert("RGB")
        if crop:
            finished = finished.crop(crop)
        finished.save(IMAGES / output, quality=91, method=6)
        print(f"{output}: {finished.width}×{finished.height}")


if __name__ == "__main__":
    main()
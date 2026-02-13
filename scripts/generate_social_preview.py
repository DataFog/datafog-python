"""Generate a GitHub social preview image aligned to the DataFog design system."""

from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import Iterable, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RGB = Tuple[int, int, int]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="public/social-preview.png",
        help="Output PNG path (default: public/social-preview.png)",
    )
    parser.add_argument("--width", type=int, default=1280, help="Image width in px")
    parser.add_argument("--height", type=int, default=640, help="Image height in px")
    return parser.parse_args()


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def lerp_color(start: RGB, end: RGB, t: float) -> RGB:
    return (lerp(start[0], end[0], t), lerp(start[1], end[1], t), lerp(start[2], end[2], t))


def load_font(candidates: Iterable[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for font_path in candidates:
        path = Path(font_path)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                pass
    return ImageFont.load_default()


def draw_background(base: Image.Image, rng: random.Random) -> None:
    width, height = base.size
    draw = ImageDraw.Draw(base)

    bg_top = (8, 7, 4)
    bg_bottom = (14, 12, 9)
    for y in range(height):
        t = y / max(1, height - 1)
        draw.line([(0, y), (width, y)], fill=lerp_color(bg_top, bg_bottom, t))

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((-260, -220, 900, 760), fill=(232, 168, 76, 44))
    glow_draw.ellipse((350, -260, 1320, 740), fill=(232, 168, 76, 26))
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    base.alpha_composite(glow)

    grid = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    grid_draw = ImageDraw.Draw(grid)
    for x in range(0, width, 56):
        grid_draw.line([(x, 0), (x, height)], fill=(24, 21, 16, 88), width=1)
    for y in range(0, height, 56):
        grid_draw.line([(0, y), (width, y)], fill=(24, 21, 16, 72), width=1)
    base.alpha_composite(grid)

    grain = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    grain_draw = ImageDraw.Draw(grain)
    for _ in range((width * height) // 90):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        alpha = rng.randint(4, 12)
        grain_draw.point((x, y), fill=(232, 168, 76, alpha))
    base.alpha_composite(grain)


def draw_fog_barrier(base: Image.Image) -> int:
    width, height = base.size
    barrier_x = int(width * 0.72)

    fog = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    fog_draw = ImageDraw.Draw(fog)

    fade_zone = 170
    for x in range(barrier_x - fade_zone, barrier_x):
        t = (x - (barrier_x - fade_zone)) / max(1, fade_zone)
        alpha = int(175 * (t * t))
        fog_draw.line([(x, 0), (x, height)], fill=(8, 7, 4, alpha), width=1)

    right_span = max(1, width - barrier_x)
    for x in range(barrier_x, width):
        t = (x - barrier_x) / right_span
        alpha = int(150 + 55 * t)
        fog_draw.line([(x, 0), (x, height)], fill=(8, 7, 4, alpha), width=1)

    fog_draw.line([(barrier_x, 0), (barrier_x, height)], fill=(232, 168, 76, 90), width=2)
    base.alpha_composite(fog)
    return barrier_x


def draw_logo(base: Image.Image, mono_bold: ImageFont.ImageFont) -> None:
    draw = ImageDraw.Draw(base)
    icon_x, icon_y = 74, 56
    icon_size = 62

    draw.rounded_rectangle(
        [icon_x, icon_y, icon_x + icon_size, icon_y + icon_size],
        radius=12,
        fill=(14, 12, 9, 255),
    )

    amber = (232, 168, 76, 255)
    draw.rounded_rectangle([icon_x + 10, icon_y + 16, icon_x + 52, icon_y + 24], radius=2, fill=amber)
    draw.rounded_rectangle([icon_x + 10, icon_y + 31, icon_x + 40, icon_y + 39], radius=2, fill=amber)
    draw.rounded_rectangle([icon_x + 10, icon_y + 46, icon_x + 46, icon_y + 54], radius=2, fill=amber)

    draw.text((icon_x + icon_size + 16, icon_y + 18), "DATAFOG", fill=(237, 232, 223, 255), font=mono_bold)


def draw_right_label(base: Image.Image, barrier_x: int, mono: ImageFont.ImageFont) -> None:
    width, height = base.size
    label = "REDACTION LAYER ACTIVE"

    temp = Image.new("RGBA", (height, 48), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(temp)
    tdraw.text((0, 12), label, fill=(232, 168, 76, 170), font=mono)
    rotated = temp.rotate(90, expand=True)

    pos_x = min(width - rotated.size[0] - 14, barrier_x + 18)
    pos_y = (height - rotated.size[1]) // 2
    base.alpha_composite(rotated, (pos_x, pos_y))


def draw_pii_stream(base: Image.Image, barrier_x: int, mono: ImageFont.ImageFont, rng: random.Random) -> None:
    draw = ImageDraw.Draw(base)
    labels = [
        "SSN:423-91-0284",
        "john.doe@mail.com",
        "PHONE:555-0134",
        "NAME:Sarah Chen",
        "IP:192.168.1.42",
        "CC:4532-9013-1204",
        "DOB:1989-03-14",
        "ADDR:742 Elm St",
        "NAME:Mike Torres",
        "EMAIL:lisa@corp.io",
        "PHONE:408-555-9120",
    ]

    y = 110
    while y < base.size[1] - 116:
        text = labels[rng.randint(0, len(labels) - 1)]
        x = rng.randint(max(40, barrier_x - 360), max(44, barrier_x - 150))
        alpha = rng.randint(55, 98)
        draw.text((x, y), text, fill=(232, 168, 76, alpha), font=mono)
        y += rng.randint(34, 48)

    y = 132
    while y < base.size[1] - 130:
        x = rng.randint(max(40, barrier_x - 120), barrier_x - 6)
        blocks = "█" * rng.randint(5, 10)
        alpha = rng.randint(74, 122)
        draw.text((x, y), blocks, fill=(155, 123, 58, alpha), font=mono)
        y += rng.randint(38, 50)


def draw_hero(
    base: Image.Image,
    serif: ImageFont.ImageFont,
    serif_accent: ImageFont.ImageFont,
    mono: ImageFont.ImageFont,
    mono_small: ImageFont.ImageFont,
    barrier_x: int,
) -> None:
    draw = ImageDraw.Draw(base)
    text_main = (237, 232, 223, 255)
    text_secondary = (154, 142, 126, 255)
    amber = (232, 168, 76, 255)
    muted = (102, 92, 79, 255)
    border = (34, 31, 24, 255)
    surface = (14, 12, 9, 255)

    hero_x = 76
    hero_y = 146
    draw.text((hero_x, hero_y), "The", fill=text_main, font=serif)
    draw.text((hero_x + 145, hero_y), "Privacy", fill=amber, font=serif_accent)
    draw.text((hero_x + 472, hero_y), "SDK", fill=text_main, font=serif)
    draw.text((hero_x, hero_y + 82), "for Python", fill=text_main, font=serif)
    draw.text(
        (hero_x, hero_y + 168),
        "Detect and redact PII in text and images via",
        fill=text_secondary,
        font=mono,
    )
    draw.text(
        (hero_x, hero_y + 198),
        "a lightweight SDK, CLI, and production-ready API patterns.",
        fill=text_secondary,
        font=mono,
    )
    draw.text((hero_x, hero_y + 236), "Open source. Runs locally.", fill=muted, font=mono_small)

    cards_y = base.size[1] - 165
    cards_w = barrier_x - hero_x - 68
    card_h = 92
    draw.rounded_rectangle([hero_x, cards_y, hero_x + cards_w, cards_y + card_h], radius=8, fill=border)

    card_gap = 1
    card_w = (cards_w - 2 * card_gap) // 3
    labels = [("Python", "pip install datafog"), ("CLI", "datafog scan <file>"), ("SDK", "TextService().scan(...)")]
    for idx, (title, command) in enumerate(labels):
        x1 = hero_x + idx * (card_w + card_gap)
        x2 = x1 + card_w
        draw.rectangle([x1, cards_y + 1, x2, cards_y + card_h - 1], fill=surface)
        draw.text((x1 + 14, cards_y + 16), title.upper(), fill=muted, font=mono_small)
        draw.text((x1 + 14, cards_y + 48), "$ " + command, fill=text_main, font=mono_small)


def draw_overlays(base: Image.Image) -> None:
    width, height = base.size
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for y in range(0, height, 2):
        draw.line([(0, y), (width, y)], fill=(18, 16, 16, 20), width=1)

    base.alpha_composite(overlay)


def main() -> None:
    args = parse_args()
    rng = random.Random(42)

    mono = load_font(
        [
            "C:/Windows/Fonts/CascadiaMono.ttf",
            "C:/Windows/Fonts/consola.ttf",
        ],
        size=22,
    )
    mono_small = load_font(
        [
            "C:/Windows/Fonts/CascadiaMono.ttf",
            "C:/Windows/Fonts/consola.ttf",
        ],
        size=18,
    )
    mono_bold = load_font(
        [
            "C:/Windows/Fonts/CascadiaCode.ttf",
            "C:/Windows/Fonts/consolab.ttf",
        ],
        size=36,
    )
    serif = load_font(
        [
            "C:/Windows/Fonts/georgia.ttf",
            "C:/Windows/Fonts/georgiab.ttf",
        ],
        size=76,
    )
    serif_accent = load_font(
        [
            "C:/Windows/Fonts/georgiab.ttf",
            "C:/Windows/Fonts/georgia.ttf",
        ],
        size=78,
    )

    image = Image.new("RGBA", (args.width, args.height), (8, 7, 4, 255))
    draw_background(image, rng)
    barrier_x = draw_fog_barrier(image)
    draw_pii_stream(image, barrier_x, mono_small, rng)
    draw_logo(image, mono_bold)
    draw_hero(image, serif, serif_accent, mono_small, mono_small, barrier_x)
    draw_right_label(image, barrier_x, mono_small)
    draw_overlays(image)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, format="PNG", optimize=True)
    print(f"Generated {output} ({args.width}x{args.height})")


if __name__ == "__main__":
    main()

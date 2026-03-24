from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tmp" / "ch4_stability_demo_backup_20260324" / "ch4_stability_demo_before.png"
OUT_DIR = ROOT / "绘图" / "图片新修" / "第四章"
PNG_OUT = OUT_DIR / "ch4_stability_demo_fontonly_preview.png"

SIMSUN = r"C:\Windows\Fonts\simsun.ttc"
TIMES = r"C:\Windows\Fonts\times.ttf"
TIMESI = r"C:\Windows\Fonts\timesi.ttf"


def add_text(
    base: Image.Image,
    text: str,
    center: tuple[int, int],
    font: ImageFont.FreeTypeFont,
    *,
    fill: tuple[int, int, int] = (0, 0, 0),
    rotation: float = 0.0,
) -> None:
    tmp = Image.new("RGBA", base.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(tmp)
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = int(center[0] - w / 2)
    y = int(center[1] - h / 2)
    draw.text((x, y), text, font=font, fill=fill)
    if abs(rotation) > 1e-6:
        tmp = tmp.rotate(rotation, resample=Image.Resampling.BICUBIC, center=center)
    base.alpha_composite(tmp)


def cover(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    draw.rectangle(box, fill=(255, 255, 255, 255))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    img = Image.open(SRC).convert("RGBA")
    draw = ImageDraw.Draw(img)

    simsun_24 = ImageFont.truetype(SIMSUN, 24)
    simsun_26 = ImageFont.truetype(SIMSUN, 26)
    times_24 = ImageFont.truetype(TIMES, 24)
    timesi_24 = ImageFont.truetype(TIMESI, 24)

    # Remove the in-figure title entirely; keep only the original content.
    cover(draw, (2200, 10, 4820, 270))

    # Y-axis labels
    cover(draw, (0, 260, 320, 1235))
    add_text(img, "Bz / nT", (94, 750), timesi_24, rotation=90)

    cover(draw, (0, 1290, 260, 2370))
    add_text(img, "R(k)", (96, 1830), timesi_24, rotation=90)

    cover(draw, (0, 2470, 260, 3560))
    add_text(img, "M(k)", (96, 3010), timesi_24, rotation=90)

    cover(draw, (0, 3600, 260, 4750))
    add_text(img, "stable", (96, 4170), times_24, rotation=90)

    # X-axis label
    cover(draw, (3090, 4480, 3870, 4850))
    add_text(img, "时间 / s", (3480, 4675), simsun_26)

    # Event markers
    cover(draw, (2780, 930, 3360, 1420))
    add_text(img, "t_out", (3060, 1165), timesi_24)

    cover(draw, (3500, 910, 4100, 1420))
    add_text(img, "t_st", (3800, 1165), timesi_24)

    # Threshold labels
    cover(draw, (6240, 1520, 6845, 1815))
    add_text(img, "R_th", (6540, 1665), timesi_24)

    cover(draw, (6200, 2735, 6845, 3045))
    add_text(img, "M_th", (6535, 2890), timesi_24)

    # Legend text only; keep the original legend box and sample lines.
    cover(draw, (5860, 3940, 6750, 4405))
    add_text(img, "双判据成立", (6285, 4095), simsun_24)
    add_text(img, "连续门控后", (6285, 4265), simsun_24)

    img.convert("RGB").save(PNG_OUT, quality=95)


if __name__ == "__main__":
    main()

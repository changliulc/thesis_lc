from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
IMG_DIR = ROOT / "images"
OUT_PATH = IMG_DIR / "ch4_wave_abcd_combined.png"

PANELS = [
    ("ch4_wave_a_new.png", "A类正常车流单车停靠场景"),
    ("ch4_wave_b_new.png", "B类占用期过车扰动场景"),
    ("ch4_wave_c_new.png", "C类连续车流稳定窗缺失场景"),
    ("ch4_wave_d_new.png", "D类慢漂移背景场景"),
]

FALLBACK_DIRS = [
    IMG_DIR,
    ROOT / "tmp" / "ch4_matlab_bulk_outputs_20260324_203347" / "images",
    ROOT / "盲审" / "盲审版工作副本" / "images",
]


def crop_white_border(image: Image.Image, pad: int = 3) -> Image.Image:
    rgb = image.convert("RGB")
    bg = Image.new("RGB", rgb.size, (255, 255, 255))
    diff = ImageChops.difference(rgb, bg)
    bbox = diff.getbbox()
    if not bbox:
        return rgb
    left = max(0, bbox[0] - pad)
    upper = max(0, bbox[1] - pad)
    right = min(rgb.width, bbox[2] + pad)
    lower = min(rgb.height, bbox[3] + pad)
    return rgb.crop((left, upper, right, lower))


def load_font(size: int):
    candidates = [
        Path(r"C:\Windows\Fonts\simsun.ttc"),
        Path(r"C:\Windows\Fonts\STSONG.TTF"),
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
    ]
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def resolve_panel_path(filename: str) -> Path:
    for base in FALLBACK_DIRS:
        candidate = base / filename
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"panel image not found: {filename}")


def fit_panel(image: Image.Image, target_size: tuple[int, int]) -> Image.Image:
    contained = ImageOps.contain(image, target_size, Image.Resampling.LANCZOS)
    panel = Image.new("RGB", target_size, "white")
    x = (target_size[0] - contained.width) // 2
    y = (target_size[1] - contained.height) // 2
    panel.paste(contained, (x, y))
    return panel


def main() -> None:
    cropped_panels = []
    widths = []
    heights = []

    for filename, title in PANELS:
        image = crop_white_border(Image.open(resolve_panel_path(filename)))
        cropped_panels.append((image, title))
        widths.append(image.width)
        heights.append(image.height)

    target_w = int(max(widths) * 0.92 * 4 / 3)
    target_h = int(max(heights) * 0.94 * 4 / 3)
    panel_size = (target_w, target_h)

    title_font = load_font(1)
    title_band_h = 10
    title_gap = 0
    outer_margin_left = 12
    outer_margin_right = 12
    outer_margin_top = 8
    outer_margin_bottom = 10
    gutter_y = 10

    canvas_w = outer_margin_left + outer_margin_right + panel_size[0]
    canvas_h = (
        outer_margin_top
        + outer_margin_bottom
        + len(PANELS) * (title_band_h + panel_size[1])
        + (len(PANELS) - 1) * gutter_y
    )

    canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
    draw = ImageDraw.Draw(canvas)

    for idx, (image, title) in enumerate(cropped_panels):
        x0 = outer_margin_left
        y0 = outer_margin_top + idx * (title_band_h + panel_size[1] + gutter_y)

        panel_img = fit_panel(image, panel_size)
        canvas.paste(panel_img, (x0, y0 + title_band_h))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT_PATH, dpi=(220, 220))
    print(f"saved -> {OUT_PATH}")


if __name__ == "__main__":
    main()

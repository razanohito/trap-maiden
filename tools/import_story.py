"""お話（アドベンチャー）パートの立ち絵を作る。tools/import_v2.py と同じ切り抜きを使う。

入力: art-src/v2/ の白背景の画像（Nano Banana）
  - chirin_<normal|proud|annoyed>.webp … 鍵束の精チリン
  - baron_<laugh|panic|wet>.webp       … ガメツ男爵
  - sheet_<knight|thief|heavy>.webp    … 侵入者の設定画（左の正面の絵を立ち絵に使う）
出力: art/story/<名前>.webp（背景を抜いて高さ 640px。チリンは 480px）

使い方: python tools/import_story.py
"""
from pathlib import Path

import numpy as np
from PIL import Image

from import_v2 import SRC, cut_white, figures

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "art" / "story"
H = 640


def soft_glow(im: Image.Image) -> Image.Image:
    """チリンの後光（白に近い淡い金色）は、明るさに応じて透かして背景になじませる"""
    a = np.asarray(im).astype(float)
    light = a[..., :3].min(2)
    keep = np.clip((250 - light) / 40, 0, 1)  # 白に近いほど透かす
    a[..., 3] = np.minimum(a[..., 3], keep * 255 + (a[..., 3] > 0) * (light < 200) * 255)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def save(im: Image.Image, name: str, h: int = H) -> None:
    im = im.crop(im.getbbox())
    im = im.resize((round(im.width * h / im.height), h), Image.LANCZOS)
    im.save(OUT / f"{name}.webp", quality=88, method=6)
    print("立ち絵", name, im.size)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for face in ("normal", "proud", "annoyed"):
        im = cut_white(Image.open(SRC / f"chirin_{face}.webp"), drop_side_bits=True)
        save(soft_glow(im), f"chirin_{face}", 480)
    for face in ("laugh", "panic", "wet"):
        save(cut_white(Image.open(SRC / f"baron_{face}.webp"), drop_side_bits=True), f"baron_{face}")
    for foe in ("knight", "thief", "heavy"):
        save(figures(Image.open(SRC / f"sheet_{foe}.webp"))[0], f"foe_{foe}")


if __name__ == "__main__":
    main()

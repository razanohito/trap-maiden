"""Gemini に描いてもらった罠のアイコン（金枠つき）を、ゲーム用にそろえて art/icons/ に入れる。

- 入力: art-src/icons/icon_<罠の名前>.png
- 枠の外に残ったマゼンタ（#FF00FF に近い色）を消す
- 枠の大きさがアイコンごとに違うので、絵のある範囲で切り抜いてから 64x64 に最近傍補間でそろえる
- 出力: art/icons/<罠の名前>.png（罠ボタン・支度画面・確認画面で使う。盤面の罠は今までどおりコードで描く）

使い方: python tools/import_icons.py
"""
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art-src" / "icons"
OUT = ROOT / "art" / "icons"
S = 64


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for p in sorted(SRC.glob("icon_*.png")):
        a = np.asarray(Image.open(p).convert("RGBA")).copy()
        r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
        a[(r > 170) & (g < 100) & (b > 170) & (r - g > 110) & (b - g > 110), 3] = 0  # 濃いマゼンタだけ（送り返しの紫は残す）
        im = Image.fromarray(a, "RGBA")
        box = im.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
        im = im.crop(box).resize((S, S), Image.NEAREST)
        name = p.stem[len("icon_"):]
        im.save(OUT / f"{name}.png")
        print(name, box)


if __name__ == "__main__":
    main()

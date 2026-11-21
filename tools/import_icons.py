"""Gemini に描いてもらった罠のアイコン（金枠つき）を、ゲーム用にそろえて art/icons/ に入れる。

- 入力: art-src/icons/icon_<罠の名前>.png
- 枠の外に残ったマゼンタ（#FF00FF に近い色）を消す
- 枠の大きさがアイコンごとに違うので、絵のある範囲で切り抜いてから 64x64 に最近傍補間でそろえる
- 色の薄い暗い部分（石の床・壁・鉄）を、絵柄「月夜のおかし箱」のブルーベリー〜ラベンダー色に置き換える。
  炎・氷・渦・金枠など色のある部分はそのまま
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


def sweets_tint(im: Image.Image) -> Image.Image:
    """色の薄い画素（石・鉄）を、明るさを保ったままブルーベリー〜ラベンダーの濃淡に置き換える。色のある画素ほど元の色を残す"""
    a = np.asarray(im.convert("RGBA")).astype(float) / 255
    rgb = a[..., :3]
    mx, mn = rgb.max(2), rgb.min(2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    lum = rgb @ np.array([.3, .59, .11])
    k = np.clip(lum * 1.25 + .05, 0, 1)[..., None] ** .9
    dark, light = np.array([.17, .14, .36]), np.array([.93, .9, 1.0])  # ブルーベリーの影 → ミルクがかったラベンダー
    new = dark * (1 - k) + light * k
    w = np.clip((.5 - sat) / .2, 0, 1)
    w[(rgb[..., 2] - rgb[..., 0] > .06) & (lum > .5)] = 0  # 氷の淡い水色は残す
    w = w[..., None]                                    # 彩度 0.3 以下は全部、0.5 以上はそのまま
    a[..., :3] = rgb * (1 - w) + new * w
    return Image.fromarray((a * 255).round().astype(np.uint8), "RGBA")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for p in sorted(SRC.glob("icon_*.png")):
        a = np.asarray(Image.open(p).convert("RGBA")).copy()
        r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
        a[(r > 170) & (g < 100) & (b > 170) & (r - g > 110) & (b - g > 110), 3] = 0  # 濃いマゼンタだけ（送り返しの紫は残す）
        im = Image.fromarray(a, "RGBA")
        box = im.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
        im = sweets_tint(im.crop(box).resize((S, S), Image.NEAREST))
        name = p.stem[len("icon_"):]
        im.save(OUT / f"{name}.png")
        print(name, box)


if __name__ == "__main__":
    main()

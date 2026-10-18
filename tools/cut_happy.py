"""ChatGPT に描いてもらった喜びの立ち絵（白背景）の背景を抜いて、結果画面用に art/ に入れる。

- 入力: art-src/happy/<名前>_portrait_happy.png（白背景）
- 外周からつながっている白い画素を塗りつぶして背景とみなす（エプロンやフリルの白は線で囲まれているので残る）
- ふちの薄い白は半透明にして、暗い背景に置いても白い縁取りが出にくいようにする
- 出力: art/portrait_<名前>_happy.webp（高さ 560px、既存の立ち絵と同じ大きさ）

使い方: python tools/cut_happy.py
"""
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art-src" / "happy"
OUT = ROOT / "art"
H = 560


def cut(path: Path) -> Image.Image:
    a = np.asarray(Image.open(path).convert("RGB")).astype(int)
    h, w, _ = a.shape
    white = a.min(2) > 232  # 背景の白（紙の白より明るい）
    bg = np.zeros((h, w), bool); q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if white[y, x] and not bg[y, x]: bg[y, x] = True; q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if white[y, x] and not bg[y, x]: bg[y, x] = True; q.append((y, x))
    while q:
        y, x = q.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and white[ny, nx] and not bg[ny, nx]:
                bg[ny, nx] = True; q.append((ny, nx))
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    # ふち: 背景のすぐ内側の明るい画素は、明るさに応じて透かす
    near = np.asarray(Image.fromarray(alpha).filter(ImageFilter.MinFilter(5))) < 128
    edge = near & ~bg
    light = a.min(2)
    alpha[edge] = np.clip((255 - light[edge]) * 255 // 60, 0, 255).astype(np.uint8)
    rgba = np.dstack([a.astype(np.uint8), alpha])
    im = Image.fromarray(rgba, "RGBA")
    im = im.crop(im.getbbox())
    return im.resize((round(im.width * H / im.height), H), Image.LANCZOS)


def main():
    for p in sorted(SRC.glob("*_portrait_happy.png")):
        name = p.name.replace("_portrait_happy.png", "")
        im = cut(p)
        im.save(OUT / f"portrait_{name}_happy.webp", quality=90)
        print(name, im.size)


if __name__ == "__main__":
    main()

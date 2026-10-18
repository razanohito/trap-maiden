"""Gemini / ChatGPT に作ってもらったエフェクトを、ゲーム用の 8 コマ横長画像（384x48）にそろえて art/fx/ に入れる。

- 入力: art-src/fx/ の画像
  - fx_<名前>_strip.png（8 コマを横に並べた 384x48。透過済み）… そのまま使う
  - fx_<名前>.png（3 列×3 行に 8 コマ、右下は空き。背景マゼンタでも透過でもよい）… 等分して並べ直す
- マゼンタの背景と、そのふちに残ったピンク・紫の点を消す
- 大きく描かれた絵は、ドットの大きさを測って最近傍補間で 48px に縮める
- 出力: art/fx/<名前>.png（384x48、左から順に再生）

使い方: python tools/import_fx.py
"""
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art-src" / "fx"
OUT = ROOT / "art" / "fx"
F = 48


def clean(im: Image.Image) -> Image.Image:
    a = np.asarray(im.convert("RGBA")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    if (a[..., 3] == 0).any():  # 透過済みの絵は紫の演出（送り返し・魂）を消さないよう、ほぼ純粋なマゼンタだけ消す
        magenta = (r > 200) & (g < 70) & (b > 200)
    else:
        magenta = (r - g > 45) & (b - g > 45)  # マゼンタとそのふち（背景がマゼンタの絵）
    a[magenta, 3] = 0
    return Image.fromarray(a.astype("uint8"), "RGBA")


def to_frame(cell: Image.Image) -> Image.Image:
    if cell.size == (F, F):
        return cell
    return cell.resize((F, F), Image.NEAREST)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    done = set()
    # 中身がまったく同じ絵（別の名前で複製されたもの）は取り込まない。すでに art/fx にある名前だけ残す
    groups = {}
    for p in sorted(SRC.glob("fx_*_strip.png")):
        groups.setdefault(hashlib.md5(p.read_bytes()).hexdigest(), []).append(p.name[3:-len("_strip.png")])
    skip = set()
    for names in groups.values():
        if len(names) > 1:
            keep = [n for n in names if (OUT / f"{n}.png").exists()][:1]
            skip |= set(names) - set(keep)
            print("同じ絵:", "・".join(names), "→ 取り込まない:", "・".join(sorted(set(names) - set(keep))) or "なし")
    for p in sorted(SRC.glob("fx_*_strip.png")):
        name = p.name[3:-len("_strip.png")]
        if name in skip:
            continue
        im = clean(Image.open(p))
        if im.size != (F * 8, F):
            im = im.resize((F * 8, F), Image.NEAREST)
        im.save(OUT / f"{name}.png"); done.add(name); print(name, "（横長）")
    for p in sorted(SRC.glob("fx_*.png")):
        stem = p.stem
        if stem.endswith("_strip") or "_f" in stem[3:] and stem.rsplit("_f", 1)[-1].isdigit():
            continue
        name = stem[3:]
        if name in done:
            continue
        im = clean(Image.open(p))
        w, h = im.size
        strip = Image.new("RGBA", (F * 8, F))
        for k in range(8):  # 3x3 の左上から右へ、行ごとに下へ。9 マス目は使わない
            cx, cy = k % 3, k // 3
            cell = im.crop((cx * w // 3, cy * h // 3, (cx + 1) * w // 3, (cy + 1) * h // 3))
            strip.paste(to_frame(cell), (k * F, 0))
        strip.save(OUT / f"{name}.png"); print(name, "（3x3）")


if __name__ == "__main__":
    main()

"""導入マンガの絵の小さな手直し → art/comic/page02.webp
- 2ページ目: 1コマ目のリリィの靴が、下のセシルのコマの吹き出しの中まではみ出していたので、吹き出しの白で塗る
- 元の絵は art-src/comic_orig/（tools/recolor_mina.py と同じ場所）

使い方: python tools/fix_comic.py
"""
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ORIG = ROOT / "art-src" / "comic_orig"
SHOE = (300, 521, 339, 540)  # はみ出した靴の範囲（x0, y0, x1, y1）。吹き出しの右の線（x=340）は残す


def main():
    ORIG.mkdir(parents=True, exist_ok=True)
    dst = ROOT / "art" / "comic" / "page02.webp"; orig = ORIG / "page02.webp"
    if not orig.exists():
        shutil.copy(dst, orig)
    a = np.asarray(Image.open(orig).convert("RGB")).copy()
    x0, y0, x1, y1 = SHOE
    white = a[y1 + 5, (x0 + x1) // 2].copy()  # 吹き出しの中の白
    reg = a[y0:y1, x0:x1]
    reg[np.abs(reg.astype(int) - white.astype(int)).sum(-1) > 18] = white
    Image.fromarray(a).save(dst, quality=90, method=6)
    print("手直し", dst.name)


if __name__ == "__main__":
    main()

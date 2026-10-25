"""ミーナの立ち絵（イラスト）の服の色を、盤面のドット絵と同じ色合いに塗り替える → art/portrait_mina*.webp
2026-10-25 の希望「ミーナのイラスト、ドット絵の色合いに変えて。服色立ち絵が違和感しか無い」
- 盤面のドット絵（tools/import_sprites.py の RULES['mina']）と同じ置きかえ:
    うす紫の帽子・ケープ・ワンピース → 暗いプラム色、ピンクのリボン → 金色。うす紫の髪はそのまま
- 元の絵は art-src/mina_lavender/ に残す（何度実行しても元の絵から作り直す）
- このあと tools/make_busts.py でバストアップを作り直し、tools/build.py

使い方: python tools/recolor_mina.py
"""
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from import_sprites import rgb2hsv, hsv2rgb

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "art"
KEEP = ROOT / "art-src" / "mina_lavender"


def ramp(x, lo, hi):
    return np.clip((x - lo) / (hi - lo), 0, 1)


def grow(mask: np.ndarray, n: int) -> np.ndarray:
    return np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(n))) > 0


def shrink(mask: np.ndarray, n: int) -> np.ndarray:
    return np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(n))) > 0


def recolor(im: Image.Image) -> Image.Image:
    a = np.asarray(im.convert("RGBA")).astype(float)
    rgb = a[..., :3] / 255
    h, s, v = rgb2hsv(rgb)
    op = a[..., 3] > 0
    # 服のうす紫（髪は彩度が低いので外れる）。点々の誤検出を消すため、まとまった所のまわりだけ残す
    H, W = h.shape
    yy, xx = np.mgrid[0:H, 0:W]
    hairzone = (yy > H * 0.1) & (yy < H * 0.47) & (xx > W * 0.2) & (xx < W * 0.8)  # 髪（三つ編みの先まで）がある範囲
    top = np.where(hairzone, 278.0, 305.0)  # 髪のある範囲だけ、赤寄りの紫（髪の色）を外す
    hard = op & (h >= 235) & (h < top) & (s > 0.13)
    near = grow(grow(shrink(hard, 5), 5), 7)
    inside = shrink(grow(near, 15), 15) & ~hairzone | near  # 服の中の白っぽいハイライトのすき間も埋める
    w = ramp(s, 0.01, 0.06) * ramp(h, 228, 238) * (1 - ramp(h, top - 2, top + 8)) * inside  # 髪は色相が赤寄り（280〜)なので外す
    nh = np.full_like(h, 335.0); ns = np.clip(s * 0.75 + 0.12, 0, 1); nv = v * 0.55
    cloth = hsv2rgb(nh, ns, nv)
    # ピンクのリボン → 金
    rib = op & (h >= 318) & (h < 358) & (s > 0.17) & (v > 0.5)  # 帽子のリボンと襟のリボン（細い輪郭線は shrink で外れる）
    ribn = grow(grow(shrink(rib, 3), 3), 5)
    wr = ramp(s, 0.08, 0.17) * ((h >= 312) | (h < 2)) * ribn
    gold = hsv2rgb(np.full_like(h, 42.0), np.clip(s * 1.5 + 0.25, 0, 0.8), np.clip(v * 0.95, 0, 1))
    out = rgb * (1 - w[..., None]) + cloth * w[..., None]
    out = out * (1 - wr[..., None]) + gold * wr[..., None]
    a[..., :3] = out * 255
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def main():
    KEEP.mkdir(parents=True, exist_ok=True)
    for src in sorted(ART.glob("portrait_mina*.webp")):
        orig = KEEP / src.name
        if not orig.exists():
            shutil.copy(src, orig)
        recolor(Image.open(orig)).save(src, quality=90, method=6)
        print("塗り替え", src.name)


if __name__ == "__main__":
    main()

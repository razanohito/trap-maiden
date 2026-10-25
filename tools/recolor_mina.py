"""ミーナの立ち絵（イラスト）と導入マンガの服の色を、盤面のドット絵と同じ色合いに塗り替える → art/portrait_mina*.webp
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


def recolor(im: Image.Image, hair_top=None, skin=None) -> Image.Image:
    """hair_top: 髪を外す色相の上限を全体で固定する（マンガのコマ用）。None なら立ち絵の髪の範囲で決める"""
    a = np.asarray(im.convert("RGBA")).astype(float)
    rgb = a[..., :3] / 255
    h, s, v = rgb2hsv(rgb)
    op = a[..., 3] > 0
    # 服のうす紫 → プラム。髪（髪の範囲にある、赤寄りで明るいうす紫）だけを外し、それ以外のうす紫はすべて塗る
    H, W = h.shape
    yy, xx = np.mgrid[0:H, 0:W]
    lav = op & (h >= 228) & (h < 324) & (s > 0.03) & ~((h >= 312) & (s > 0.17) & (v > 0.5))  # 赤寄りでも暗い・くすんだ紫は服の影。あざやかなピンクはリボン（下で金に）
    if hair_top is None:
        lav &= yy < H * 0.75  # 立ち絵の脚（黒いタイツ）は塗らない
    if hair_top is not None:  # マンガのコマ: 色相だけで髪を見分ける
        hair = lav & (h >= hair_top)
    else:  # 立ち絵: 頭から三つ編みの先までの範囲で、赤寄り・明るいものが髪
        zone = (yy > H * 0.12) & (yy < H * 0.5) & (xx > W * 0.15) & (xx < W * 0.85)
        hair = lav & zone & (h >= 279) & (v > 0.5)
        hair = grow(shrink(grow(hair, 3), 3), 3) & lav & zone & (v > 0.45)  # ばらばらの点を消し、髪のかたまりだけ残す
    keep = np.asarray(Image.fromarray((hair * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))) / 255  # 髪とのさかいめをなめらかに
    w = ramp(s, 0.03, 0.08) * ramp(h, 226, 234) * (1 - ramp(h, 318, 326)) * lav * (1 - keep)
    nh = np.full_like(h, 335.0); ns = np.clip(s * 0.75 + 0.12, 0, 1); nv = v * 0.55
    cloth = hsv2rgb(nh, ns, nv)
    # ピンクのリボン → 金
    rib = op & (h >= 318) & (h < 358) & (s > 0.17) & (v > 0.5)  # 帽子のリボンと襟のリボン（細い輪郭線は shrink で外れる）
    if skin:  # 顔のほんのりピンク（ほお・おでこ）やいちごは金にしない
        for x0, y0, x1, y1 in skin:
            rib[y0:y1, x0:x1] = False
    ribn = grow(grow(shrink(rib, 3), 3), 5)
    wr = ramp(s, 0.08, 0.17) * ((h >= 312) | (h < 2)) * ribn
    gold = hsv2rgb(np.full_like(h, 42.0), np.clip(s * 1.5 + 0.25, 0, 0.8), np.clip(v * 0.95, 0, 1))
    out = rgb * (1 - w[..., None]) + cloth * w[..., None]
    out = out * (1 - wr[..., None]) + gold * wr[..., None]
    a[..., :3] = out * 255
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


COMIC = {"page01.webp": [((32, 677, 404, 995), [(80, 95, 215, 200), (60, 245, 135, 318)])]}  # 導入マンガでミーナが描かれているコマ（x0, y0, x1, y1）と、金にしない範囲（顔・いちご）
COMIC_KEEP = ROOT / "art-src" / "comic_orig"


def main():
    COMIC_KEEP.mkdir(parents=True, exist_ok=True)
    for name, rects in COMIC.items():  # マンガのコマも同じ色合いに（元の絵は art-src/comic_orig/）
        dst = ART / "comic" / name; orig = COMIC_KEEP / name
        if not orig.exists():
            shutil.copy(dst, orig)
        page = Image.open(orig).convert("RGBA")
        for r, face in rects:
            page.paste(recolor(page.crop(r), hair_top=285, skin=face), r[:2])
        page.convert("RGB").save(dst, quality=90, method=6)
        print("塗り替え", name)
    KEEP.mkdir(parents=True, exist_ok=True)
    for src in sorted(ART.glob("portrait_mina*.webp")):
        orig = KEEP / src.name
        if not orig.exists():
            shutil.copy(src, orig)
        recolor(Image.open(orig)).save(src, quality=90, method=6)
        print("塗り替え", src.name)


if __name__ == "__main__":
    main()

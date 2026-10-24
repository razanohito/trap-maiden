"""部屋の床・壁・置き物の絵（Gemini / Nano Banana）をゲームに入れる → art/rooms/

入力: art-src/rooms/<部屋>_floor.* ・ <部屋>_wall.* ・ <部屋>_prop.*（png / webp / jpg。無い物は飛ばす）
  部屋: hall（大広間）library（東の書庫）gallery（回廊）greenhouse（温室）dungeon（地下牢）chapel（礼拝堂）attic（屋根裏）clock（大時計の間）
出力:
  - art/rooms/<部屋>_floor.webp … 床の模様。1マス 96px（盤面の 48px の2倍）で最大 4x4 マス分 = 384px。
    絵の中のタイルの繰り返しを探し、タイル1枚がゲームの1マスになるよう縮める。継ぎ目なしにつながる
  - art/rooms/<部屋>_wall.webp  … 外壁の模様。最大 2x2 マス分 = 192px。継ぎ目なし
  - art/rooms/<部屋>_prop.webp  … 部屋の中の柱・本棚など（地図の内側の #）。96px 四方、緑の背景を抜き、足もとを下にそろえる
  - tools/sim/out/rooms_preview.png … 確認用（床を 3x3 並べて継ぎ目を見る）

使い方: python tools/import_rooms.py
"""
from pathlib import Path

import numpy as np
from PIL import Image

from greenkey import key_green

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art-src" / "rooms"
OUT = ROOT / "art" / "rooms"
PREVIEW = ROOT / "tools" / "sim" / "out" / "rooms_preview.png"
ROOMS = ("hall", "library", "gallery", "greenhouse", "dungeon", "chapel", "attic", "clock")  # MAPS の順
CELL = 96  # 1マス（2倍の解像度）


def find(name):
    for ext in ("png", "webp", "jpg", "jpeg"):
        p = SRC / f"{name}.{ext}"
        if p.exists():
            return p
    return None


def square(im):
    w, h = im.size
    s = min(w, h)
    return im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))


def period(gray, axis):
    """模様の繰り返し（タイル1枚の大きさ）を自己相関で探す。見つからなければ None"""
    g = np.abs(np.diff(gray, axis=axis)).mean(axis=1 - axis)  # その向きの線の強さ
    g = g - g.mean()
    n = len(g)
    ac = np.correlate(g, g, "full")[n - 1:]
    ac /= ac[0] + 1e-9
    lo, hi = n // 10, n // 2
    k = int(np.argmax(ac[lo:hi])) + lo
    return k if ac[k] > .25 else None


def fit_tiles(im, tiles):
    """タイルの目地がゲームのマス目にそろうよう、繰り返しの整数倍で切って tiles マス分に縮める"""
    im = square(im.convert("RGB"))
    gray = np.asarray(im.convert("L")).astype(float)
    px, py = period(gray, 1), period(gray, 0)
    p = None
    if px and py and abs(px - py) <= max(px, py) * .12:
        p = (px + py) / 2
    elif px or py:
        p = px or py
    if p:
        k = max(1, round(im.width / p))  # 画像の中の繰り返しの数
        size = int(round(p * k))
        im = im.crop((0, 0, min(size, im.width), min(size, im.height)))
        out = im.resize((CELL * k, CELL * k), Image.LANCZOS)  # 繰り返し1つ = 1マス
        n = min(k, tiles)  # 繰り返しが少ない絵は、そのまま繰り返して敷く
        return out.crop((0, 0, CELL * n, CELL * n))
    return im.resize((CELL * tiles, CELL * tiles), Image.LANCZOS)


def seamless(im):
    """半分ずらした絵と、ふちほどずらした側を濃く混ぜて、上下左右の継ぎ目を消す"""
    a = np.asarray(im.convert("RGB")).astype(float)
    h, w, _ = a.shape
    rolled = np.roll(np.roll(a, h // 2, 0), w // 2, 1)
    yy = 1 - np.abs(np.linspace(-1, 1, h))[:, None]
    xx = 1 - np.abs(np.linspace(-1, 1, w))[None, :]
    wgt = np.clip(np.minimum(yy, xx) * 3, 0, 1)[..., None]  # 真ん中は元の絵、ふちはずらした絵
    out = a * wgt + rolled * (1 - wgt)
    return Image.fromarray(out.round().clip(0, 255).astype(np.uint8), "RGB")


def prop(im):
    g = key_green(im)
    g = g.crop(g.getbbox())
    s = min((CELL - 6) / g.width, (CELL - 4) / g.height)
    g = g.resize((max(1, round(g.width * s)), max(1, round(g.height * s))), Image.LANCZOS)
    out = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    out.alpha_composite(g, ((CELL - g.width) // 2, CELL - 3 - g.height))  # 足もとをマスの下にそろえる
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for room in ROOMS:
        for kind in ("floor", "wall", "prop"):
            src = find(f"{room}_{kind}")
            if not src:
                continue
            im = Image.open(src)
            if kind == "floor":
                out = seamless(fit_tiles(im, 4))
            elif kind == "wall":
                out = seamless(fit_tiles(im, 2))
            else:
                out = prop(im)
            out.save(OUT / f"{room}_{kind}.webp", quality=90, method=6)
            made.append((room, kind, out))
            print(f"{room}_{kind}", out.size)
    if not made:
        print("art-src/rooms/ に絵がありません")
        return
    # 確認用: 部屋ごとに 床3x3 ・ 壁2x2 ・ 置き物
    rows = sorted({r for r, _, _ in made}, key=ROOMS.index)
    sheet = Image.new("RGB", (CELL * 4 * 3 // 2 + CELL * 2 + CELL + 40, (CELL * 4 * 3 // 2 + 10) * len(rows)), (40, 30, 80))
    for i, room in enumerate(rows):
        y = i * (CELL * 6 + 10)
        for r, kind, im in made:
            if r != room:
                continue
            if kind == "floor":
                t = Image.new("RGB", (im.width * 3, im.height * 3))
                for k in range(9):
                    t.paste(im, ((k % 3) * im.width, (k // 3) * im.height))
                sheet.paste(t.resize((CELL * 6, CELL * 6)), (0, y))
            elif kind == "wall":
                t = Image.new("RGB", (im.width * 2, im.height * 2))
                for k in range(4):
                    t.paste(im, ((k % 2) * im.width, (k // 2) * im.height))
                sheet.paste(t.resize((CELL * 2, CELL * 2)), (CELL * 6 + 20, y))
            else:
                bg = Image.new("RGBA", im.size, (90, 70, 120, 255))
                bg.alpha_composite(im)
                sheet.paste(bg.convert("RGB"), (CELL * 6 + 20, y + CELL * 2 + 20))
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(PREVIEW)
    print("確認用:", PREVIEW.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()

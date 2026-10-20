"""Steam のストア用の画像（カプセル・ライブラリ）を作る → steam/capsules/

- 背景: ストア用スクリーンショットの盤面（steam/screenshots/en_03_night.png。tools/sim/shot_store.js で撮る）を暗くぼかす
- 絵: 喜びの立ち絵（art-src/happy、tools/cut_happy.py と同じ方法で背景を抜く）
- 文字: Shippori Mincho B1（art-src/fonts。tools/make_fonts.py が取ってくる）
大きさは Steamworks の「グラフィックアセット」の決まり（2026年10月時点）に合わせる。

使い方: python tools/make_capsules.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import cut_happy

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "steam" / "capsules"
SHOT = ROOT / "steam" / "screenshots" / "en_03_night.png"
FONT = ROOT / "art-src" / "fonts" / "shipporiminchob1_ShipporiMinchoB1-ExtraBold.ttf"
GOLD, GOLD_HI, INK = (201, 162, 74), (241, 217, 142), (21, 16, 23)

cut_happy.H = 1400
GIRLS = {n: cut_happy.cut(ROOT / "art-src" / "happy" / f"{n}_portrait_happy.png") for n in ("lily", "mina", "noel", "cecil")}


def background(w, h):
    board = Image.open(SHOT).convert("RGB").crop((497, 285, 1423, 880))
    s = max(w / board.width, h / board.height)
    board = board.resize((round(board.width * s) + 1, round(board.height * s) + 1), Image.LANCZOS)
    board = board.crop(((board.width - w) // 2, (board.height - h) // 2, (board.width - w) // 2 + w, (board.height - h) // 2 + h))
    board = board.filter(ImageFilter.GaussianBlur(max(2, w // 300)))
    dark = Image.new("RGB", (w, h), INK)
    im = Image.blend(board, dark, .45).convert("RGBA")
    # ふちを暗くする（真ん中の明かり）
    v = Image.new("L", (w, h), 0)
    ImageDraw.Draw(v).ellipse((-w * .15, -h * .3, w * 1.15, h * 1.3), fill=255)
    v = v.filter(ImageFilter.GaussianBlur(min(w, h) // 4))
    im = Image.composite(im, Image.new("RGBA", (w, h), INK + (255,)), v)
    return im


def girl(name, height):
    g = GIRLS[name]
    return g.resize((round(g.width * height / g.height), height), Image.LANCZOS)


def paste_girls(im, layout):
    """layout: [(名前, 中心x, 下端y, 高さ)] 後ろから順に"""
    for name, cx, bottom, h in layout:
        g = girl(name, h)
        sh = Image.new("RGBA", g.size, (0, 0, 0, 0))
        sh.putalpha(g.getchannel("A").point(lambda a: a * .55))
        sh = sh.filter(ImageFilter.GaussianBlur(max(3, h // 60)))
        im.alpha_composite(sh, (round(cx - g.width / 2 + h * .015), round(bottom - h + h * .015)))
        im.alpha_composite(g, (round(cx - g.width / 2), round(bottom - h)))


def text(im, xy, s, size, anchor="la", fill=GOLD_HI, glow=True, spacing=0):
    f = ImageFont.truetype(str(FONT), size)
    d = ImageDraw.Draw(im)
    if glow:
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).text(xy, s, font=f, anchor=anchor, fill=(0, 0, 0, 230), stroke_width=max(2, size // 12), stroke_fill=(0, 0, 0, 230))
        im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(max(2, size // 14))))
    d.text(xy, s, font=f, anchor=anchor, fill=fill, stroke_width=max(1, size // 40), stroke_fill=(90, 60, 20))
    return d.textbbox(xy, s, font=f, anchor=anchor)


def logo(im, cx, cy, width, sub=True):
    """TRAP OF LILY（と小さくトラップオブリリー）を中心 (cx, cy)、横幅 width に収める"""
    size = 200
    f = ImageFont.truetype(str(FONT), size)
    tw = ImageDraw.Draw(im).textlength("TRAP OF LILY", font=f)
    size = int(size * width / tw)
    box = text(im, (cx, cy), "TRAP OF LILY", size, anchor="mm")
    if sub:
        text(im, (cx, box[3] + size * .12), "トラップオブリリー", max(12, int(size * .36)), anchor="mt", fill=GOLD)
    # 細い金の線
    d = ImageDraw.Draw(im)
    y = box[1] - size * .18
    d.line((cx - width * .32, y, cx + width * .32, y), fill=GOLD + (200,), width=max(1, size // 40))
    return box


def save(im, name):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    (im.convert("RGB") if name.endswith(".jpg") else im).save(p, quality=92)
    print(p.relative_to(ROOT).as_posix(), im.size)


def capsule_wide(w, h, name, girls_scale=1.0, logo_w=.46):
    im = background(w, h)
    gh = int(h * 1.05 * girls_scale)
    paste_girls(im, [("mina", w * .66, h * 1.02, int(gh * .86)), ("cecil", w * .95, h * 1.02, int(gh * .86)),
                     ("noel", w * .77, h * 1.06, int(gh * .93)), ("lily", w * .86, h * 1.08, gh)])
    logo(im, w * .27, h * .48, w * logo_w)
    save(im, name)


def capsule_tall(w, h, name):
    im = background(w, h)
    gh = int(h * .78)
    paste_girls(im, [("mina", w * .2, h * 1.02, int(gh * .82)), ("cecil", w * .82, h * 1.02, int(gh * .82)),
                     ("noel", w * .34, h * 1.04, int(gh * .9)), ("lily", w * .62, h * 1.06, gh)])
    logo(im, w * .5, h * .16, w * .86)
    save(im, name)


def main():
    capsule_wide(920, 430, "header_capsule_920x430.jpg")
    capsule_wide(1232, 706, "main_capsule_1232x706.jpg")
    # 小さいカプセルは文字を大きく、絵は1人
    im = background(462, 174)
    paste_girls(im, [("lily", 462 * .86, 174 * 1.25, int(174 * 1.4))])
    logo(im, 462 * .38, 174 * .46, 462 * .66, sub=False)
    save(im, "small_capsule_462x174.jpg")
    capsule_tall(748, 896, "vertical_capsule_748x896.jpg")
    capsule_tall(600, 900, "library_capsule_600x900.jpg")
    # ライブラリのヒーロー（文字なし。真ん中にロゴが重なるので絵は左右に寄せる）
    w, h = 3840, 1240
    im = background(w, h)
    paste_girls(im, [("mina", w * .12, h * 1.02, int(h * .95)), ("noel", w * .24, h * 1.04, int(h * 1.0)),
                     ("cecil", w * .76, h * 1.02, int(h * .95)), ("lily", w * .88, h * 1.05, int(h * 1.08))])
    save(im, "library_hero_3840x1240.jpg")
    # ライブラリのロゴ（透明の背景）
    im = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    logo(im, 640, 330, 1180)
    save(im, "library_logo_1280x720.png")


if __name__ == "__main__":
    main()

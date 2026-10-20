"""Steam の実績アイコン（256x256 の JPG、取った絵と取っていない灰色の絵）を作る → steam/achievements/

ゲームの実績（src/game.html の ACH）と同じ並び。Steamworks の API 名は ACH_<id を大文字>（desktop/main.js と同じ）。
絵は罠のアイコン（art/icons）・エフェクト（art/fx の 1 コマ）・逃げる子の顔（art-src/happy）を金の枠に入れる。

使い方: python tools/make_ach_icons.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

import cut_happy

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "steam" / "achievements"
S = 256

# id: (絵の種類, 名前)  icon=art/icons, fx=art/fx の 4 コマ目, face=逃げる子の顔, faces=4人
ACH = [
    ("night1", "face", "lily"), ("stage10", "icon", "bear"), ("stage20", "icon", "blade"), ("stage40", "face", "lily"),
    ("challenge", "faces", ""), ("combo10", "icon", "spring"), ("combo20", "icon", "ice"), ("combo30", "icon", "fire"),
    ("fusion", "icon", "rock"), ("fusion20", "icon", "vortex"), ("triple", "fx", "bomb"), ("crash", "fx", "hurt"),
    ("pit", "fx", "pit"), ("oiuchi", "icon", "caltrop"), ("weak", "fx", "fire"), ("items", "fx", "mana"),
    ("crown", "fx", "keys"), ("nohit", "face", "noel"), ("editor", "face", "cecil"), ("all4", "faces", ""),
]
cut_happy.H = 900
FACES = {}


def face(name):
    if name not in FACES:
        g = cut_happy.cut(ROOT / "art-src" / "happy" / f"{name}_portrait_happy.png")
        w = g.width
        FACES[name] = g.crop((int(w * .18), 0, int(w * .82), int(w * .64)))  # 頭のあたり
    return FACES[name]


def art(kind, name):
    if kind == "icon":
        return Image.open(ROOT / "art" / "icons" / f"{name}.png").convert("RGBA")
    if kind == "fx":
        strip = Image.open(ROOT / "art" / "fx" / f"{name}.png").convert("RGBA")
        n = max(1, strip.width // strip.height)
        k = min(3, n - 1)
        return strip.crop((k * strip.height, 0, (k + 1) * strip.height, strip.height))
    if kind == "face":
        return face(name)
    im = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    for i, n in enumerate(("mina", "cecil", "noel", "lily")):
        f = face(n).resize((220, 220), Image.LANCZOS)
        im.alpha_composite(f, ((0, 180, 20, 160)[i], (20, 20, 170, 170)[i]))
    return im


def frame(inner):
    im = Image.new("RGBA", (S, S), (42, 33, 48, 255))
    d = ImageDraw.Draw(im)
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((30, 30, S - 30, S - 30), fill=(110, 84, 120, 255))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(26)))
    pix = inner.width <= 64  # ドット絵は角を立てたまま大きくする
    inner = inner.resize((196, 196), Image.NEAREST if pix else Image.LANCZOS)
    im.alpha_composite(inner, ((S - 196) // 2, (S - 196) // 2))
    d.rectangle((4, 4, S - 5, S - 5), outline=(201, 162, 74, 255), width=8)
    d.rectangle((14, 14, S - 15, S - 15), outline=(241, 217, 142, 255), width=2)
    return im.convert("RGB")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for aid, kind, name in ACH:
        im = frame(art(kind, name))
        api = "ACH_" + aid.upper()
        im.save(OUT / f"{api}.jpg", quality=92)
        gray = ImageOps.grayscale(im).point(lambda v: int(v * .55))
        gray.convert("RGB").save(OUT / f"{api}_locked.jpg", quality=92)
    print(len(ACH), "個の実績アイコンを作りました:", OUT.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()

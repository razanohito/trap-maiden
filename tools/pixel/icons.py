"""火薬樽の罠アイコン（64x64）を、ほかの罠アイコンと同じ石のタイルと金の枠で描く → art/icons/keg.png

枠（外周1ドットと四隅の飾り 8x8）は art/icons/bear.png から写す。中の石畳と樽はここで点を打って描く。
使い方: python tools/pixel/icons.py
"""
import math
import random
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import big, hexc  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ICONS = ROOT / 'art' / 'icons'


def mix(a, b, t):
    return tuple(round(a[k] * (1 - t) + b[k] * t) for k in range(3)) + (255,)


def keg():
    S = 64
    im = Image.new('RGBA', (S, S))
    p = im.load()
    rnd = random.Random(7)
    base, grout, hi, lo = hexc('#7b739f'), hexc('#5b5484'), hexc('#8f88b2'), hexc('#6b6392')
    # 石畳（16px 角。目地・明るい上辺・左上から差す灯りのにじみ）
    for y in range(S):
        for x in range(S):
            tx, ty = (x + 4) % 16, (y + 2) % 16
            c = base
            if rnd.random() < .08:
                c = mix(c, lo if rnd.random() < .5 else hi, .6)
            if ty == 1:
                c = hi
            if tx == 0 or ty == 0:
                c = grout
            elif tx == 15 or ty == 15:
                c = lo
            glow = max(0, 1 - math.hypot(x - 6, y - 6) / 26)
            c = mix(c, hexc('#e0a060'), glow * .45)
            p[x, y] = c
    # 樽の影
    for y in range(S):
        for x in range(S):
            if ((x - 33) / 19) ** 2 + ((y - 53) / 5) ** 2 <= 1:
                p[x, y] = mix(p[x, y], hexc('#2a2450'), .55)
    wood = [hexc(c) for c in ('#e0a46a', '#c98a52', '#a86c3e', '#8a5430', '#6a3e22')]
    hoop, hoop_hi, hoop_lo = hexc('#6e6a80'), hexc('#c8c4d8'), hexc('#3a3448')
    ink = hexc('#2a1a20')
    top, bot, cx = 14, 52, 32
    for y in range(top, bot + 1):
        t = (y - top) / (bot - top)
        w = 13 + 3.2 * math.sin(math.pi * t)  # ふくらんだ胴
        for x in range(int(cx - w) - 1, int(cx + w) + 2):
            u = (x - cx) / w
            if abs(u) > 1:
                continue
            edge = abs(u) > .93 or y in (top, bot)
            # 板（縦に6枚）の陰影。左上が明るい
            k = int((u + 1) / 2 * 6)
            shade = .5 + .5 * u + (.12 if k % 2 else 0)
            col = wood[min(4, max(0, int(shade * 4.2)))]
            if abs(((u + 1) / 2 * 6) % 1) < .12:
                col = wood[4]  # 板の継ぎ目
            for hy in (.17, .5, .83):  # 鉄の輪
                d = t - hy
                if abs(d) < .045:
                    col = hoop_hi if d < -.015 and u < .3 else (hoop_lo if u > .55 else hoop)
            p[x, y] = ink if edge else col
    # ふた（楕円）
    for y in range(top - 5, top + 4):
        for x in range(cx - 15, cx + 16):
            e = ((x - cx) / 13.5) ** 2 + ((y - top) / 4.2) ** 2
            if e <= 1:
                inner = ((x - cx) / 11) ** 2 + ((y - top) / 3) ** 2 <= 1
                col = hexc('#b07444') if inner else hexc('#d8a06a')
                if inner and (x - cx) % 5 == 0:
                    col = hexc('#7a4a2a')
                p[x, y] = ink if e > .86 else col
    # 導火線と火花
    fuse = [(36, 12), (37, 11), (38, 10), (39, 9), (40, 9), (41, 8), (42, 8), (43, 7), (44, 7), (45, 7)]
    for (x, y) in fuse:
        p[x, y] = hexc('#e8dcc0')
        p[x, y + 1] = hexc('#6a5a48')
    spark = {(46, 6): '#ffffff', (45, 6): '#ffe27a', (47, 6): '#ffe27a', (46, 5): '#ffe27a', (46, 7): '#ffe27a',
             (44, 5): '#ff9a3a', (48, 5): '#ff9a3a', (44, 8): '#ff9a3a', (48, 8): '#ff9a3a', (46, 3): '#ffb35a',
             (46, 9): '#ff9a3a', (49, 6): '#ffb35a', (43, 6): '#ffb35a', (50, 4): '#ffe27a', (42, 3): '#ffe27a'}
    for (x, y), c in spark.items():
        p[x, y] = hexc(c)
    # 胴の中央に、炎の印の札
    for y in range(29, 37):
        for x in range(27, 38):
            col = hexc('#f2c24a') if 28 <= x <= 36 and 30 <= y <= 35 else ink
            if 29 <= x <= 35 and 31 <= y <= 34:
                col = hexc('#d03a3a')
            p[x, y] = col
    for (x, y), c in {(32, 31): '#ffb35a', (31, 32): '#ffb35a', (32, 32): '#ffe27a', (31, 33): '#ffb35a', (32, 33): '#ffe27a',
                      (33, 33): '#ffb35a', (31, 34): '#ffb35a', (32, 34): '#ffe27a', (33, 34): '#ffb35a', (33, 32): '#ff9a3a'}.items():
        p[x, y] = hexc(c)  # 札の炎の印
    # 枠を bear.png から写す
    fr = Image.open(ICONS / 'bear.png').convert('RGBA')
    fp = fr.load()
    for y in range(S):
        for x in range(S):
            if x < 2 or y < 2 or x > S - 3 or y > S - 3 or (min(x, S - 1 - x) < 8 and min(y, S - 1 - y) < 8):
                p[x, y] = fp[x, y]
    return im


def main():
    im = keg()
    im.save(ICONS / 'keg.png')
    print('火薬樽のアイコン', (ICONS / 'keg.png').relative_to(ROOT).as_posix())
    row = Image.new('RGBA', (64 * 4 + 40, 64 + 16), (40, 30, 60, 255))
    for i, n in enumerate(('bear', 'fire', 'rock', 'keg')):
        row.alpha_composite(Image.open(ICONS / f'{n}.png').convert('RGBA'), (8 + i * 72, 8))
    out = ROOT / 'tools' / 'sim' / 'out' / 'keg_icon.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    big(row, 4).save(out)


if __name__ == '__main__':
    main()

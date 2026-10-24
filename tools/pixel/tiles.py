"""盤面の床・壁・置き物のドット絵を作る → art/pixel/room_<部屋>.png

1マス 24x24 ドット（盤面には 2倍の 48px で描く）。シートは横に並べた 24x32 のコマ。
マスの絵はコマの下 24 行に入る。柱や石像など背の高い物は上の 8 行まではみ出してよい（奥のマスに重なる）。
コマの順（ゲームの TILE_IDX と同じ）:
  0 床A  1 床B（市松のもう片方）  2 壁の上面  3 壁の正面（上の壁で、下が床のとき）  4 部屋の中の置き物（柱・本棚など）
  5 扉  6 トゲ床  7 シャンデリアの真下の紋章  8 奈落  9 槍の石像  10 絨毯  11 燭台（コマの上に置く。ほかと違い下寄せではない）
  12〜15 床A・床Bの別の模様（同じ模様が並ばないよう、ゲームの側でマスごとに選ぶ）  16 壁の正面の飾り（旗・絵・窓など。3マスに1つ）
使い方: python tools/pixel/tiles.py  （確認用 tools/sim/out/pixel_rooms.png も書き出す）
"""
import math
import random
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import big, hexc, render, rows  # noqa: E402,F401
import props  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'art' / 'pixel'
PREVIEW = ROOT / 'tools' / 'sim' / 'out' / 'pixel_rooms.png'
TS, CH = 24, 32
ORDER = ('floorA', 'floorB', 'wallTop', 'wallFace', 'prop', 'door', 'spikes', 'emblem', 'pit', 'statue', 'carpet', 'torch',
         'floorA2', 'floorB2', 'floorA3', 'floorB3', 'wallFace2')


class Px:
    """24x24 のマスに点を打つ"""

    def __init__(self, w=TS, h=TS):
        self.im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        self.p = self.im.load()
        self.w, self.h = w, h

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h and c:
            self.p[x, y] = hexc(c) if isinstance(c, str) else c

    def rect(self, x0, y0, x1, y1, c):  # x1, y1 を含む
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, c)

    def get(self, x, y):
        return self.p[x % self.w, y % self.h]


def mix(a, b, t):
    a, b = hexc(a), hexc(b)
    return '#%02x%02x%02x' % tuple(round(a[k] * (1 - t) + b[k] * t) for k in range(3))


# ---------- 床 ----------
def slab(c, hi, lo, grout, vein, seed, specks=6, veins=1, inlay=None):
    """大きな石板1枚（上と左が明るく、下と右に目地）"""
    t = Px()
    rnd = random.Random(seed)
    t.rect(0, 0, 23, 23, c)
    for _ in range(veins):  # 大理石のすじ
        x, y = rnd.randrange(3, 20), rnd.randrange(3, 20)
        dx = rnd.choice((-1, 1))
        for _ in range(rnd.randrange(6, 12)):
            t.set(x, y, vein)
            if rnd.random() < .55:
                x += dx
            else:
                y += 1
            if rnd.random() < .2:
                dx = -dx
    for _ in range(specks):
        t.set(rnd.randrange(2, 22), rnd.randrange(2, 22), mix(c, lo, .5) if rnd.random() < .6 else mix(c, hi, .5))
    t.rect(0, 0, 22, 0, hi)
    t.rect(0, 0, 0, 22, hi)
    t.rect(1, 1, 21, 1, mix(c, hi, .4))
    t.rect(0, 23, 23, 23, grout)
    t.rect(23, 0, 23, 23, grout)
    t.rect(1, 22, 22, 22, lo)
    t.rect(22, 1, 22, 22, lo)
    if inlay:  # 四隅のひし形の象眼（4枚のマスが集まるところで1つのひし形になる）
        for (x, y) in ((0, 0), (23, 0), (0, 23), (23, 23)):
            t.set(x, y, inlay)
    return t.im


def planks(c, hi, lo, gap, seed):
    """木の床（横長の板。継ぎ目をずらす）"""
    t = Px()
    rnd = random.Random(seed)
    for row in range(4):
        y0 = row * 6
        shade = mix(c, lo, rnd.random() * .25)
        t.rect(0, y0, 23, y0 + 5, shade)
        t.rect(0, y0, 23, y0, mix(shade, hi, .5))
        t.rect(0, y0 + 5, 23, y0 + 5, gap)
        j = (row * 9 + 5) % 24
        t.rect(j, y0, j, y0 + 5, gap)
        for _ in range(3):  # 木目
            x, y = rnd.randrange(0, 20), y0 + rnd.randrange(2, 5)
            for k in range(rnd.randrange(3, 7)):
                t.set(x + k, y, mix(shade, lo, .45))
        if rnd.random() < .5:
            t.set(rnd.randrange(2, 22), y0 + 3, mix(shade, gap, .7))  # 節
    return t.im


def bricks(c, hi, lo, mortar, bw=8, bh=4, seed=1, rough=.15):
    """れんが（上から見た壁の上面・正面で使う）"""
    t = Px()
    rnd = random.Random(seed)
    for row in range(TS // bh):
        y0 = row * bh
        off = (row % 2) * (bw // 2)
        for k in range(-1, TS // bw + 1):
            x0 = k * bw + off
            shade = mix(c, lo if rnd.random() < .5 else hi, rnd.random() * rough)
            t.rect(x0, y0, x0 + bw - 2, y0 + bh - 2, shade)
            t.rect(x0, y0, x0 + bw - 2, y0, mix(shade, hi, .45))
            t.rect(x0, y0 + bh - 2, x0 + bw - 2, y0 + bh - 2, mix(shade, lo, .35))
            t.rect(x0 + bw - 1, y0, x0 + bw - 1, y0 + bh - 1, mortar)
        t.rect(0, y0 + bh - 1, 23, y0 + bh - 1, mortar)
    return t.im


def wall_face(top, face, trim, base, cap_hi):
    """上の壁の正面: 上 6 行は壁の上面、その下にれんがの面、金の飾り、幅木"""
    t = Px()
    t.im.paste(top.crop((0, 0, 24, 6)), (0, 0))
    t.rect(0, 6, 23, 6, cap_hi)
    t.im.paste(face.crop((0, 7, 24, 20)), (0, 7))
    t.rect(0, 20, 23, 20, trim)
    t.rect(0, 21, 23, 23, base)
    t.rect(0, 21, 23, 21, mix(base, '#ffffff', .12))
    return t.im


def cobble(c, hi, lo, gap, seed, moss=None, n=7):
    """丸い石を敷いた床（つなぎ目なしで並ぶ）"""
    t = Px()
    rnd = random.Random(seed)
    pts = [(rnd.uniform(0, 24), rnd.uniform(0, 24)) for _ in range(n)]
    shades = [mix(c, rnd.choice((hi, lo)), rnd.random() * .18) for _ in pts]
    for y in range(24):
        for x in range(24):
            ds = []
            for i, (px, py) in enumerate(pts):
                dx = min(abs(x - px), 24 - abs(x - px))
                dy = min(abs(y - py), 24 - abs(y - py))
                ds.append((math.hypot(dx, dy), i, px - x, py - y))
            ds.sort()
            (d1, i1, ox, oy), (d2, _, _, _) = ds[0], ds[1]
            if d2 - d1 < 1.3:
                col = gap
                if moss and rnd.random() < .07:
                    col = moss
            else:
                col = shades[i1]
                # 石の左上を明るく、右下を暗く
                ox = ((ox + 12) % 24) - 12
                oy = ((oy + 12) % 24) - 12
                if ox > 1.2 and oy > 1.2 and d2 - d1 < 3.2:
                    col = mix(col, hi, .5)
                elif ox < -1.2 and oy < -1.2 and d2 - d1 < 3.2:
                    col = mix(col, lo, .5)
            t.set(x, y, col)
    return t.im


def small_tiles(c, hi, lo, grout, seed, n=2, moss=None, accent=None):
    """小さな四角いタイル（n x n 枚で1マス）"""
    t = Px()
    rnd = random.Random(seed)
    k = 24 // n
    for j in range(n):
        for i in range(n):
            shade = mix(c, rnd.choice((hi, lo)), rnd.random() * .22)
            if accent and (i + j) % 2 == 0 and rnd.random() < .3:
                shade = accent
            x0, y0 = i * k, j * k
            t.rect(x0, y0, x0 + k - 1, y0 + k - 1, shade)
            t.rect(x0, y0, x0 + k - 2, y0, mix(shade, hi, .5))
            t.rect(x0, y0, x0, y0 + k - 2, mix(shade, hi, .3))
            t.rect(x0 + 1, y0 + k - 2, x0 + k - 2, y0 + k - 2, mix(shade, lo, .4))
            t.rect(x0, y0 + k - 1, x0 + k - 1, y0 + k - 1, grout)
            t.rect(x0 + k - 1, y0, x0 + k - 1, y0 + k - 1, grout)
            for _ in range(2):
                t.set(x0 + rnd.randrange(1, k - 2), y0 + rnd.randrange(1, k - 2), mix(shade, lo, .35))
    if moss:  # 目地のこけ
        for _ in range(10):
            x, y = rnd.randrange(24), rnd.choice((k - 1, 23)) if rnd.random() < .5 else rnd.randrange(24)
            if t.get(x, y)[:3] == hexc(grout)[:3]:
                t.set(x, y, moss)
    return t.im


def mosaic(c, c2, hi, lo, grout, accents, seed):
    """礼拝堂の石の床（大きな石板の四隅に色石のモザイク）"""
    t = Image.new('RGBA', (24, 24))
    t.alpha_composite(slab(c, hi, lo, grout, mix(c, hi, .4), seed, specks=4, veins=0))
    p = t.load()
    rnd = random.Random(seed)
    for (cx, cy) in ((0, 0), (24, 0), (0, 24), (24, 24)):  # 四隅の4分の1の円 = 4マスで1つの円
        for y in range(24):
            for x in range(24):
                d = math.hypot(x + .5 - cx, y + .5 - cy)
                if d < 5:
                    if d > 4.2 or 1.8 < d < 2.5:
                        p[x, y] = hexc(grout)
                    else:
                        p[x, y] = hexc(accents[0] if d > 3 else accents[1])
    return t


def parquet(c, hi, lo, gap, seed):
    """大時計の間の寄せ木の床（市松に縦横の板）"""
    t = Px()
    rnd = random.Random(seed)
    for by in range(2):
        for bx in range(2):
            vert = (bx + by) % 2 == 0
            for k in range(3):
                shade = mix(c, rnd.choice((hi, lo)), rnd.random() * .3)
                if vert:
                    x0, y0, x1, y1 = bx * 12 + k * 4, by * 12, bx * 12 + k * 4 + 3, by * 12 + 11
                else:
                    x0, y0, x1, y1 = bx * 12, by * 12 + k * 4, bx * 12 + 11, by * 12 + k * 4 + 3
                t.rect(x0, y0, x1, y1, shade)
                if vert:
                    t.rect(x1, y0, x1, y1, gap)
                    t.rect(x0, y0, x0, y1, mix(shade, hi, .4))
                else:
                    t.rect(x0, y1, x1, y1, gap)
                    t.rect(x0, y0, x1, y0, mix(shade, hi, .4))
    return t.im


def paneling(c, hi, lo, gap):
    """縦の板張り（壁の正面の下半分など）"""
    t = Px()
    for x in range(24):
        k = x % 6
        col = gap if k == 5 else (mix(c, hi, .45) if k == 0 else (mix(c, lo, .25) if k == 4 else c))
        t.rect(x, 0, x, 23, col)
    return t.im


def deco(base, g, pal, x=0, y=0):
    """壁の正面に飾り（方眼）を重ねる"""
    im = base.copy()
    im.alpha_composite(render(rows(g), pal), (x, y))
    return im


# ---------- 床の上の物 ----------
def spikes(plate, rim, tip, mid, dark):
    t = Px()
    t.rect(2, 2, 21, 21, plate)
    for x in range(2, 22):
        t.set(x, 2, rim)
        t.set(x, 21, mix(plate, dark, .5))
    for y in range(2, 22):
        t.set(2, y, rim)
        t.set(21, y, mix(plate, dark, .5))
    sp = ['..w..', '.wWn.', '.wWn.', 'wWWnn', '.ddd.']
    pal = dict(w=tip, W=mid, n=mix(mid, dark, .45), d=mix(plate, dark, .6))
    for sy in (3, 9, 15):
        for sx in (4, 10, 16):
            for j, r in enumerate(sp):
                for i, ch in enumerate(r):
                    if ch != '.':
                        t.set(sx + i - 1 + 1, sy + j + 1, pal[ch])
    return t.im


def ring_emblem(c, c2):
    t = Px()
    for y in range(24):
        for x in range(24):
            d = math.hypot(x - 11.5, y - 11.5)
            if abs(d - 9) < .6:
                t.set(x, y, c)
            elif abs(d - 5.5) < .55:
                t.set(x, y, c2)
    for (x, y) in ((11, 2), (12, 2), (11, 21), (12, 21), (2, 11), (2, 12), (21, 11), (21, 12)):
        t.set(x, y, c2)
    return t.im


def pit(rim_hi, rim_lo, c1, c2, c3, seed=3):
    t = Px()
    rnd = random.Random(seed)
    jag = [rnd.uniform(-1, 1) for _ in range(16)]
    for y in range(24):
        for x in range(24):
            a = math.atan2(y - 11.5, x - 11.5)
            k = (a + math.pi) / (2 * math.pi) * 16
            j = jag[int(k) % 16] * (1 - k % 1) + jag[(int(k) + 1) % 16] * (k % 1)
            r = 10 + j
            d = math.hypot(x - 11.5, (y - 11.5) * 1.08)
            if d > r:
                continue
            if d > r - 1.2:
                t.set(x, y, rim_hi if y > 11 else rim_lo)  # 奥（上）の縁は暗く、手前（下）の縁が光る
                continue
            depth = (y - 11.5 + 10) / 20  # 上ほど奥の壁が見える
            q = d / r
            if q > .78 and y < 12:
                col = c1
            elif q > .55:
                col = c2 if (x + y) % 2 or q < .66 else c1
            else:
                col = c3
            if depth > .8 and q > .7:
                col = c2
            t.set(x, y, col)
    return t.im


def carpet(c, hi, lo, edge, gold):
    t = Px()
    t.rect(3, 0, 20, 23, c)
    t.rect(3, 0, 3, 23, gold)
    t.rect(20, 0, 20, 23, gold)
    t.rect(4, 0, 4, 23, lo)
    t.rect(19, 0, 19, 23, lo)
    t.rect(5, 0, 5, 23, edge)
    t.rect(18, 0, 18, 23, edge)
    for y in range(24):  # ひし形
        w = abs(((y + 6) % 24) - 12) // 2
        for x in range(12 - w - 1, 12 + w + 1):
            if x in (12 - w - 1, 12 + w):
                t.set(x, y, gold)
            elif 6 <= x <= 17:
                t.set(x, y, hi)
    t.set(11, 6, gold)
    t.set(12, 6, gold)
    return t.im


def torch(gold, dark, wax):
    """燭台（炎はゲームの側で揺らして描く）。コマの上 7 行に入れる。ろうそくの上はしが 0 行目"""
    t = Px(TS, CH)
    g = rows('''
        ..........ww..........
        ..........ww..........
        ......GGGGGGGGGG......
        .......gggggggg.......
        ..........Gg..........
        ..........Gg..........
        .........GGgg.........
    ''')
    pal = dict(w=wax, G=gold, g=dark)
    im = render(g, pal, outline=False)
    t.im.alpha_composite(im, (1, 0))
    return t.im


def cell(im):
    """24x24 の絵を 24x32 のコマの下に置く（24x32 の絵はそのまま）"""
    c = Image.new('RGBA', (TS, CH), (0, 0, 0, 0))
    if im.height == CH:
        c.alpha_composite(im)
    else:
        c.alpha_composite(im, (0, CH - im.height))
    return c


def build(room):
    R = ROOMS[room]
    tiles = R['make']()
    sheet = Image.new('RGBA', (TS * len(ORDER), CH), (0, 0, 0, 0))
    for i, k in enumerate(ORDER):
        if k in tiles:
            sheet.alpha_composite(cell(tiles[k]), (i * TS, 0))
    return sheet


def stripes(c, c2, hi, w=4):
    """縦じまの壁紙"""
    t = Px()
    for x in range(24):
        col = c2 if x % (w * 2) < w else c
        if x % (w * 2) == 0:
            col = hi
        t.rect(x, 0, x, 23, col)
    return t.im


def damask(c, c2):
    """小さな模様の壁紙"""
    t = Px()
    t.rect(0, 0, 23, 23, c)
    for (x, y) in ((3, 2), (9, 6), (15, 2), (21, 6), (3, 10), (15, 10), (9, 14), (21, 14), (3, 18), (15, 18), (9, 22), (21, 22)):
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            t.set(x + dx, y + dy, c2)
    return t.im


def glass(frame, pane, hi, lo):
    """温室のガラスの壁（白い鉄の枠）"""
    t = Px()
    t.rect(0, 0, 23, 23, pane)
    for y in range(24):
        for x in range(24):
            if (x + y) % 9 == 0 and 3 < x < 20:
                t.set(x, y, hi)
    t.rect(0, 0, 23, 1, frame)
    t.rect(0, 11, 23, 12, frame)
    t.rect(0, 0, 1, 23, frame)
    t.rect(12, 0, 12, 23, frame)
    t.rect(2, 13, 11, 13, lo)
    t.rect(13, 13, 23, 13, lo)
    t.rect(2, 2, 11, 2, lo)
    t.rect(13, 2, 23, 2, lo)
    return t.im


def make(P):
    """部屋の色と形の決まり（P）から、マスの絵をそろえる"""
    f = {}
    for i, sfx in enumerate(('', '2', '3')):
        for half, key in ((0, 'floorA'), (1, 'floorB')):
            f[key + sfx] = P['floor'](half, i)
    top = P['top']
    f['wallTop'] = top
    f['wallFace'] = wall_face(top, P['face'], P['trim'], P['base'], P['cap'])
    f['wallFace2'] = deco(f['wallFace'], P['deco'][0], P['deco'][1], *P['deco'][2]) if P.get('deco') else f['wallFace']
    f['prop'] = P['prop']
    f['door'] = P.get('door') or props.door()
    f['spikes'] = spikes(*P.get('spikes', ('#3a3370', '#a8862e', '#f4f0fa', '#c8c0e4', '#1e1a40')))
    f['emblem'] = ring_emblem(*P.get('emblem', ('#d8b860', '#b8944a')))
    f['pit'] = pit(*P.get('pit', ('#9a90d4', '#3a3470', '#3e3680', '#262058', '#120f2c')))
    f['statue'] = props.statue(**P.get('statue', {}))
    f['carpet'] = carpet(*P.get('carpet', ('#c8487a', '#e0689a', '#9a2e58', '#f4d8a0', '#f2c24a')))
    f['torch'] = torch('#f2c24a', '#a87420', '#f4ead8')
    return f


# 壁の正面の飾り（方眼・色・置く位置）
BANNER = ("""
    GGGGGGGGGGGG
    .gRRRRRRRRg.
    .gRRRYYRRRg.
    .gRRYYYYRRg.
    .gRRRYYRRRg.
    .gRRRRRRRRg.
    .gRRRRRRRRg.
    .gRRRrrRRRg.
    .gRRr..rRRg.
    .gRr....rRg.
""", dict(G='#f2c24a', g='#b8862a', R='#d8508a', r='#a03466', Y='#ffe08a'), (6, 7))

PAINTING = ("""
    gGGGGGGGGGGGGg
    GbbbbbbbbbbbbG
    GbbbbbbWWbbbbG
    GbbbbbbWWbbbbG
    GbbbllbbbbbbbG
    GblllllbbllbbG
    GlLlLLlllLLllG
    GLLLLLLLLLLLLG
    GLLLLmLLLLLmLG
    gGGGGGGGGGGGGg
""", dict(G='#f2c24a', g='#b8862a', b='#7aa8d8', W='#fff4c8', l='#5a9a7a', L='#7ac08a', m='#4a7a5a'), (5, 8))

STAINED = ("""
    ....kkkk....
    ...kRRBBk...
    ..kRRYBBBk..
    ..kRYYYBBk..
    ..kkkkkkkk..
    ..kBBkGGGk..
    ..kBBkGGGk..
    ..kBYkGRGk..
    ..kBBkGGGk..
    ..kkkkkkkk..
""", dict(k='#3a3060', R='#e05a7a', B='#6a9ae8', Y='#ffe07a', G='#7ad09a'), (6, 8))

SHACKLES = ("""
    .i......i.
    .I......I.
    .i......i.
    .I......I.
    .i......i.
    IiI....IiI
    I.I....I.I
    III....III
""", dict(I='#9a96b0', i='#5a5670'), (7, 9))

ROUND_WINDOW = ("""
    ...wwwwww...
    ..wbbbbbbw..
    .wbbbYYbbbw.
    .wbbbYYbbbw.
    .wwwwwwwwww.
    .wbbbwwbbbw.
    .wbbbwwbbbw.
    ..wbbwwbbw..
    ...wwwwww...
""", dict(w='#c09a70', b='#5a6aa8', Y='#fff0b0'), (6, 9))

CLOCK = ("""
    ...gGGGGg...
    ..gYYYYYYg..
    .gYYYDYYYYg.
    .GYYYDYYYYG.
    .GYYYDDDYYG.
    .GYYYYYYYYG.
    .gYYYYYYYYg.
    ..gYYYYYYg..
    ...gGGGGg...
""", dict(G='#e8b84a', g='#a87a28', Y='#f4ead0', D='#3a2a20'), (6, 8))

SHELF = ("""
    wwwwwwwwwwww
    wDDDDDDDDDDw
    wDabcdeabcDw
    wDabcdeabcDw
    wwwwwwwwwwww
    wDDDDDDDDDDw
    wDcdeabDDeDw
    wDcdeabDaeDw
    wwwwwwwwwwww
""", dict(w='#8a5a3e', D='#3e2620', a='#ff9dbd', b='#9ad8c0', c='#b8a4f0', d='#ffd98a', e='#8ab0e8'), (6, 9))

VINE = ("""
    ..L..l....L.
    .LlL.Ll..LlL
    ..lLlLlLlL..
    ...l..L..l..
    ...L..l..L..
    ..FfL.L.LFf.
    ...l..l..l..
    ......L.....
""", dict(L='#6ac07a', l='#3e8a50', F='#ff9ac0', f='#ffe27a'), (6, 7))


def slab_floor(c, c2, hi, lo, grout, vein, inlay=None):
    hiB, loB, vB = mix(c2, '#ffffff', .2), mix(c2, '#000000', .18), mix(c2, '#ffffff', .1)

    def fl(half, i):
        if half == 0:
            return slab(c, hi, lo, grout, vein, 1 + i * 10, inlay=inlay, veins=(1, 0, 2)[i])
        return slab(c2, hiB, loB, grout, vB, 2 + i * 10, inlay=inlay, veins=(0, 1, 1)[i])
    return fl


def hall():
    return make(dict(
        floor=slab_floor('#6a62a4', '#5d5797', '#8b84c4', '#4f4988', '#36305f', '#7c74b8', inlay='#b49a62'),
        top=bricks('#3e3878', '#57509a', '#2c2860', '#221e4a', seed=4),
        face=bricks('#5a539c', '#7a72bc', '#423c80', '#2e2a5e', seed=5),
        trim='#e8b84a', base='#3a3470', cap='#8a82c4',
        deco=BANNER, prop=props.pillar(),
    ))


def library():
    face = Image.new('RGBA', (24, 24))
    face.alpha_composite(damask('#6a3a5a', '#8a5070'))
    face.alpha_composite(paneling('#7a4e38', '#9a6a4c', '#5a3828', '#3e2620').crop((0, 14, 24, 24)), (0, 14))
    return make(dict(
        floor=lambda half, i: planks(('#8e6248', '#84593f')[half], '#b08060', '#6a4632', '#4a3024', 3 + half * 7 + i * 13),
        top=bricks('#4a3044', '#644058', '#36223a', '#2a1a2e', bw=12, seed=6),
        face=face, trim='#e8b84a', base='#3e2620', cap='#8a6a7a',
        deco=SHELF, prop=props.bookshelf(),
        statue=dict(M='#d8ccc4', m='#ae9e98', n='#7e6e6a', V='#f0e8e4'),
        carpet=('#7a4aa8', '#9a6ac8', '#5a3088', '#e8d8f8', '#f2c24a'),
    ))


def gallery():
    return make(dict(
        floor=slab_floor('#5c6aa4', '#525e96', '#7e8cc4', '#434e86', '#2e3462', '#6e7cb8', inlay='#c8a860'),
        top=bricks('#2e3a6a', '#44508a', '#222c58', '#1a2248', seed=7),
        face=stripes('#3e4c8a', '#46549a', '#5a68aa', 3), trim='#e8b84a', base='#2a3262', cap='#7a88c4',
        deco=PAINTING, prop=props.vase(),
    ))


def greenhouse():
    return make(dict(
        floor=lambda half, i: small_tiles(('#b87a62', '#a87058')[half], '#d89a7a', '#8a5444', '#5a4a3a', 20 + half * 3 + i * 11, n=2, moss='#5a8a4a'),
        top=bricks('#e8e4f0', '#ffffff', '#b8b4c8', '#8a86a0', bw=12, bh=6, seed=8, rough=.05),
        face=glass('#ece8f4', '#7ab8b0', '#b8e8dc', '#5a9890'), trim='#ece8f4', base='#6a7a6a', cap='#ffffff',
        deco=VINE, prop=props.planter(),
        statue=dict(M='#cfe0d4', m='#a4bcac', n='#748c7c', V='#ecf6ee'),
        spikes=('#3a4a3a', '#8a9a5a', '#f4f0fa', '#c8d0c4', '#1a2418'),
        pit=('#a0c8a0', '#3a4a3a', '#3a5040', '#22322a', '#0e1812'),
    ))


def dungeon():
    return make(dict(
        floor=lambda half, i: cobble(('#64627e', '#5e5c78')[half], '#7a78a0', '#4e4c68', '#3a3852', 30 + half * 5 + i * 17, moss='#4e6a50', n=5),
        top=bricks('#34324a', '#4a4866', '#262438', '#1a1828', bw=12, bh=6, seed=9, rough=.3),
        face=bricks('#4a4864', '#625f84', '#36344e', '#24223a', bw=12, bh=6, seed=10, rough=.3),
        trim='#5a5670', base='#24223a', cap='#6e6c8c',
        deco=SHACKLES, prop=props.chained_block(), door=props.iron_door(),
        statue=dict(M='#a8a6bc', m='#848298', n='#5c5a70', V='#c8c6d8'),
        emblem=('#8a88a8', '#6a6888'),
    ))


def chapel():
    return make(dict(
        floor=lambda half, i: mosaic(('#8c86ac', '#827ca2')[half], '#6e68a0', '#a8a2c8', '#6a648e', '#4a4470', ('#7a74b0', '#b4a070'), 40 + half + i * 7),
        top=bricks('#5a5484', '#7470a4', '#46416e', '#34305a', seed=11),
        face=bricks('#9a94c0', '#b4aed8', '#7e78a8', '#5a5484', seed=12, rough=.1),
        trim='#e8b84a', base='#4a4470', cap='#c4bee4',
        deco=STAINED, prop=props.carved_pillar(),
        carpet=('#3a5aa8', '#5a7ac8', '#2a3a80', '#e8e0f8', '#f2c24a'),
    ))


def attic():
    return make(dict(
        floor=lambda half, i: planks(('#7e6a58', '#766250')[half], '#9a8470', '#5e4c3e', '#3e3228', 50 + half * 7 + i * 13),
        top=bricks('#4a3e36', '#5e5046', '#3a302a', '#2a221e', bw=12, bh=6, seed=13, rough=.2),
        face=paneling('#7a6450', '#9a8068', '#5a4838', '#3e3024'), trim='#5e4c3e', base='#3e3228', cap='#8a7a6a',
        deco=ROUND_WINDOW, prop=props.crates(),
        statue=dict(M='#d0c8bc', m='#aaa094', n='#7a7066', V='#ece6dc'),
        spikes=('#3e3430', '#8a7a4a', '#f4f0fa', '#c8c0c0', '#1e1814'),
        pit=('#a89a88', '#3e3430', '#3e3430', '#26201c', '#0e0c0a'),
    ))


def clock():
    face = stripes('#2e5a64', '#326270', '#4a7a84', 6)
    for x in range(0, 24, 12):
        for y in range(7, 20):
            face.putpixel((x, y), hexc('#a87a28'))
    return make(dict(
        floor=lambda half, i: parquet(('#6a4a3a', '#604234')[half], '#8a6a52', '#4a3228', '#2e2018', 60 + half * 3 + i * 9),
        top=bricks('#24404a', '#345a64', '#1a3038', '#12242a', seed=14),
        face=face, trim='#e8b84a', base='#1a3038', cap='#5a8a94',
        deco=CLOCK, prop=props.gear_pillar(),
        carpet=('#2e7a5a', '#4a9a7a', '#1e5a40', '#d8f0e0', '#e8b84a'),
        emblem=('#e8b84a', '#a87a28'),
    ))


ROOMS = dict(hall=dict(make=hall), library=dict(make=library), gallery=dict(make=gallery), greenhouse=dict(make=greenhouse),
             dungeon=dict(make=dungeon), chapel=dict(make=chapel), attic=dict(make=attic), clock=dict(make=clock))


def main(names=None):
    OUT.mkdir(parents=True, exist_ok=True)
    names = names or list(ROOMS)
    shots = []
    for n in names:
        sh = build(n)
        sh.save(OUT / f'room_{n}.png')
        shots.append((n, sh))
        print('部屋のドット絵', n, sh.size)
    # 確認用: 床を 4x3 に敷き、その上にほかのマスを並べる
    pv = Image.new('RGBA', (TS * 13, (CH + 24 * 4) * len(shots)), (30, 26, 56, 255))
    for r, (n, sh) in enumerate(shots):
        y0 = r * (CH + 24 * 4)
        pv.alpha_composite(sh, (0, y0))
        for j in range(4):
            for i in range(13):
                k = (0 if (i + j) % 2 == 0 else 1) + (0, 0, 12, 14)[(i * 7 + j * 13) % 4]
                pv.alpha_composite(sh.crop((k * TS, 8, k * TS + TS, CH)), (i * TS, y0 + CH + j * 24))
        for i in range(13):
            k = 16 if i % 3 == 1 else 3
            pv.alpha_composite(sh.crop((k * TS, 8, k * TS + TS, CH)), (i * TS, y0 + CH))
        for i, k in enumerate((4, 9, 6, 7, 8, 10, 11)):
            pv.alpha_composite(sh.crop((k * TS, 0, k * TS + TS, CH)), (i * 2 * TS - (0 if i else 0), y0 + CH + 24 + 16))
        pv.alpha_composite(sh.crop((5 * TS, 8, 6 * TS, CH)), (12 * TS, y0 + CH))
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    big(pv, 4).save(PREVIEW)
    print('確認用:', PREVIEW.relative_to(ROOT).as_posix())


if __name__ == '__main__':
    main(sys.argv[1:] or None)

"""ドット絵を文字の方眼から作る道具。

方眼は1文字が1ドット。'.' は透明。色は文字ごとのパレットで決める。
- outline(): ふちのドットを、そのドット自身の色を暗くした色にする（色つきの輪郭。黒一色よりやわらかい）
- mirror(): 左右反転。left(): 左半分から左右対称の絵を作る
"""
from PIL import Image

INK = (42, 24, 48)  # 輪郭を暗くするときに混ぜる色


def hexc(s):
    s = s.lstrip('#')
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)) + ((int(s[6:8], 16),) if len(s) == 8 else (255,))


def rows(s):
    """複数行の文字列 → 行のリスト（前後の空行と、行頭の共通の空白を除く）"""
    ls = [l for l in s.split('\n')]
    while ls and not ls[0].strip():
        ls.pop(0)
    while ls and not ls[-1].strip():
        ls.pop()
    ind = min(len(l) - len(l.lstrip()) for l in ls if l.strip())
    return [l[ind:] for l in ls]


def sym(half):
    """左半分の方眼（行のリスト）から、左右対称の方眼を作る"""
    return [h + h[::-1] for h in half]


def mirror(g):
    return [r[::-1] for r in g]


def pad(g, w, h, x=None, y=None):
    """g を w x h の方眼の中に置く（既定は左右中央・下寄せ）"""
    gw = max(len(r) for r in g)
    x = (w - gw) // 2 if x is None else x
    y = h - len(g) if y is None else y
    out = [['.'] * w for _ in range(h)]
    for j, r in enumerate(g):
        for i, ch in enumerate(r):
            if ch != '.' and 0 <= y + j < h and 0 <= x + i < w:
                out[y + j][x + i] = ch
    return [''.join(r) for r in out]


def stamp(g, patch, x, y):
    """g の (x, y) に patch を重ねる（patch の '.' は下を残す、' ' は透明にする）"""
    out = [list(r) for r in g]
    for j, r in enumerate(patch):
        for i, ch in enumerate(r):
            if ch == '.':
                continue
            yy, xx = y + j, x + i
            if 0 <= yy < len(out) and 0 <= xx < len(out[yy]):
                out[yy][xx] = '.' if ch == ' ' else ch
    return [''.join(r) for r in out]


def shift(g, dx=0, dy=0):
    h, w = len(g), len(g[0])
    out = [['.'] * w for _ in range(h)]
    for j in range(h):
        for i in range(w):
            if g[j][i] != '.' and 0 <= j + dy < h and 0 <= i + dx < w:
                out[j + dy][i + dx] = g[j][i]
    return [''.join(r) for r in out]


def render(g, pal, outline=True, dark=.62, keep='', oc=None):
    """方眼 → RGBA 画像。outline=True なら外周のドットを暗くする（keep の文字は暗くしない。oc で文字ごとの輪郭の色を決められる）"""
    oc = oc or {}
    h, w = len(g), max(len(r) for r in g)
    g = [r.ljust(w, '.') for r in g]
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    px = im.load()
    for y in range(h):
        for x in range(w):
            ch = g[y][x]
            if ch == '.':
                continue
            if ch not in pal:
                raise KeyError(f'色が無い文字 {ch!r} ({x},{y})')
            c = hexc(pal[ch])
            if outline and ch not in keep:
                edge = any(not (0 <= y + dy < h and 0 <= x + dx < w) or g[y + dy][x + dx] == '.'
                           for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                if edge and ch in oc:
                    c = hexc(oc[ch])
                elif edge:
                    c = tuple(round(c[k] * (1 - dark) + INK[k] * dark) for k in range(3)) + (c[3],)
            px[x, y] = c
    return im


def big(im, k):
    return im.resize((im.width * k, im.height * k), Image.NEAREST)

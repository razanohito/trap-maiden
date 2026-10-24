"""盤面のキャラのドット絵を作る → art/pixel/<名前>.png

1コマ 32x32 ドット（盤面には 2倍の 64px で描く。マスは 48px）。足もとはコマのいちばん下の行。
シート（横4コマ）:
  女の子: 0〜3行 歩き（下・左・右・上 向き。4コマ = 左足・そろい・右足・そろい）
          4行 立ち（下・左・右・上）  5行 やられ  6行 ピンチ  7行 喜びジャンプ（4コマ）
  侵入者: 0〜3行 歩き  4行 立ち
キャラの絵（方眼）は tools/pixel/chars.py。文字の意味はキャラどうしでそろえてある:
  H I h d 髪（地・つや・影・濃い影）  S s 肌  K 目や線  E e W 目  M 口  B ほお
  P p 服の主な色  A a 2番目の色（エプロンなど）  C c 3番目の色  R r リボン  Y y 金具  L l 脚  F f 靴  G g T など その他
使い方: python tools/pixel/sprites.py  （確認用の拡大図 tools/sim/out/pixel_chars.png も書き出す）
"""
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import big, mirror, pad, render, rows, shift, stamp, sym  # noqa: E402
import chars  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'art' / 'pixel'
PREVIEW = ROOT / 'tools' / 'sim' / 'out' / 'pixel_chars.png'
CELL = 32

# 横向きの歩きの脚（右向き。近い脚 L/F、遠い脚 l/f）。x は脚の左はし
SIDE_LEGS = {
    'n': ['...lLL...', '...fFF...', '...fFFF..'],
    'a': ['..ll.LL..', '.ff...FF.', 'ff....FFF'],
    'b': ['..LL.ll..', '.FF...ff.', 'FF....fff'],
}


def grid_of(c, view):
    g = c[view]
    if isinstance(g, str):
        g = rows(g)
    if c.get(view + '_sym'):
        g = sym(g)
    return pad(g, CELL, CELL)


def face(g, c, view, mood):
    """表情を目と口に重ねる"""
    fx = c.get('face', {}).get(view)
    if not fx or mood == 'normal':
        return g
    for (x, y, w) in fx['eyes']:  # 目の左上と幅（右の目は左右反転の形）
        pat = chars.EYES[mood]
        if w < 0:
            pat = mirror(pat)
        g = stamp(g, pat, x, y)
    if 'mouth' in fx and mood in chars.MOUTH:
        mx, my, mw = fx['mouth']
        g = stamp(g, [r[:mw] for r in chars.MOUTH[mood]], mx, my)
    return g


def split(g, hem):
    """hem 行より上が体、下が脚"""
    body = [r if j <= hem else '.' * CELL for j, r in enumerate(g)]
    legs = ['.' * CELL if j <= hem else r for j, r in enumerate(g)]
    return body, legs


def over(a, b):
    """a の上に b を重ねる"""
    return [''.join(bc if bc != '.' else ac for ac, bc in zip(ra, rb)) for ra, rb in zip(a, b)]


def lift(legs, half):
    """片足（左半分 half=0 / 右半分 1）を1ドット持ち上げる"""
    mid = CELL // 2
    part = [r[:mid] if half == 0 else r[mid:] for r in legs]
    part = shift(part, dy=-1)
    return [(p + r[mid:]) if half == 0 else (r[:mid] + p) for p, r in zip(part, legs)]


def walk_front(g, c):
    body, legs = split(g, c['hem'])
    down = shift(body, dy=1)
    return [over(lift(legs, 0), down), g, over(lift(legs, 1), down), g]


def shear(legs, k, top):
    """脚を、下ほど k ドット横にずらして斜めにする（横向きの歩き）"""
    h = CELL - 1 - top
    out = ['.' * CELL] * CELL
    for j in range(top, CELL):
        d = round((j - top) / max(1, h) * k)
        out[j] = shift([legs[j]], dx=d)[0]
    return out


def recolor(g, m):
    return [''.join(m.get(ch, ch) for ch in r) for r in g]


def walk_side(g, c):
    body, legs = split(g, c['hem'])
    if c.get('foe'):  # 侵入者: 立ち姿の脚を、前後に斜めにずらして2本に見せる（奥の脚は暗く）
        far = c.get('far', {'M': 'm', 'm': 'n', 'L': 'l', 'F': 'f'})
        top = c['hem'] + 1
        out = []
        for k, bob in ((3, 1), (0, 0), (-3, 1), (0, 0)):
            if k:
                lg = over(recolor(shear(legs, -k, top), far), shear(legs, k, top))
            else:
                lg = legs
            out.append(over(lg, shift(body, dy=bob)))
        return out
    x = c['side_leg_x']
    out = []
    for k, bob in (('a', 1), ('n', 0), ('b', 1), ('n', 0)):
        lg = stamp(['.' * CELL] * CELL, SIDE_LEGS[k], x, CELL - 3)
        out.append(over(lg, shift(body, dy=bob)))
    return out


def tear(g, c):
    """ピンチ: すその破れ・ほつれ"""
    for (x, y, ch) in c.get('tear', []):
        g = stamp(g, [ch], x, y)
    return g


def build(name):
    c = chars.CHARS[name]
    pal, oc = c['pal'], c.get('oc', {})
    pal = {**chars.COMMON, **pal}
    views = {}
    for v in ('front', 'side', 'back'):
        g = grid_of(c, v)
        for (x, y, patch) in c.get(v + '_add', []):
            g = stamp(g, rows(patch) if isinstance(patch, str) else patch, x, y)
        views[v] = g
    views['left'] = mirror(views['side'])
    order = ('front', 'left', 'side', 'back')  # 下・左・右・上
    sheet_rows = []
    for v in order:
        g = face(views[v], c, 'side' if v == 'left' else v, 'normal')
        if v == 'left':
            g = mirror(face(views['side'], c, 'side', 'normal'))
        if v in ('front', 'back'):
            fr = walk_front(g, c)
        else:
            fr = walk_side(views['side'], c) if v == 'side' else [mirror(f) for f in walk_side(views['side'], c)]
        sheet_rows.append(fr)

    def pose(mood, dy=0, extra=None):
        out = []
        for v in order:
            src = views['side'] if v == 'left' else views[v]
            vv = 'side' if v == 'left' else v
            g = face(src, c, vv, mood)
            if extra:
                g = extra(g)
            if v == 'left':
                g = mirror(g)
            out.append(shift(g, dy=dy))
        return out

    sheet_rows.append(pose('normal'))
    if c.get('foe'):
        pass
    else:
        sheet_rows.append(pose('hurt', dy=-1))
        sheet_rows.append(pose('teary', dy=0, extra=lambda g: tear(g, c)))
        f = views['front']
        body, legs = split(f, c['hem'])
        crouch = over(legs, shift(face(body, c, 'front', 'happy'), dy=1))
        sheet_rows.append([crouch, face(f, c, 'front', 'happy'), face(f, c, 'front', 'cheer'), face(f, c, 'front', 'happy')])
    sheet = Image.new('RGBA', (CELL * 4, CELL * len(sheet_rows)), (0, 0, 0, 0))
    for r, fr in enumerate(sheet_rows):
        for k, g in enumerate(fr):
            sheet.alpha_composite(render(g, pal, oc=oc, keep=c.get('keep', '')), (k * CELL, r * CELL))
    return sheet


def main(names=None):
    OUT.mkdir(parents=True, exist_ok=True)
    names = names or list(chars.CHARS)
    sheets = []
    for n in names:
        sh = build(n)
        sh.save(OUT / f'{n}.png')
        sheets.append(sh)
        print('ドット絵', n, sh.size)
    W = sum(s.width for s in sheets) + 8 * (len(sheets) + 1)
    H = max(s.height for s in sheets) + 16
    pv = Image.new('RGBA', (W, H), (98, 90, 146, 255))
    x = 8
    for s in sheets:
        pv.alpha_composite(s, (x, 8))
        x += s.width + 8
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    big(pv, 4).save(PREVIEW)
    print('確認用:', PREVIEW.relative_to(ROOT).as_posix())


if __name__ == '__main__':
    main(sys.argv[1:] or None)

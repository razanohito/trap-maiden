"""新しい絵柄（Nano Banana で描いた「月夜のおかし箱」版）をゲームに入れる。

入力: art-src/v2/ の白背景の画像
  - sheet_<名前>.webp  … 設定画（左から 正面・横・後ろ）。lily mina noel cecil knight thief heavy
  - <子>_<表情>.webp   … 立ち絵。表情は normal laugh surprised teary smug
出力:
  - art/portrait_<子>.webp（normal）、art/portrait_<子>_happy.webp（laugh）、
    art/portrait_<子>_<surprised|teary|smug>.webp … 高さ 640px、背景を抜いたもの
  - art/sprites/<子>_{walk,idle,hit,pinch,jump}.webp、art/sprites/foe_<敵>_{walk,idle}.webp
    … 盤面の絵。1コマ 96x96px（盤面には 48px で描く。高解像度の画面でもにじまない）
       walk は 4列×4行（行は 下・左・右・上、列は歩く順）、idle・hit・pinch は 4列×1行（下・左・右・上）、
       jump は 4列×1行（ジャンプの順）。歩く・のけぞる・喜ぶ動きは、設定画の1枚を傾け・伸び縮みさせて作る
  - 女の子は頭を大きくした2.5頭身（ちびキャラ）にして、小さな盤面でも顔と髪型が分かるようにする

使い方: python tools/import_v2.py（確認用の一覧を tools/sim/out/v2_sprites.png に出す）
新しい絵を入れるときは art-src/v2/ に同じ名前で置いてから実行する。
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art-src" / "v2"
OUT = ROOT / "art"
SPR = ROOT / "art" / "sprites"
PREVIEW = ROOT / "tools" / "sim" / "out"
F = 96          # 1コマの大きさ（盤面の 48px の2倍）
FOOT = 93       # 足もとの高さ（コマの下から 3px 上）
GIRLS = ("lily", "mina", "noel", "cecil")
FOES = ("knight", "thief", "heavy")
FACES = {"normal": "", "laugh": "_happy", "surprised": "_surprised", "teary": "_teary", "smug": "_smug"}
PORTRAIT_H = 640
SIDE_LOOKS_LEFT = {"knight", "heavy"}  # 設定画の横向きが左を向いているもの
# 盤面での背の高さ（コマの高さに対する割合）と、頭を大きくする度合い
HEIGHT = {"lily": .9, "mina": .94, "noel": .9, "cecil": .9, "knight": .74, "thief": .74, "heavy": .94}
HEAD = {"lily": (.2, .42), "mina": (.27, .46), "noel": (.2, .42), "cecil": (.2, .42), "thief": (.3, .4)}  # (元の頭の割合, 盤面での割合)


def cut_white(img: Image.Image, drop_side_bits: bool = False) -> Image.Image:
    """外周からつながっている白い背景を抜く。エプロンやフリルの白は線で囲まれているので残る。
    drop_side_bits: 左右の端に触れている小さなかけら（隣の人物の髪や羽根飾り）を消す"""
    a = np.asarray(img.convert("RGB")).astype(int)
    h, w, _ = a.shape
    white = a.min(2) > 236
    lab, _ = ndimage.label(white)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    bg = np.isin(lab, border[border > 0])
    # 髪と腕のすき間など、まわりを囲まれた背景も抜く。背景は紙より明るい真っ白（エプロンの白は少し暗い）なので明るさで見分ける
    pure = a.min(2) > 248
    lab2, n2 = ndimage.label(pure & ~bg)
    if n2:
        idx = np.arange(1, n2 + 1)
        size = ndimage.sum(np.ones_like(lab2), lab2, idx)
        mean = ndimage.mean(a.min(2), lab2, idx)
        holes = idx[(size > 200) & (mean >= 251.5)]
        bg |= np.isin(lab2, holes)
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    # ふち: 背景のすぐ内側の明るい画素は、明るさに応じて透かす（暗い背景で白い縁が出ないように）
    near = np.asarray(Image.fromarray(alpha).filter(ImageFilter.MinFilter(5))) < 128
    edge = near & ~bg
    light = a.min(2)
    alpha[edge] = np.clip((255 - light[edge]) * 255 // 50, 0, 255).astype(np.uint8)
    if drop_side_bits:
        parts, n = ndimage.label(alpha > 40)
        if n > 1:
            sizes = ndimage.sum(np.ones_like(parts), parts, range(1, n + 1))
            big = int(np.argmax(sizes)) + 1
            side = set(np.unique(np.concatenate([parts[:, 0], parts[:, -1]]))) - {0, big}
            side |= {i + 1 for i, n in enumerate(sizes) if n < sizes.max() * .02}  # 離れた小さな点（紙のしみ・隣の持ち物の先）
            for k in side - {big}: alpha[parts == k] = 0
    im = Image.fromarray(np.dstack([a.astype(np.uint8), alpha]), "RGBA")
    return im.crop(im.getbbox())


def figures(sheet: Image.Image) -> list[Image.Image]:
    """設定画から3体（正面・横・後ろ）を切り出して背景を抜く。
    人物の間は「色の付いた画素が一番少ない列」で分ける（羽根飾りなどが隣とつながっていても切れる）"""
    a = np.asarray(sheet.convert("RGB")).astype(int)
    h, w, _ = a.shape
    col = ndimage.uniform_filter1d((a.min(2) < 225).sum(0).astype(float), 9)
    cuts = []
    for lo, hi in ((.22, .48), (.52, .78)):
        x0, x1 = int(w * lo), int(w * hi)
        m = col[x0:x1].min()
        xs = np.nonzero(col[x0:x1] <= m + .5)[0] + x0  # 一番少ない列が続くときは真ん中で
        cuts.append(int(xs.mean()) if xs.max() - xs.min() < w * .15 else int(xs[len(xs) // 2]))
    edges = [0] + cuts + [w]
    return [cut_white(sheet.crop((edges[i], 0, edges[i + 1], h)), True) for i in range(3)]


def chibi(im: Image.Image, head: tuple[float, float] | None, height: int) -> Image.Image:
    """頭（上の head[0] の割合）を大きくして、全体の高さを height にする。
    倍率は首のあたりでなめらかに変える（ツインテールなどが途中で切れて見えないように）"""
    if not head:
        return im.resize((max(1, round(im.width * height / im.height)), height), Image.LANCZOS)
    src_head, dst_head = head
    # 最終の3倍の大きさで形を変えてから縮める（細い線がちらつかないように）
    S = 3
    big_h = height * S
    base = big_h / im.height
    im = im.resize((max(1, round(im.width * base)), big_h), Image.LANCZOS)
    a = np.asarray(im).astype(float)
    a[..., :3] *= a[..., 3:4] / 255  # 透明なところの色がにじまないように
    h, w = a.shape[:2]
    kt = dst_head / src_head; kb = (1 - dst_head) / (1 - src_head)  # 頭と体の倍率（高さを保つ）
    ys = np.arange(h) / h
    t = np.clip((ys - src_head * .75) / (src_head * .6), 0, 1)
    k = kt + (kb - kt) * (1 - np.cos(t * np.pi)) / 2      # 元の行ごとの倍率
    pos = np.concatenate([[0], np.cumsum(k)])              # 元の行 → 出力の行
    out_h = int(pos[-1])
    yo = np.arange(out_h) + .5
    ysrc = np.interp(yo, pos, np.arange(h + 1))             # 出力の行 → 元の行
    krow = np.interp(ysrc, np.arange(h), k)
    cols = np.nonzero(a[..., 3].max(0) > 0)[0]
    cx = (cols.min() + cols.max()) / 2
    out_w = int(w * k.max()) + 2
    xo = np.arange(out_w) + .5 - out_w / 2
    yy = np.repeat(ysrc[:, None], out_w, 1)
    xx = cx + xo[None, :] / krow[:, None]
    res = np.stack([ndimage.map_coordinates(a[..., c], [yy, xx], order=1, cval=0) for c in range(4)], -1)
    al = res[..., 3:4]
    res[..., :3] = np.where(al > 0, res[..., :3] * 255 / np.maximum(al, 1e-3), 0)
    out = Image.fromarray(np.clip(res, 0, 255).astype(np.uint8), "RGBA")
    out = out.crop(out.getbbox())
    return out.resize((max(1, round(out.width * height / out.height)), height), Image.LANCZOS)


def fit(im: Image.Image, max_w: int) -> Image.Image:
    if im.width > max_w:
        im = im.resize((max_w, max(1, round(im.height * max_w / im.width))), Image.LANCZOS)
    return im


def place(im: Image.Image, rot: float = 0, sx: float = 1, sy: float = 1, dx: int = 0, dy: int = 0) -> Image.Image:
    """足もとを基準に、伸び縮み・傾き・ずらしをかけて 1コマに置く"""
    if sx != 1 or sy != 1:
        im = im.resize((max(1, round(im.width * sx)), max(1, round(im.height * sy))), Image.LANCZOS)
    big = Image.new("RGBA", (F * 2, F * 2), (0, 0, 0, 0))
    ox, oy = F - im.width // 2, F * 2 - 20 - im.height  # 足もとを (F, 2F-20) に
    big.alpha_composite(im, (ox, oy))
    if rot:
        big = big.rotate(rot, resample=Image.BICUBIC, center=(F, F * 2 - 20))
    frame = big.crop((F // 2 - dx, F * 2 - 20 - FOOT - dy, F // 2 + F - dx, F * 2 - 20 - FOOT + F - dy))
    return frame


def stride(im: Image.Image, k: float) -> Image.Image:
    """足もと（下の2割）を左右にずらして、歩いている感じを出す"""
    a = np.asarray(im).copy()
    h = a.shape[0]; y0 = int(h * .78)
    for y in range(y0, h):
        s = round(k * (y - y0) / max(1, h - y0))
        if s: a[y] = np.roll(a[y], s, axis=0); (a[y, :s] if s > 0 else a[y, s:])[:] = 0
    return Image.fromarray(a, "RGBA")


def sheet_row(frames: list[Image.Image]) -> Image.Image:
    out = Image.new("RGBA", (F * len(frames), F), (0, 0, 0, 0))
    for i, f in enumerate(frames): out.alpha_composite(f, (i * F, 0))
    return out


def make_sprites(name: str, key: str, girl: bool) -> list[Image.Image]:
    down, side, up = figures(Image.open(SRC / f"sheet_{name}.webp"))
    h = round(F * HEIGHT[name])
    head = HEAD.get(name)
    views = [fit(chibi(v, head, h), F - 4) for v in (down, side, up)]
    d, s, u = views
    right = s.transpose(Image.FLIP_LEFT_RIGHT) if name in SIDE_LOOKS_LEFT else s
    left = right.transpose(Image.FLIP_LEFT_RIGHT)
    dirs = [d, left, right, u]  # 行の順: 下・左・右・上
    # 歩く: 接地A → 通過（少し浮く）→ 接地B → 通過
    walk = []
    for vi, v in enumerate(dirs):
        sidev = vi in (1, 2)
        fwd = -1 if vi == 1 else 1
        seq = []
        for c in range(4):
            if c % 2 == 0:
                sgn = 1 if c == 0 else -1
                img = stride(v, 5 * sgn * (fwd if sidev else 1)) if sidev else v
                seq.append(place(img, rot=(3 * sgn if not sidev else -2.5 * fwd), sx=1.03, sy=.97))
            else:
                seq.append(place(v, dy=3, sx=.98, sy=1.02))
        walk.append(sheet_row(seq))
    walk_im = Image.new("RGBA", (F * 4, F * 4), (0, 0, 0, 0))
    for r, row in enumerate(walk): walk_im.alpha_composite(row, (0, r * F))
    idle = sheet_row([place(v) for v in dirs])
    out = {"walk": walk_im, "idle": idle}
    if girl:
        # のけぞる: 向きと反対に傾いて、少し縮む
        out["hit"] = sheet_row([place(v, rot=(-12 if i == 1 else 12 if i == 2 else 9), sx=1.04, sy=.93) for i, v in enumerate(dirs)])
        # ピンチ（体力が残り1）: 膝を曲げてへたりこみ気味に
        out["pinch"] = sheet_row([place(v, rot=(4 if i == 1 else -4 if i == 2 else 0), sx=1.06, sy=.88) for i, v in enumerate(dirs)])
        # 喜びのジャンプ（正面）: かがむ → 伸びる → ふつう → 伸びる
        out["jump"] = sheet_row([place(d, sx=1.08, sy=.88), place(d, sx=.94, sy=1.06), place(d), place(d, sx=.96, sy=1.04, rot=4)])
    for part, im in out.items():
        im.save(SPR / f"{key}_{part}.webp", quality=90, method=6, exact=False)  # 透明を保ったまま軽くする
    return [out["walk"], out["idle"]] + ([out["hit"], out["pinch"], out["jump"]] if girl else [])


def main() -> None:
    SPR.mkdir(parents=True, exist_ok=True); PREVIEW.mkdir(parents=True, exist_ok=True)
    for g in GIRLS:
        for face, suf in FACES.items():
            p = SRC / f"{g}_{face}.webp"
            if not p.exists():
                continue
            im = cut_white(Image.open(p))
            im = im.resize((round(im.width * PORTRAIT_H / im.height), PORTRAIT_H), Image.LANCZOS)
            im.save(OUT / f"portrait_{g}{suf}.webp", quality=88, method=6)
        print("立ち絵", g)
    sheets = []
    for g in GIRLS: sheets += make_sprites(g, g, True); print("盤面の絵", g)
    for e in FOES: sheets += make_sprites(e, f"foe_{e}", False); print("盤面の絵", e)
    # 確認用: 全部を縦に並べて、暗い床の色の上に 2 倍で置く
    W = max(s.width for s in sheets); H = sum(s.height for s in sheets)
    pv = Image.new("RGBA", (W, H), (91, 91, 168, 255)); y = 0
    for s in sheets: pv.alpha_composite(s, (0, y)); y += s.height
    pv.save(PREVIEW / "v2_sprites.png")


if __name__ == "__main__":
    main()

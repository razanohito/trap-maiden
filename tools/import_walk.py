"""盤面で動くキャラの絵（Nano Banana に描いてもらった 4x4 のスプライト）をゲームに入れる → art/sprites/

入力: art-src/walk/<名前>_walk.*  … 4x4。行は 下・左・右・上 向きの歩き、列は歩く順の4コマ
      art-src/walk/<名前>_poses.* … 4x4。行は 立ち・やられ・ピンチ（各 下・左・右・上）・喜びジャンプ4コマ
      名前: lily mina noel cecil knight thief heavy（png / webp / jpg、緑 #00FF00 の背景）
出力（tools/import_v2.py が作るものと同じ形。ゲームの側は変えなくてよい）:
  - 女の子: art/sprites/<名前>_{walk,idle,hit,pinch,jump}.webp
  - 侵入者: art/sprites/foe_<名前>_{walk,idle}.webp
  - tools/sim/out/walk_preview.png … 確認用（盤面の床の色の上に並べる）
  1コマ 96px。足もとを下から 3px の線にそろえ、背の高さは 1枚の絵の中で同じ倍率にする（コマごとに大きさが変わらない）。
  poses が無いときは、walk の各行の1コマ目を立ち絵に使い、やられ・ピンチ・ジャンプは import_v2 の作り方（傾ける）で作る。

使い方: python tools/import_walk.py
"""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from greenkey import key_green
from import_v2 import F, FOOT, HEIGHT, place, sheet_row

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art-src" / "walk"
SPR = ROOT / "art" / "sprites"
PREVIEW = ROOT / "tools" / "sim" / "out" / "walk_preview.png"
GIRLS = ("lily", "mina", "noel", "cecil")
FOES = ("knight", "thief", "heavy")


def find(name):
    for ext in ("png", "webp", "jpg", "jpeg"):
        p = SRC / f"{name}.{ext}"
        if p.exists():
            return p
    return None


def cells(path):
    """4x4 に分けて、各コマの人物を切り出す。人物が枠をはみ出していても、いちばん大きなかたまりの中心で拾う"""
    im = key_green(Image.open(path))
    a = np.asarray(im)
    al = a[..., 3] > 60
    parts, n = ndimage.label(al)
    objs = ndimage.find_objects(parts)
    sizes = ndimage.sum(np.ones_like(parts), parts, range(1, n + 1)) if n else []
    h, w = al.shape
    ch, cw = h / 4, w / 4
    grid = [[[] for _ in range(4)] for _ in range(4)]
    big = max(sizes) if n else 0
    for i, sl in enumerate(objs):
        if sizes[i] < big * .02:  # ごみ
            continue
        cy = (sl[0].start + sl[0].stop) / 2
        cx = (sl[1].start + sl[1].stop) / 2
        r, c = min(3, int(cy // ch)), min(3, int(cx // cw))
        grid[r][c].append(i + 1)
    out = []
    for r in range(4):
        row = []
        for c in range(4):
            ids = grid[r][c]
            if not ids:
                row.append(None)
                continue
            m = np.isin(parts, ids)
            ys, xs = np.nonzero(m)
            box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
            fig = a.copy()
            fig[~m, 3] = 0
            row.append((Image.fromarray(fig, "RGBA").crop(box), box))
        out.append(row)
    return out


def frames(grid, name, align_bottom=True):
    """1枚の絵の中のコマを同じ倍率で 96px のコマにする"""
    hs = [f[0].height for row in grid for f in row if f]
    ws = [f[0].width for row in grid for f in row if f]
    if not hs:
        return None
    s = min(F * HEIGHT.get(name, .9) / np.median(hs), (F - 4) / max(ws))
    out = []
    for row in grid:
        bottoms = [f[1][3] for f in row if f]
        low = max(bottoms) if bottoms else 0
        r = []
        for f in row:
            if not f:
                r.append(Image.new("RGBA", (F, F), (0, 0, 0, 0)))
                continue
            im = f[0].resize((max(1, round(f[0].width * s)), max(1, round(f[0].height * s))), Image.LANCZOS)
            lift = 0 if align_bottom else min(round((low - f[1][3]) * s), max(0, FOOT - im.height - 1))  # ジャンプは浮いた分を残す（頭がコマから出ない範囲で）
            r.append(place(im, dy=-lift))  # place の dy は下向きが正
        out.append(r)
    return out


def main():
    SPR.mkdir(parents=True, exist_ok=True)
    previews = []
    for name in GIRLS + FOES:
        wp, pp = find(f"{name}_walk"), find(f"{name}_poses")
        if not wp:
            continue
        key = name if name in GIRLS else f"foe_{name}"
        walk = frames(cells(wp), name)
        walk_im = Image.new("RGBA", (F * 4, F * 4), (0, 0, 0, 0))
        for r, row in enumerate(walk):
            walk_im.alpha_composite(sheet_row(row), (0, r * F))
        out = {"walk": walk_im}
        poses = None
        if pp:
            g = cells(pp)
            poses = frames(g[:3], name) + frames([g[3]], name, align_bottom=False)
        if poses:
            out["idle"] = sheet_row(poses[0])
        else:  # 歩きの1コマ目（下・左・右・上）を立ち絵に
            out["idle"] = sheet_row([walk[r][1] for r in range(4)])
        if name in GIRLS:
            if poses:
                out["hit"], out["pinch"], out["jump"] = sheet_row(poses[1]), sheet_row(poses[2]), sheet_row(poses[3])
            else:  # import_v2 と同じく、立ち絵を傾けて作る
                base = [walk[r][1] for r in range(4)]
                trim = [b.crop(b.getbbox()) for b in base]
                out["hit"] = sheet_row([place(t, rot=(-12 if i == 1 else 12 if i == 2 else 9), sx=1.04, sy=.93) for i, t in enumerate(trim)])
                out["pinch"] = sheet_row([place(t, rot=(4 if i == 1 else -4 if i == 2 else 0), sx=1.06, sy=.88) for i, t in enumerate(trim)])
                d = trim[0]
                out["jump"] = sheet_row([place(d, sx=1.08, sy=.88), place(d, sx=.94, sy=1.06), place(d), place(d, sx=.96, sy=1.04, rot=4)])
        for part, im in out.items():
            im.save(SPR / f"{key}_{part}.webp", quality=90, method=6, exact=False)
            previews.append(im)
        print("盤面の絵", key, "（ポーズあり）" if poses else "")
    if not previews:
        print("art-src/walk/ に絵がありません")
        return
    W = max(p.width for p in previews)
    H = sum(p.height for p in previews)
    pv = Image.new("RGBA", (W, H), (91, 91, 168, 255))
    y = 0
    for p in previews:
        pv.alpha_composite(p, (0, y))
        y += p.height
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    pv.resize((W * 2, H * 2), Image.NEAREST).save(PREVIEW)
    print("確認用:", PREVIEW.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()

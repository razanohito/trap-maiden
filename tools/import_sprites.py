"""ChatGPT に作ってもらった 48px のスプライトシートを、ゲーム用に整えて art/sprites/ に入れる。

もらったシートは、コマがマスの境目をまたいでずれていることがあるので、
1 行ぶん（192x48）から人物のかたまりを4つ取り出し、それぞれをマスの中央・足もと y=46 にそろえ直す。

- 入力: art-src/sprites48/<名前>_walk_4dir_48px.png（4列×4行、行は 下・左・右・上）
        art-src/sprites48/<名前>_hit_critical_4dir_48px.png（1行目の「被弾」だけ使う）
- 出力: art/sprites/<名前>_walk.png（4列×4行）、<名前>_idle.png（各行の2コマ目を待機姿勢に）、
        <名前>_hit.png（4列×1行。下・左・右・上）
- 侵入者は foe_knight / foe_thief / foe_heavy（歩行だけ）

使い方: python tools/import_sprites.py
"""
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art-src" / "sprites48"
OUT = ROOT / "art" / "sprites"
F, FOOT = 48, 46


def blobs(a: np.ndarray):
    """不透明な画素のかたまり（8方向につながる）を [(画素数, ys, xs)] で返す"""
    h, w = a.shape
    seen = np.zeros_like(a, bool); out = []
    for sy, sx in zip(*np.nonzero(a)):
        if seen[sy, sx]:
            continue
        q = deque([(sy, sx)]); seen[sy, sx] = True; ys, xs = [], []
        while q:
            y, x = q.popleft(); ys.append(y); xs.append(x)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and a[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True; q.append((ny, nx))
        out.append((len(ys), np.array(ys), np.array(xs)))
    return out


def fix_row(row: Image.Image) -> list[Image.Image]:
    """1行（192x48）から人物を4つ取り出し、48x48 の中央・足もとをそろえて返す"""
    rgba = np.asarray(row.convert("RGBA"))
    alpha = rgba[..., 3] > 30
    parts = blobs(alpha)
    big = sorted(parts, key=lambda b: b[0], reverse=True)
    figs = sorted(big[:4], key=lambda b: b[2].mean())
    # 小さなかけら（光の粒・持ち物の先など）は、いちばん近い人物に付ける
    groups = [[f] for f in figs]
    for p in big[4:]:  # 人物のすぐそば（4px 以内）のかけらだけ残し、隣のコマからはみ出た切れ端は捨てる
        def gap(f):
            return max(f[2].min() - p[2].max(), p[2].min() - f[2].max(), f[1].min() - p[1].max(), p[1].min() - f[1].max(), 0)
        k = min(range(4), key=lambda i: gap(figs[i]))
        if gap(figs[k]) <= 4 and p[0] >= 3:
            groups[k].append(p)
    cells = []
    for g in groups:
        ys = np.concatenate([p[1] for p in g]); xs = np.concatenate([p[2] for p in g])
        cell = np.zeros((F, F, 4), np.uint8)
        low = ys >= ys.min() + (ys.max() - ys.min()) * 0.55  # 下半身の中心で左右をそろえる
        cx = int(round(xs[low].mean())) if low.any() else int(round(xs.mean()))
        dx, dy = 24 - cx, FOOT - ys.max()
        for y, x in zip(ys, xs):
            nx, ny = x + dx, y + dy
            if 0 <= nx < F and 0 <= ny < F:
                cell[ny, nx] = rgba[y, x]
        cells.append(Image.fromarray(cell, "RGBA"))
    return cells


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for path in sorted(SRC.glob("*_walk_4dir_48px.png")):
        name = path.name.replace("_walk_4dir_48px.png", "")
        sheet = Image.open(path)
        walk = Image.new("RGBA", (F * 4, F * 4)); idle = Image.new("RGBA", (F * 4, F))
        for r in range(4):
            cells = fix_row(sheet.crop((0, r * F, F * 4, r * F + F)))
            for c, im in enumerate(cells):
                walk.paste(im, (c * F, r * F))
            idle.paste(cells[1], (r * F, 0))
        walk.save(OUT / f"{name}_walk.png"); idle.save(OUT / f"{name}_idle.png")
        hit_path = SRC / f"{name}_hit_critical_4dir_48px.png"
        if hit_path.exists():  # 1行目（被弾）だけ使う。2行目（ピンチ）は服が破れる表現なので使わない
            hit = Image.new("RGBA", (F * 4, F))
            for c, im in enumerate(fix_row(Image.open(hit_path).crop((0, 0, F * 4, F)))):
                hit.paste(im, (c * F, 0))
            hit.save(OUT / f"{name}_hit.png")
        print(name, "ok", "(被弾あり)" if hit_path.exists() else "")


if __name__ == "__main__":
    main()

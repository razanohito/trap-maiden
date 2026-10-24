"""ChatGPT・Gemini に描いてもらった 48px のスプライトシートを、盤面用の 1 枚のシートにまとめる → art/pixel48/<名前>.png

もらったシートは、コマがマスの境目をまたいでずれていることがあるので、
1 行ぶん（192x48）から人物のかたまりを4つ取り出し、それぞれをマスの中央・足もと y=46 にそろえ直す。

- 入力（art-src/sprites48/）:
    <名前>_walk_4dir_48px.png         4列×4行。行は 下・左・右・上 向き、列は歩きの4コマ
    <名前>_hit_critical_4dir_48px.png  4列×2行。列は 下・左・右・上、1行目＝被弾、2行目＝ピンチ（女の子だけ）
    <名前>_jump_4frames_48px.png       4列×1行。喜びのジャンプ（女の子だけ）
- 出力: art/pixel48/<名前>.png（1コマ 48x48、横4コマ）
    女の子:   0〜3行 歩き  4行 立ち（各向きの2コマ目）  5行 やられ  6行 ピンチ  7行 喜びジャンプ
    それ以外: 0〜3行 歩き  4行 立ち
- 侵入者は foe_knight / foe_thief / foe_heavy。男爵 baron と鍵の精 chirin も同じ形で作っておく
- チリンは宙に浮いているので、足もとをそろえず上下の揺れをそのまま残す（横の中央だけそろえる）
- 確認用の拡大図: tools/sim/out/pixel48_chars.png

使い方: python tools/import_sprites.py
"""
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art-src" / "sprites48"
OUT = ROOT / "art" / "pixel48"
PREVIEW = ROOT / "tools" / "sim" / "out" / "pixel48_chars.png"
F, FOOT = 48, 46
FLOATING = {"chirin"}  # 足もとをそろえないキャラ（宙に浮いている）
MIRROR_RIGHT = {"chirin", "lily"}  # 右向きの行だけ小さく描かれていたので、左向きを左右反転して使う


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


def dehalo(rgba: np.ndarray) -> np.ndarray:
    """ふちの白いにじみ（白い縁取り）を取る。透明に接している、白っぽくて色の薄い画素を2周ぶん消す"""
    a = rgba.copy()
    for _ in range(2):
        op = a[..., 3] > 30
        edge = np.zeros_like(op)
        edge[1:, :] |= ~op[:-1, :]; edge[:-1, :] |= ~op[1:, :]
        edge[:, 1:] |= ~op[:, :-1]; edge[:, :-1] |= ~op[:, 1:]
        rgb = a[..., :3].astype(int)
        light = (rgb.min(-1) > 100) & (rgb.max(-1) - rgb.min(-1) < 45)
        kill = op & edge & light
        if not kill.any():
            break
        a[kill] = 0
    return a


def fix_row(row: Image.Image, floating=False, halo=False) -> list[Image.Image]:
    """1行（192x48）から人物を4つ取り出し、48x48 の中央・足もとをそろえて返す"""
    rgba = np.asarray(row.convert("RGBA"))
    if halo:
        rgba = dehalo(rgba)
    alpha = rgba[..., 3] > 30
    parts = blobs(alpha)
    big = sorted(parts, key=lambda b: b[0], reverse=True)
    figs = sorted(big[:4], key=lambda b: b[2].mean())
    # 小さなかけら（光の粒・持ち物の先など）は、いちばん近い人物に付ける
    groups = [[f] for f in figs]
    for p in big[4:]:  # 人物のすぐそば（4px 以内）のかけらだけ残し、隣のコマからはみ出た切れ端は捨てる
        if p[1].max() >= F - 1 or p[1].min() <= 0:  # 行の上下のふちに付いた切れ端は、上下のコマからはみ出たもの
            continue
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
        dx = 24 - cx
        dy = 0 if floating else FOOT - ys.max()
        if floating and ys.max() + dy > FOOT:  # 浮いていても、コマの下にはみ出さない
            dy = FOOT - ys.max()
        for y, x in zip(ys, xs):
            nx, ny = x + dx, y + dy
            if 0 <= nx < F and 0 <= ny < F:
                cell[ny, nx] = rgba[y, x]
        cells.append(Image.fromarray(cell, "RGBA"))
    return cells


def enlarge(cells: list[Image.Image], target: int) -> list[Image.Image]:
    """小さく描かれたコマ（喜びのジャンプは歩きより一回り小さかった）を、いちばん背の高いコマが target ドットになるまで拡大する。
    どのコマも同じ倍率にして、足もと y=46・横の中央にそろえ直す"""
    figs = [c.crop(c.getbbox()) for c in cells]
    k = min(1.4, target / max(f.height for f in figs))
    if k <= 1.02:
        return cells
    out = []
    for fig in figs:
        fig = fig.resize((round(fig.width * k), round(fig.height * k)), Image.LANCZOS)  # 元の絵がなめらかなので、なめらかに拡大する
        wide = Image.new("RGBA", (F * 2, F * 2))  # はみ出しても困らないよう広い台に置いてから 48x48 を切り出す
        wide.alpha_composite(fig, (F - fig.width // 2, F + FOOT - fig.height))
        out.append(wide.crop((F // 2, F, F // 2 + F, F * 2)))
    return out


def build(name: str) -> Image.Image:
    floating = name in FLOATING
    walk = Image.open(SRC / f"{name}_walk_4dir_48px.png")
    rows = [fix_row(walk.crop((0, r * F, F * 4, r * F + F)), floating, halo=floating) for r in range(4)]
    if name in MIRROR_RIGHT:
        rows[2] = [im.transpose(Image.FLIP_LEFT_RIGHT) for im in rows[1]]
    rows.append([rows[r][1] for r in range(4)])  # 立ち: 各向きの2コマ目
    hit = SRC / f"{name}_hit_critical_4dir_48px.png"
    if hit.exists():
        sheet = Image.open(hit)
        rows += [fix_row(sheet.crop((0, r * F, F * 4, r * F + F))) for r in range(2)]
    jump = SRC / f"{name}_jump_4frames_48px.png"
    if jump.exists():
        rows.append(list(enlarge(fix_row(Image.open(jump).crop((0, 0, F * 4, F)), halo=True), target=42)))
    out = Image.new("RGBA", (F * 4, F * len(rows)))
    for r, cells in enumerate(rows):
        for c, im in enumerate(cells):
            out.paste(im, (c * F, r * F))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sheets = []
    for path in sorted(SRC.glob("*_walk_4dir_48px.png")):
        name = path.name.replace("_walk_4dir_48px.png", "")
        sh = build(name)
        sh.save(OUT / f"{name}.png", optimize=True)
        sheets.append(sh)
        print(name, sh.size)
    W = sum(s.width for s in sheets) + 8 * (len(sheets) + 1)
    H = max(s.height for s in sheets) + 16
    pv = Image.new("RGBA", (W, H), (58, 52, 80, 255))
    x = 8
    for s in sheets:
        pv.alpha_composite(s, (x, 8)); x += s.width + 8
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    pv.resize((W * 3, H * 3), Image.NEAREST).save(PREVIEW)
    print("確認用:", PREVIEW.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()

"""ChatGPT に描いてもらった高精細なドット絵（横4コマ×縦2行のシートを4枚）を、盤面用の1枚のシートにまとめる → art/pixel48/<名前>.png

もらったシートは 1774x887 ほどの大きさで、1ドットが約5.5ピクセル、背景はマゼンタ。マス目の位置はそろっていないので、
1行ぶんを横に見て、何も描かれていない縦のすき間で4人に切り分け、全コマを同じ倍率で縮めて 96x96 のマスに並べ直す。

- 入力（art-src/sprites128/）: <名前>_1_*.png 〜 <名前>_4_*.png（ファイル名の順に読む）
    1枚目: 上の行＝下向き歩き  下の行＝左向き歩き
    2枚目: 上の行＝右向き歩き  下の行＝上向き歩き（後ろ姿）
    3枚目: 上の行＝立ち（正面・右・左・後ろの順に描かれていたので、左と右を入れかえる）  下の行＝やられ
    4枚目: 上の行＝ピンチ  下の行＝喜び
- 出力: art/pixel48/<名前>.png（1コマ 96x96、横4コマ×縦8行。行の中身は 48px の絵と同じ）
    足もとは y=90。背丈（立ち姿）は HEIGHT ドット。行ごとに、いちばん下の足をそろえ、行の中の上下の動き（跳ねる・しりもち）はそのまま残す
- 色は COLORS 色に絞り、マゼンタがにじんだふちの画素は消す
- ゲーム側（pxGeo）は、シートの幅が 4×48 より大きければ高精細な絵として、1ドット＝画面の1ピクセルで描く
- 確認用の拡大図: tools/sim/out/hires_<名前>.png

使い方: python tools/import_hires.py noel
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art-src" / "sprites128"
OUT = ROOT / "art" / "pixel48"
PREVIEW = ROOT / "tools" / "sim" / "out"
S, FOOT, HEIGHT = 96, 90, 72  # 1コマの大きさ・足もとの高さ・立ち姿の背丈（ドット）
COLORS = 48
SWAP = {4: (0, 2, 1, 3)}  # 行 → 並べかえ（立ちの行は 正面・右・左・後ろ で描かれていた）


def bg_mask(a: np.ndarray) -> np.ndarray:
    """マゼンタの背景と、マゼンタがにじんだ紫っぽいふちの画素"""
    r, g, b = (a[..., i].astype(int) for i in range(3))
    mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    magenta = (r > 140) & (b > 140) & (g < 0.6 * np.minimum(r, b))
    purple = (g == mn) & (mx - mn > 60) & (np.abs(r - b) < 0.35 * (mx - mn) + 20) & (r > g + 50) & (b > g + 50)  # 輪郭線とマゼンタが混ざった色
    return magenta | purple


def split4(fg: np.ndarray) -> list[tuple[int, int]]:
    """1行の前景から、何も描かれていない縦のすき間で4人ぶんの横の範囲を返す"""
    occ = fg.sum(0) > 0
    xs = np.nonzero(occ)[0]
    runs, x = [], xs.min()
    while x <= xs.max():  # 中の空き列のかたまり（左右のふちに付いたものは除く）
        if not occ[x]:
            s = x
            while not occ[x]:
                x += 1
            runs.append((x - s, s, x))
        x += 1
    cuts = sorted(r for r in sorted(runs, reverse=True)[:3])
    edges = [xs.min()] + [(s + e) // 2 for _, s, e in sorted(cuts, key=lambda r: r[1])] + [xs.max() + 1]
    return [(edges[i], edges[i + 1]) for i in range(4)]


def shrink(rgb: np.ndarray, fg: np.ndarray, k: float) -> np.ndarray:
    """前景だけを面積で平均して k 倍に縮める（背景の色を混ぜない）→ RGBA。半分以上が前景のドットだけ残す"""
    h, w = fg.shape
    nh, nw = max(1, round(h * k)), max(1, round(w * k))
    pre = np.zeros((h, w, 4), np.float32)
    pre[..., :3] = rgb * fg[..., None]; pre[..., 3] = fg
    ch = [np.asarray(Image.fromarray(pre[..., i]).resize((nw, nh), Image.BOX)) for i in range(4)]
    al = ch[3]
    out = np.zeros((nh, nw, 4), np.uint8)
    keep = al >= 0.5
    for i in range(3):
        out[..., i] = np.clip(ch[i] / np.maximum(al, 1e-6), 0, 255)
    out[..., 3] = keep * 255
    return out


def main(name: str):
    files = sorted(SRC.glob(f"{name}_[1-4]_*.png"))
    assert len(files) == 4, f"{SRC} に {name}_1_〜{name}_4_ の4枚が必要です（見つかったのは {len(files)} 枚）"
    rows = []  # 8行ぶん: [(rgb, fg) を4つ]
    for f in files:
        a = np.asarray(Image.open(f).convert("RGB"))
        fg_all = ~bg_mask(a)
        h = a.shape[0] // 2
        for half in (slice(0, h), slice(h, a.shape[0])):
            rgb, fg = a[half].astype(np.float32), fg_all[half]
            figs = []
            for x0, x1 in split4(fg):
                sub = fg[:, x0:x1]
                ys = np.nonzero(sub.any(1))[0]; xs = np.nonzero(sub.any(0))[0]
                y0, y1, xa, xb = ys.min(), ys.max() + 1, xs.min() + x0, xs.max() + 1 + x0
                figs.append((rgb[y0:y1, xa:xb], fg[y0:y1, xa:xb], y0, y1))
            rows.append(figs)
    stand = np.median([y1 - y0 for _, _, y0, y1 in rows[4]])  # 立ち姿の背丈で倍率を決める
    k = HEIGHT / stand
    sheet = np.zeros((S * 8, S * 4, 4), np.uint8)
    for r, figs in enumerate(rows):
        order = SWAP.get(r, (0, 1, 2, 3))
        base = max(y1 for _, _, _, y1 in figs)  # 行の中でいちばん下の足
        for c, i in enumerate(order):
            rgb, fg, y0, y1 = figs[i]
            im = shrink(rgb, fg, k)
            h, w = im.shape[:2]
            op = im[..., 3] > 0
            ys = np.nonzero(op.any(1))[0]
            low = op[int(h * 0.55):]  # 下半身の中心で左右をそろえる
            cx = np.nonzero(low)[1].mean() if low.any() else w / 2
            top = FOOT - round((base - y0) * k)
            left = round(S / 2 - cx)
            xs = np.nonzero(op.any(0))[0]
            if xs.max() - xs.min() < S:  # はみ出すなら、マスに収まる範囲で寄せる（やられの、ほうきが飛ぶコマ）
                left = min(max(left, -xs.min()), S - 1 - xs.max())
            for yy in range(h):
                ty = top + yy
                if not 0 <= ty < S:
                    continue
                for xx in np.nonzero(op[yy])[0]:
                    tx = left + xx
                    if 0 <= tx < S:
                        sheet[r * S + ty, c * S + tx] = im[yy, xx]
    img = Image.fromarray(sheet, "RGBA")
    op = sheet[..., 3] > 0  # 色を絞る
    q = Image.fromarray(sheet[..., :3]).quantize(COLORS, method=Image.MEDIANCUT, dither=Image.NONE)
    rgbq = np.asarray(q.convert("RGB"))
    out = np.zeros_like(sheet); out[op, :3] = rgbq[op]; out[op, 3] = 255
    img = Image.fromarray(out, "RGBA")
    OUT.mkdir(parents=True, exist_ok=True); img.save(OUT / f"{name}.png", optimize=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    pv = Image.new("RGBA", img.size, (40, 30, 44, 255)); pv.alpha_composite(img)
    pv.resize((img.width * 2, img.height * 2), Image.NEAREST).save(PREVIEW / f"hires_{name}.png")
    print(f"{name}: 倍率 {k:.3f}（立ち姿 {stand:.0f}px → {HEIGHT}ドット） → {OUT / (name + '.png')}")


if __name__ == "__main__":
    for n in sys.argv[1:] or ["noel"]:
        main(n)

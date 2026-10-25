"""ChatGPT に描いてもらった高精細なドット絵（横4コマ×縦2行のシートを4枚）を、盤面用の1枚のシートにまとめる → art/pixel48/<名前>.png

もらったシートは 1774x887 ほどの大きさで、1ドットが約5.5ピクセル、背景はマゼンタ。マス目の位置はそろっていないので、
1行ぶんを横に見て、何も描かれていない縦のすき間で4人に切り分け、全コマを同じ倍率で縮めて 96x96 のマスに並べ直す。

- 入力（art-src/sprites128/）: キャラごとの読み方は SOURCES に書く
    ノエル: <名前>_1_*.png 〜 _4_*.png（マゼンタの背景・横4×縦2）
        1枚目 下向き歩き・左向き歩き  2枚目 右向き歩き・上向き歩き  3枚目 立ち（正面・右・左・後ろで描かれていたので入れかえる）・やられ  4枚目 ピンチ・喜び
        やられ・ピンチは4コマの動き（ゲームは時間でコマを進める。PX_ANIM）
    リリィ: lily_walk_4x4.png（白とグレーの市松模様が絵に焼き込まれた背景・横4×縦4の歩き）、
        lily_hit_pinch_4dir.png（透明の背景・やられ／ピンチを下・左・右・上の向きごとに1コマ）、lily_joy.png（透明・喜び4コマ）
        立ちの行は、歩きの各向きの2コマ目を使う
- 絵ごとに描かれた大きさが違うので、ファイルごとに「ref のコマの背丈」が HEIGHT×ref の割合になるよう倍率を決める
- 出力: art/pixel48/<名前>.png（1コマ 96x96、横4コマ×縦8行。行の中身は 48px の絵と同じ）
    足もとは y=90。背丈（立ち姿）は HEIGHT ドット。行ごとに、いちばん下の足をそろえ、行の中の上下の動き（跳ねる・しりもち）はそのまま残す
- 色は COLORS 色に絞り、マゼンタがにじんだふちの画素は消す
- ゲーム側（pxGeo）は、シートの幅が 4×48 より大きければ高精細な絵として、1ドット＝画面の1ピクセルで描く
- 確認用の拡大図: tools/sim/out/hires_<名前>.png

使い方: python tools/import_hires.py noel
"""
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from import_sprites import rgb2hsv, hsv2rgb

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art-src" / "sprites128"
OUT = ROOT / "art" / "pixel48"
PREVIEW = ROOT / "tools" / "sim" / "out"
S, FOOT, HEIGHT = 96, 90, 72  # 1コマの大きさ・足もとの高さ・立ち姿の背丈（ドット）
COLORS = 96  # 48色だとミーナの髪のうす紫と杖の緑の宝石が消えた


def bg_mask(a: np.ndarray) -> np.ndarray:
    """マゼンタの背景と、マゼンタがにじんだ紫っぽいふちの画素"""
    r, g, b = (a[..., i].astype(int) for i in range(3))
    mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    magenta = (r > 140) & (b > 140) & (g < 0.6 * np.minimum(r, b))
    purple = (g == mn) & (mx - mn > 60) & (np.abs(r - b) < 0.35 * (mx - mn) + 20) & (r > g + 50) & (b > g + 50)  # 輪郭線とマゼンタが混ざった色
    return magenta | purple


def split_n(cnt: np.ndarray, n: int) -> list[tuple[int, int]]:
    """画素の数の並び cnt（列ごと・行ごと）を、何も描かれていないすき間で n 個の範囲に分ける"""
    occ = cnt > 0
    xs = np.nonzero(occ)[0]
    runs, x = [], xs.min()
    while x <= xs.max():  # 中の空きのかたまり（ふちに付いたものは除く）
        if not occ[x]:
            s = x
            while not occ[x]:
                x += 1
            runs.append((x - s, s, x))
        x += 1
    mids = sorted((s + e) // 2 for _, s, e in sorted(runs, reverse=True)[:n - 1])
    span = xs.max() - xs.min()
    good = [m for m in mids if any(abs(m - (xs.min() + span * i / n)) < span / (2 * n) for i in range(1, n))]
    mids = good
    for i in range(1, n):  # すき間がない（くっついている）ところは、n等分の位置の近くで、いちばん絵の少ない所で切る
        want = xs.min() + span * i / n
        if any(abs(m - want) < span / (2 * n) for m in mids):
            continue
        lo, hi = int(want - span / (2.5 * n)), int(want + span / (2.5 * n))
        mids.append(lo + int(np.argmin(cnt[lo:hi])))
    edges = [xs.min()] + sorted(mids) + [xs.max() + 1]
    return [(edges[i], edges[i + 1]) for i in range(n)]


def split4(fg: np.ndarray) -> list[tuple[int, int]]:
    """1行の前景から、何も描かれていない縦のすき間で4人ぶんの横の範囲を返す"""
    return split_n(fg.sum(0), 4)


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


def checker_mask(a: np.ndarray) -> np.ndarray:
    """白とグレーの市松模様（透明のつもりの背景が絵に焼き込まれたもの）。
    明るい無彩色の画素のうち、画像のふちからつながっているところ（輪郭線で囲まれた絵の中の白は残る）"""
    rgb = a.astype(int); mx, mn = rgb.max(-1), rgb.min(-1)
    cand = ((mx - mn) < 16) & (mn > 170)
    grow = lambda m, n: np.asarray(Image.fromarray(m.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(n))) > 0
    seed = np.zeros_like(cand); seed[0, :] = seed[-1, :] = seed[:, 0] = seed[:, -1] = True
    seed &= cand
    while True:  # ふちから塗りつぶす
        nxt = grow(seed, 3) & cand
        if nxt.sum() == seed.sum():
            break
        seed = nxt
    neutral = (mx - mn) < 16
    holes = cand & ~seed & grow(neutral & (mn > 240), 9) & grow(neutral & (mn > 175) & (mx < 210), 9)  # 髪の巻き毛のすき間に閉じこめられた市松模様
    seed |= holes
    ring = grow(seed, 3) & ((mx - mn) < 24) & (mn > 110)  # 輪郭線とのあいだの、灰色のにじみ
    return seed | ring


def load(path: Path, bg: str):
    """→ (RGB, 前景の真偽)"""
    im = Image.open(path)
    if bg == "alpha":
        a = np.asarray(im.convert("RGBA"))
        return a[..., :3], a[..., 3] > 128
    a = np.asarray(im.convert("RGB"))
    return a, ~(bg_mask(a) if bg == "magenta" else checker_mask(a))


def label(m: np.ndarray):
    """8方向につながった画素のかたまりに番号を付ける → (番号の配列, かたまりの数)"""
    h, w = m.shape; lab = np.zeros((h, w), np.int32); n = 0
    for sy, sx in zip(*np.nonzero(m)):
        if lab[sy, sx]:
            continue
        n += 1; lab[sy, sx] = n; q = deque([(sy, sx)])
        while q:
            y, x = q.popleft()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and not lab[ny, nx]:
                        lab[ny, nx] = n; q.append((ny, nx))
    return lab, n


def pick(sub_fg: np.ndarray, x0: int, x1: int) -> np.ndarray:
    """行の前景から、横の範囲 x0〜x1 の人だけを取り出す。
    かたまりごとに見て、中心がこの範囲にあるものを残す（くっついた隣の人の髪を切らない）。
    行の上下のふちに付いた小さなかたまりは、上下の行からはみ出たものなので捨てる"""
    D = 4  # 4ピクセルずつまとめて数える（速さのため）
    H, W = sub_fg.shape
    small = np.asarray(Image.fromarray(sub_fg.astype(np.uint8) * 255).resize((W // D + 1, H // D + 1), Image.BOX)) > 0
    lab, n = label(small)
    keep = np.zeros(n + 1, bool); sizes = np.bincount(lab.ravel(), minlength=n + 1); sizes[0] = 0
    inside = [i for i in range(1, n + 1) if x0 <= np.nonzero(lab == i)[1].mean() * D < x1]
    if not inside:
        return np.zeros_like(sub_fg)
    big = max(sizes[i] for i in inside)
    for i in inside:
        ys = np.nonzero(lab == i)[0]
        edge = ys.min() == 0 or ys.max() >= small.shape[0] - 1
        if sizes[i] == big or (not edge and sizes[i] >= 2) or (edge and sizes[i] > big * 0.3):
            keep[i] = True
    km = keep[lab]
    km = np.repeat(np.repeat(km, D, 0), D, 1)[:H, :W]
    return sub_fg & km


def cut(rgb, fg, nrows):
    """シートを nrows 行に分け、各行から4人を切り出す → [[(rgb, fg, y0, y1), ...4], ...]"""
    out = []
    for y0r, y1r in split_n(fg.sum(1), nrows):
        sub_rgb, sub_fg = rgb[y0r:y1r].astype(np.float32), fg[y0r:y1r]
        figs = []
        for x0, x1 in split4(sub_fg):
            m = pick(sub_fg, x0, x1)
            ys = np.nonzero(m.any(1))[0]; xs = np.nonzero(m.any(0))[0]
            y0, y1, xa, xb = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            figs.append((sub_rgb[y0:y1, xa:xb], m[y0:y1, xa:xb], y0, y1))
        out.append(figs)
    return out


def recolor_mina(sheet: np.ndarray) -> np.ndarray:
    """ミーナ: うす紫の帽子・服 → 暗いプラム色、ピンクのリボン → 金（立ち絵の tools/recolor_mina.py と同じ色合い）。
    うす紫の髪（赤寄りで明るい、色相 296〜）はそのまま"""
    a = sheet.astype(float); rgb = a[..., :3] / 255
    h, s, v = rgb2hsv(rgb); op = a[..., 3] > 0
    cloth = op & (h >= 255) & (h < 296) & (s >= 0.24) & (v >= 0.28)
    rib = op & ((h >= 333) | (h < 6)) & (s >= 0.33) & (v >= 0.6)
    out = rgb.copy()
    out[cloth] = hsv2rgb(np.full(cloth.sum(), 335.0), np.clip(s[cloth] * 0.75 + 0.12, 0, 1), v[cloth] * 0.55)
    out[rib] = hsv2rgb(np.full(rib.sum(), 42.0), np.clip(s[rib] * 1.5 + 0.25, 0, 0.8), np.clip(v[rib] * 0.95, 0, 1))
    a[..., :3] = out * 255
    return np.clip(a, 0, 255).astype(np.uint8)


RECOLOR = {"mina": recolor_mina}


# キャラごとの読み方。files: (ファイル名のパターン, 背景, 行数, 出力の行の並び, ref=(行, 列) 背丈をはかるコマ, ref の背丈の割合)
SOURCES = {
    "noel": dict(files=[("noel_1_*.png", "magenta", 2, [0, 1], None),
                        ("noel_2_*.png", "magenta", 2, [2, 3], None),
                        ("noel_3_*.png", "magenta", 2, [4, 5], None),
                        ("noel_4_*.png", "magenta", 2, [6, 7], None)],
                 swap={4: (0, 2, 1, 3)}, scale_row=4),
    "lily": dict(files=[("lily_walk_4x4.png", "alpha", 4, [0, 1, 2, 3], None),  # ランタンを持った版
                        ("lily_hit_pinch_4dir.png", "alpha", 2, [5, 6], ("rel", 240 / 383)),  # 立ったままのやられの背丈で歩きとそろえる
                        ("lily_joy.png", "alpha", 1, [7], ((0, 1), 1.04))],  # 喜びはランタンなしの前の絵（片足を上げたコマで背丈をそろえる）
                 idle_from_walk=1, scale_row=0),
    "cecil": dict(files=[("cecil_walk_4x4.png", "alpha", 4, [0, 1, 2, 3], None),
                         ("cecil_hit_pinch_4dir.png", "alpha", 2, [5, 6], ("rel", 268 / 403)),
                         ("cecil_joy.png", "alpha", 1, [7], ("rel", 268 / 435))],
                  idle_from_walk=1, scale_row=0),
    # 侵入者は歩き4方向＋立ち（5行）。立ちは歩きの2コマ目。背丈はノエルたちより少し低く、重戦士だけ大きく
    "foe_knight": dict(files=[("foe_knight_walk_4x4.png", "alpha", 4, [0, 1, 2, 3], None)], idle_from_walk=1, scale_row=0, rows=5, height=66),
    "foe_thief": dict(files=[("foe_thief_walk_4x4.png", "alpha", 4, [0, 1, 2, 3], None)], idle_from_walk=1, scale_row=0, rows=5, height=66),
    "foe_heavy": dict(files=[("foe_heavy_walk_4x4.png", "alpha", 4, [0, 1, 2, 3], None)], idle_from_walk=1, scale_row=0, rows=5, height=80),
    "mina": dict(files=[("mina_walk_4x4.png", "alpha", 4, [0, 1, 2, 3], None),  # プラム色で描き直してもらった絵
                        ("mina_hit_pinch_4dir.png", "alpha", 2, [5, 6], ("rel", 0.70)),  # 歩きより大きく描かれている（背丈と帽子の幅の比の間をとる）
                        ("mina_joy.png", "alpha", 1, [7], ("rel", 196 / 380), "mina")],  # 喜びは前のうす紫の絵しかないので、色を塗り替えて使う
                 idle_from_walk=1, scale_row=0),
}


def main(name: str):
    cfg = SOURCES[name]
    rows = {}  # 出力の行 → [(rgb, fg, y0, y1, 倍率) を4つ]
    base_k = None
    for pat, bg, nrows, targets, ref, *paint in cfg["files"]:
        files = sorted(SRC.glob(pat)); assert files, f"{SRC / pat} がありません"
        rgb, fg = load(files[0], bg)
        if paint:  # このファイルだけ色を塗り替える
            rgba = np.dstack([rgb, fg.astype(np.uint8) * 255])
            rgb = RECOLOR[paint[0]](rgba)[..., :3]
        got = cut(rgb, fg, nrows)
        if ref is None:
            if cfg["scale_row"] in targets:
                stand = np.median([y1 - y0 for _, _, y0, y1 in got[targets.index(cfg["scale_row"])]])
                base_k = cfg.get("height", HEIGHT) / stand
            k = None
        elif ref[0] == "rel":  # 先に読んだ歩きの絵の倍率 × 割合
            k = base_k * ref[1]
        else:
            (rr, cc), frac = ref
            _, _, y0, y1 = got[rr][cc]
            k = cfg.get("height", HEIGHT) * frac / (y1 - y0)
        for t, figs in zip(targets, got):
            rows[t] = [(*f, k) for f in figs]
    rows = {t: [(a, b, c, d, k if k is not None else base_k) for a, b, c, d, k in figs] for t, figs in rows.items()}
    if cfg.get("idle_from_walk") is not None:
        c = cfg["idle_from_walk"]; rows[4] = [rows[d][c] for d in range(4)]
    nrow = cfg.get("rows", 8)
    sheet = np.zeros((S * nrow, S * 4, 4), np.uint8)
    for r in range(nrow):
        figs = rows[r]
        order = cfg.get("swap", {}).get(r, (0, 1, 2, 3))
        base = max(y1 for _, _, _, y1, _ in figs)  # 行の中でいちばん下の足
        for c, i in enumerate(order):
            rgb, fg, y0, y1, k = figs[i]
            im = shrink(rgb, fg, k)
            h, w = im.shape[:2]
            op = im[..., 3] > 0
            low = op[int(h * 0.55):]  # 下半身の中心で左右をそろえる
            cx = np.nonzero(low)[1].mean() if low.any() else w / 2
            top = FOOT - round((base - y0) * k) if r != 4 else FOOT - h  # 立ちの行は歩きの行から集めたので、それぞれ足もとをそろえる
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
    op = sheet[..., 3] > 0  # 色を絞る
    q = Image.fromarray(sheet[..., :3]).quantize(COLORS, method=Image.FASTOCTREE, kmeans=2, dither=Image.NONE)
    rgbq = np.asarray(q.convert("RGB"))
    out = np.zeros_like(sheet); out[op, :3] = rgbq[op]; out[op, 3] = 255
    img = Image.fromarray(out, "RGBA")
    OUT.mkdir(parents=True, exist_ok=True); img.save(OUT / f"{name}.png", optimize=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    pv = Image.new("RGBA", img.size, (40, 30, 44, 255)); pv.alpha_composite(img)
    pv.resize((img.width * 2, img.height * 2), Image.NEAREST).save(PREVIEW / f"hires_{name}.png")
    print(f"{name}: → {OUT / (name + '.png')}")


if __name__ == "__main__":
    for n in sys.argv[1:] or list(SOURCES):
        main(n)

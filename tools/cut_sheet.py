"""設定画（art-src/lily_sheet.webp）から正面・横・後ろの3方向を切り出し、羊皮紙の背景を抜いて art/ に保存する。

- 背景は「明るく、なめらかで、羊皮紙の色」の画素を、切り出した枠の外周から塗りつぶして決める。
  フリルやエプロンは羊皮紙より少し暗く、インクの線で囲まれているので残る。
- 出力: art/lily_down.webp（正面）、art/lily_side.webp（右向き）、art/lily_up.webp（後ろ）、
        art/portrait_lily.webp（正面の大きい版。タイトルと結果の画面用）
"""
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art-src" / "lily_sheet.webp"
OUT = ROOT / "art"

# 3体の左右の範囲（設定画の列を調べて決めた。左右に少し余白を足す）
FIGS = {"lily_down": (40, 530), "lily_side": (560, 975), "lily_up": (1005, 1470)}


def is_bg(px: np.ndarray) -> np.ndarray:
    r, g, b = px[..., 0], px[..., 1], px[..., 2]
    lum = (r + g + b) / 3
    return (lum >= 203) & (r - b > 40) & (r - b < 80) & (r - g < 36) & (r > 220)


def cut(img: np.ndarray) -> np.ndarray:
    h, w, _ = img.shape
    cand = is_bg(img)
    # なめらかさ: 隣との差が小さい画素だけ背景として広げる（インクの線や模様で止まる）
    diff = np.zeros((h, w), int)
    diff[:, 1:] = np.abs(img[:, 1:] - img[:, :-1]).sum(2)
    diff[1:, :] = np.maximum(diff[1:, :], np.abs(img[1:] - img[:-1]).sum(2))
    cand &= diff < 22
    bg = np.zeros((h, w), bool)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if cand[y, x] and not bg[y, x]:
                bg[y, x] = True; q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if cand[y, x] and not bg[y, x]:
                bg[y, x] = True; q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and cand[ny, nx] and not bg[ny, nx]:
                bg[ny, nx] = True; q.append((ny, nx))
    # 足もとの影（羊皮紙のしみ）は少し暗いので、下の方だけ条件をゆるめて抜く
    r, g, b2 = img[..., 0], img[..., 1], img[..., 2]
    lum = (r + g + b2) / 3
    low = np.zeros((h, w), bool); low[int(h * .9):, :] = True; low[:int(h * .06), :] = True  # 上の端の紙のしみも
    bg |= low & (lum >= 165) & (r - b2 > 35) & (r - b2 < 95) & (r - g < 40)
    # 足の間の、外とつながっていない背景のすき間も抜く（大きめのかたまりだけ）
    lab2 = np.zeros((h, w), np.int32); cur2 = 0
    for sy in range(h):
        for sx in range(w):
            if sy < h * .8 or not cand[sy, sx] or bg[sy, sx] or lab2[sy, sx]:  # 脚のあたりだけ（エプロンや顔は明るいので対象外にする）
                continue
            cur2 += 1; pts = []; q = deque([(sy, sx)]); lab2[sy, sx] = cur2
            while q:
                y, x = q.popleft(); pts.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and cand[ny, nx] and not bg[ny, nx] and not lab2[ny, nx]:
                        lab2[ny, nx] = cur2; q.append((ny, nx))
            if len(pts) > 250:
                for y, x in pts: bg[y, x] = True
    # 人物と離れた小さな残り（紙のしみ）を消す: 不透明部分のうち一番大きいかたまりだけ残す
    keep = ~bg
    lab = np.zeros((h, w), np.int32); best, best_n, cur = 0, 0, 0
    for sy in range(0, h, 2):
        for sx in range(0, w, 2):
            if not keep[sy, sx] or lab[sy, sx]:
                continue
            cur += 1; n = 0; q = deque([(sy, sx)]); lab[sy, sx] = cur
            while q:
                y, x = q.popleft(); n += 1
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and keep[ny, nx] and not lab[ny, nx]:
                        lab[ny, nx] = cur; q.append((ny, nx))
            if n > best_n:
                best, best_n = cur, n
    return lab != best


def main() -> None:
    OUT.mkdir(exist_ok=True)
    sheet = Image.open(SRC).convert("RGB")
    a = np.asarray(sheet).astype(int)
    for name, (x0, x1) in FIGS.items():
        crop = a[:, x0:x1]
        bg = cut(crop)
        alpha = Image.fromarray(((~bg) * 255).astype("uint8"))
        alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.7))
        rgba = Image.fromarray(crop.astype("uint8")).convert("RGBA")
        rgba.putalpha(alpha)
        box = rgba.getbbox()
        rgba = rgba.crop(box)
        rgba.save(OUT / f"{name}_full.png")
        # 盤面用: 高さ 160px（キャンバスでは 2 倍の解像度で約 56px 表示）
        small = rgba.resize((round(rgba.width * 160 / rgba.height), 160), Image.LANCZOS)
        small.save(OUT / f"{name}.webp", quality=90, method=6)
        if name == "lily_down":
            big = rgba.resize((round(rgba.width * 560 / rgba.height), 560), Image.LANCZOS)
            big.save(OUT / "portrait_lily.webp", quality=88, method=6)
        print(name, rgba.size)


if __name__ == "__main__":
    main()

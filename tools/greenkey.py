"""純緑（#00FF00）の背景を抜く（Nano Banana に緑の背景で描いてもらった絵用）。

- 緑らしさ = G がほかの2色よりどれだけ強いか。強いほど透かす（ふちは半分透ける）
- 抜いたあとのふちに残る緑のにじみ（スピル）を、G を R・B の大きいほうまで下げて消す
- 外周からつながっていない緑（服の緑など）は残す
"""
import numpy as np
from PIL import Image
from scipy import ndimage


def key_green(img: Image.Image, keep_inner_green: bool = True) -> Image.Image:
    a = np.asarray(img.convert("RGB")).astype(float)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    greenness = g - np.maximum(r, b)  # 純緑で 255、灰色や肌で 0 前後
    alpha = np.clip(1 - (greenness - 40) / 90, 0, 1)  # 40 以下は不透明、130 以上は透明
    if keep_inner_green:  # 外周からつながった緑と、ほぼ純緑（腕や足のすき間）だけを背景とみなす（服の緑は残す）
        bg = greenness > 70
        lab, _ = ndimage.label(bg)
        border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
        outer = np.isin(lab, border[border > 0]) | (greenness > 150)
        near = ndimage.binary_dilation(outer, iterations=3)
        alpha = np.where(near, alpha, 1.0)
    # スピルを消す: G を max(R, B) とほぼ同じまでに抑える
    g2 = np.minimum(g, np.maximum(r, b) + 4)
    g = np.where(alpha < 1, g2, g)
    out = np.dstack([r, g, b, alpha * 255]).round().clip(0, 255).astype(np.uint8)
    im = Image.fromarray(out, "RGBA")
    # 細かいごみ（ほかから離れた小さな点）を消す
    al = np.asarray(im.getchannel("A")) > 40
    parts, n = ndimage.label(al)
    if n > 1:
        sizes = ndimage.sum(np.ones_like(parts), parts, range(1, n + 1))
        small = [i + 1 for i, s in enumerate(sizes) if s < max(30, sizes.max() * .004)]
        if small:
            arr = np.asarray(im).copy()
            arr[np.isin(parts, small), 3] = 0
            im = Image.fromarray(arr, "RGBA")
    return im

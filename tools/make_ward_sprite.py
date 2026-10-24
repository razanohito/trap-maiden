"""結界騎士（3連続でないと倒せない侵入者）の盤面スプライトを、騎士の 48px シートの色を塗り替えて作る
- 入力: art/pixel48/foe_knight.png（ChatGPT に描いてもらった絵）
- 出力: art/pixel48/foe_ward.png（金の鎧・白い陣羽織・白い羽根飾り）
- 確認用の拡大図: tools/sim/out/foe_ward_x3.png
"""
import colorsys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art" / "pixel48" / "foe_knight.png"
OUT = ROOT / "art" / "pixel48" / "foe_ward.png"
PREVIEW = ROOT / "tools" / "sim" / "out" / "foe_ward_x3.png"


def recolor(r, g, b):
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    hd = h * 360
    if s < .2:  # 鎧（灰色）→ 金
        h2, s2, v2 = 43 / 360, .42 + .25 * (1 - v), min(1, v * 1.02)
    elif 180 <= hd <= 250:  # 青い陣羽織 → 生成りの白
        h2, s2, v2 = 40 / 360, .12, min(1, .35 + v * .7)
    elif hd >= 330 or hd < 15:  # 赤い羽根飾り → 白
        h2, s2, v2 = 45 / 360, .1 * s + .04, min(1, .45 + v * .6)
    else:  # 剣・紋章などはそのまま
        return r, g, b
    r2, g2, b2 = colorsys.hsv_to_rgb(h2, s2, v2)
    return round(r2 * 255), round(g2 * 255), round(b2 * 255)


def main():
    im = Image.open(SRC).convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a:
                px[x, y] = (*recolor(r, g, b), a)
    im.save(OUT)
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    big = im.resize((im.width * 3, im.height * 3), Image.NEAREST)
    bg = Image.new("RGBA", big.size, (40, 32, 44, 255))
    bg.alpha_composite(big)
    bg.save(PREVIEW)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
